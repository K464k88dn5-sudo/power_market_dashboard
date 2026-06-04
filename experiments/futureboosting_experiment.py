"""
FutureBoosting广东电价预测实验
基于 arXiv:2603.06726 的思路：
  Stage 1: TSFM零样本预测协变量（负荷、温度等）
  Stage 2: LightGBM利用TSFM预测值+领域特征做最终电价预测

运行前提：
    pip install chronos-forecasting lightgbm pandas numpy scikit-learn torch

作者：Mr.Du研究助手
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings("ignore")


# ============================================================
# 数据生成（含协变量）
# ============================================================

def generate_guangdong_data_with_covariates(days: int = 120, seed: int = 42) -> pd.DataFrame:
    """
    生成广东电力市场多变量数据集
    包含：电价、负荷、温度、辐照度、风速、煤价
    """
    np.random.seed(seed)
    
    hours = list(range(24))
    dates = pd.date_range(end=datetime(2026, 6, 1), periods=days, freq='D')
    
    # 基准曲线
    load_base = [45, 42, 40, 39, 40, 45, 55, 65, 75, 82, 88, 90,
                 85, 80, 82, 88, 92, 90, 85, 78, 70, 60, 52, 47]  # GW
    price_base = [250, 230, 220, 215, 220, 240, 300, 370, 420, 460, 490, 480,
                  440, 410, 420, 450, 490, 470, 430, 400, 370, 340, 310, 270]
    temp_base = [27, 26, 26, 25, 25, 26, 27, 29, 31, 33, 34, 35,
                 35, 36, 36, 35, 34, 33, 31, 30, 29, 28, 28, 27]  # ℃
    
    records = []
    for d in dates:
        is_weekend = d.weekday() >= 5
        month = d.month
        seasonal = 1.0 + 0.15 * np.sin((month - 3) * np.pi / 6)
        weekend_f = 0.75 if is_weekend else 1.0
        
        for h in hours:
            # 负荷
            load = load_base[h] * weekend_f * seasonal + np.random.normal(0, 2)
            
            # 温度
            temp = temp_base[h] + 3 * np.sin((month - 6) * np.pi / 6) + np.random.normal(0, 1.5)
            
            # 辐照度
            irradiance = max(0, 800 * np.sin(max(0, (h - 6)) * np.pi / 12) + np.random.normal(0, 50)) if 6 <= h <= 18 else 0
            
            # 风速
            wind = max(0, 3 + 2 * np.random.random())
            
            # 煤价（日度变化）
            coal = 850 + 5 * np.sin(dates.tolist().index(d) * 2 * np.pi / 30) + np.random.normal(0, 5)
            
            # 电价（受负荷、温度、煤价影响）
            price = (price_base[h] * weekend_f * seasonal
                     + 0.5 * (load - 70) * 3       # 负荷影响
                     + 2.0 * max(0, temp - 33) * 10  # 高温影响
                     + (coal - 850) * 0.15           # 煤价传导
                     + np.random.normal(0, 15))
            price = max(80, min(800, price))
            
            records.append({
                'datetime': d + timedelta(hours=h),
                'date': d.strftime('%Y-%m-%d'),
                'hour': h,
                'price': round(price, 2),
                'load_gw': round(load, 2),
                'temperature': round(temp, 1),
                'irradiance': round(irradiance, 1),
                'wind_speed': round(wind, 2),
                'coal_price': round(coal, 1),
                'is_weekend': int(is_weekend),
                'month': month,
            })
    
    df = pd.DataFrame(records)
    df['datetime'] = pd.to_datetime(df['datetime'])
    return df


# ============================================================
# 特征工程
# ============================================================

def build_features(df: pd.DataFrame, tsfm_load_pred: np.ndarray = None,
                   tsfm_temp_pred: np.ndarray = None) -> pd.DataFrame:
    """
    构建特征矩阵
    如果提供TSFM预测值，则作为特征加入（FutureBoosting核心）
    """
    feat = df.copy()
    
    # 时间特征
    feat['hour_sin'] = np.sin(2 * np.pi * feat['hour'] / 24)
    feat['hour_cos'] = np.cos(2 * np.pi * feat['hour'] / 24)
    feat['day_sin'] = np.sin(2 * np.pi * feat['datetime'].dt.dayofweek / 7)
    feat['day_cos'] = np.cos(2 * np.pi * feat['datetime'].dt.dayofweek / 7)
    feat['month_sin'] = np.sin(2 * np.pi * feat['month'] / 12)
    feat['month_cos'] = np.cos(2 * np.pi * feat['month'] / 12)
    
    # 滞后特征
    for lag in [1, 24, 48, 168]:  # 1h, 1d, 2d, 1w
        feat[f'price_lag_{lag}'] = feat['price'].shift(lag)
        feat[f'load_lag_{lag}'] = feat['load_gw'].shift(lag)
    
    # 滚动统计
    for window in [24, 168]:
        feat[f'price_roll_mean_{window}'] = feat['price'].rolling(window).mean()
        feat[f'price_roll_std_{window}'] = feat['price'].rolling(window).std()
        feat[f'load_roll_mean_{window}'] = feat['load_gw'].rolling(window).mean()
    
    # TSFM预测的协变量（FutureBoosting核心创新）
    if tsfm_load_pred is not None:
        feat['tsfm_load_pred'] = tsfm_load_pred
    if tsfm_temp_pred is not None:
        feat['tsfm_temp_pred'] = tsfm_temp_pred
    
    # 交互特征
    feat['load_x_temp'] = feat['load_gw'] * feat['temperature']
    feat['coal_x_load'] = feat['coal_price'] * feat['load_gw']
    
    feat = feat.dropna().reset_index(drop=True)
    return feat


# ============================================================
# TSFM协变量预测
# ============================================================

def tsfm_predict_covariate(series: np.ndarray, pred_len: int, cov_name: str = "covariate") -> np.ndarray:
    """
    使用Chronos-Bolt对协变量做零样本预测
    """
    try:
        import torch
        from chronos import ChronosPipeline
        
        print(f"  [Chronos] 零样本预测 {cov_name}...")
        pipeline = ChronosPipeline.from_pretrained(
            "amazon/chronos-bolt-base",
            device_map="cpu",
        )
        context = torch.tensor(series.astype(np.float32))
        forecast = pipeline.predict(context, prediction_length=pred_len, num_samples=10)
        median = np.median(forecast[0].numpy(), axis=0)
        print(f"  [Chronos] {cov_name} 预测完成，shape={median.shape}")
        return median
    except Exception as e:
        print(f"  [Chronos] {cov_name} 预测失败: {e}")
        # 回退：用最近24小时的周期性重复
        last_day = series[-24:]
        return np.tile(last_day, pred_len // 24 + 1)[:pred_len]


# ============================================================
# 实验主流程
# ============================================================

def run_futureboosting_experiment():
    """
    FutureBoosting实验：
    对比3种方案的电价预测效果
    A. 纯LightGBM（无TSFM）
    B. TSFM零样本直接预测电价
    C. FutureBoosting = TSFM预测协变量 + LightGBM最终预测
    """
    print("=" * 60)
    print("FutureBoosting 广东电价预测实验")
    print("=" * 60)
    
    # 1. 数据
    print("\n[1] 生成多变量数据（120天 × 24小时）...")
    df = generate_guangdong_data_with_covariates(days=120)
    print(f"  样本数: {len(df)}")
    print(f"  变量: {df.columns.tolist()}")
    
    # 划分：前90天训练，后30天测试
    split_idx = 90 * 24
    train_df = df.iloc[:split_idx].copy()
    test_df = df.iloc[split_idx:].copy()
    pred_len = len(test_df)
    
    print(f"  训练集: {len(train_df)}步, 测试集: {pred_len}步")
    
    # 2. TSFM零样本预测协变量
    print("\n[2] Stage 1: TSFM零样本预测协变量...")
    
    tsfm_load = tsfm_predict_covariate(train_df['load_gw'].values, pred_len, "负荷(GW)")
    tsfm_temp = tsfm_predict_covariate(train_df['temperature'].values, pred_len, "温度(℃)")
    
    # 截取到测试集长度
    tsfm_load = tsfm_load[:pred_len]
    tsfm_temp = tsfm_temp[:pred_len]
    
    # 3. 构建特征
    print("\n[3] 构建特征矩阵...")
    
    # A: 无TSFM特征
    feat_train_a = build_features(train_df)
    feat_test_a = build_features(test_df)
    
    # C: 有TSFM特征（FutureBoosting）
    feat_train_c = build_features(train_df)
    # 测试集用TSFM预测值填充
    test_df_fb = test_df.copy()
    test_df_fb['load_gw'] = tsfm_load  # 用TSFM预测的负荷替代
    test_df_fb['temperature'] = tsfm_temp
    feat_test_c = build_features(test_df_fb, tsfm_load, tsfm_temp)
    
    # 特征列（排除目标和元数据）
    exclude_cols = ['price', 'datetime', 'date']
    feature_cols = [c for c in feat_train_a.columns if c not in exclude_cols]
    
    # 对齐列
    common_cols_a = list(set(feature_cols) & set(feat_train_a.columns) & set(feat_test_a.columns))
    common_cols_c = list(set(feature_cols) & set(feat_train_c.columns) & set(feat_test_c.columns))
    
    # 4. 方案A：纯LightGBM
    print("\n[4] 方案A: 纯LightGBM...")
    try:
        import lightgbm as lgb
        
        X_train_a = feat_train_a[common_cols_a]
        y_train_a = feat_train_a['price']
        X_test_a = feat_test_a[common_cols_a]
        y_test = feat_test_a['price'].values
        
        model_a = lgb.LGBMRegressor(
            num_leaves=63,
            learning_rate=0.05,
            n_estimators=500,
            early_stopping_rounds=50,
            verbose=-1,
        )
        model_a.fit(X_train_a, y_train_a,
                    eval_set=[(X_test_a, y_test)],
                    callbacks=[lgb.early_stopping(50), lgb.log_evaluation(0)])
        
        pred_a = model_a.predict(X_test_a)
        print(f"  LightGBM 训练完成")
    except Exception as e:
        print(f"  LightGBM 失败: {e}")
        pred_a = np.full(len(test_df), train_df['price'].mean())
    
    # 5. 方案B：Chronos零样本直接预测电价
    print("\n[5] 方案B: Chronos零样本直接预测电价...")
    tsfm_price = tsfm_predict_covariate(train_df['price'].values, pred_len, "电价")
    pred_b = tsfm_price[:pred_len]
    
    # 6. 方案C：FutureBoosting
    print("\n[6] 方案C: FutureBoosting (TSFM + LightGBM)...")
    try:
        X_train_c = feat_train_c[common_cols_c]
        y_train_c = feat_train_c['price']
        X_test_c = feat_test_c[common_cols_c]
        
        model_c = lgb.LGBMRegressor(
            num_leaves=63,
            learning_rate=0.05,
            n_estimators=500,
            early_stopping_rounds=50,
            verbose=-1,
        )
        model_c.fit(X_train_c, y_train_c,
                    eval_set=[(X_test_c, y_test)],
                    callbacks=[lgb.early_stopping(50), lgb.log_evaluation(0)])
        
        pred_c = model_c.predict(X_test_c)
        print(f"  FutureBoosting 训练完成")
    except Exception as e:
        print(f"  FutureBoosting 失败: {e}")
        pred_c = pred_a
    
    # 7. 评估
    print("\n[7] 评估结果...")
    
    y_test = feat_test_a['price'].values
    min_len = min(len(y_test), len(pred_a), len(pred_b), len(pred_c))
    y_test = y_test[:min_len]
    pred_a = pred_a[:min_len]
    pred_b = pred_b[:min_len]
    pred_c = pred_c[:min_len]
    
    def metrics(y_true, y_pred):
        mae = np.mean(np.abs(y_true - y_pred))
        mse = np.mean((y_true - y_pred) ** 2)
        rmse = np.sqrt(mse)
        mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
        ss_res = np.sum((y_true - y_pred) ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
        return {'MAE': round(mae, 2), 'RMSE': round(rmse, 2), 'MAPE(%)': round(mape, 2), 'R²': round(r2, 4)}
    
    results = pd.DataFrame([
        {'方案': 'A. 纯LightGBM', **metrics(y_test, pred_a)},
        {'方案': 'B. Chronos零样本', **metrics(y_test, pred_b)},
        {'方案': 'C. FutureBoosting', **metrics(y_test, pred_c)},
    ])
    
    print("\n" + "=" * 60)
    print("最终对比结果")
    print("=" * 60)
    print(results.to_string(index=False))
    
    # 保存
    output = '/Users/duchaochao/Desktop/futureboosting_experiment.csv'
    results.to_csv(output, index=False, encoding='utf-8-sig')
    print(f"\n结果已保存: {output}")
    
    # 特征重要性（FutureBoosting）
    print("\n[8] FutureBoosting 特征重要性 Top 10:")
    try:
        importance = pd.Series(model_c.feature_importances_, index=common_cols_c)
        top10 = importance.sort_values(ascending=False).head(10)
        for feat, imp in top10.items():
            tsfm_tag = " ← TSFM" if 'tsfm' in feat.lower() else ""
            print(f"  {feat}: {imp}{tsfm_tag}")
    except:
        pass
    
    return results


if __name__ == "__main__":
    run_futureboosting_experiment()
