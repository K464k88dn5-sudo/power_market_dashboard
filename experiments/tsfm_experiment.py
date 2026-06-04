"""
TSFM广东电价预测预实验
目标：验证多个TSFM在广东日前电价数据上的零样本预测能力
模型：TimesFM、Chronos-Bolt（轻量版，可本地运行）

运行前提：
    pip install timesfm[torch] chronos-forecasting pandas numpy matplotlib scikit-learn

作者：Mr.Du研究助手
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings("ignore")


# ============================================================
# 第一部分：广东电价数据生成（真实数据接入后替换）
# ============================================================

def generate_guangdong_price_data(days: int = 90, seed: int = 42) -> pd.DataFrame:
    """
    生成广东日前市场模拟电价数据
    基于广东电力市场典型特征：
    - 日内双峰曲线（上午峰10-12，下午峰15-17）
    - 工作日/周末差异
    - 季节性（夏季高温负荷推高电价）
    - 价格区间：100-800元/MWh
    """
    np.random.seed(seed)
    
    hours = list(range(24))
    dates = pd.date_range(end=datetime(2026, 6, 1), periods=days, freq='D')
    
    # 广东典型日前电价基准曲线（元/MWh）
    base_curve = [
        250, 230, 220, 215, 220, 240,   # 0-5: 深夜低谷
        300, 370, 420, 460, 490, 480,   # 6-11: 上午攀升+峰
        440, 410, 420, 450, 490, 470,   # 12-17: 午后+下午峰
        430, 400, 370, 340, 310, 270,   # 18-23: 晚间下降
    ]
    
    records = []
    for d in dates:
        is_weekend = d.weekday() >= 5
        month = d.month
        
        # 周末系数（负荷低，电价低）
        weekend_factor = 0.75 if is_weekend else 1.0
        
        # 季节系数（夏季高）
        seasonal_factor = 1.0 + 0.15 * np.sin((month - 3) * np.pi / 6)
        
        # 日间随机波动
        day_noise = np.random.normal(0, 0.06)
        
        for h in hours:
            price = base_curve[h] * weekend_factor * seasonal_factor * (1 + day_noise)
            price += np.random.normal(0, 18)  # 小时级噪声
            price = max(price, 80)  # 最低价限制
            price = min(price, 800)  # 最高价限制
            
            records.append({
                'date': d.strftime('%Y-%m-%d'),
                'hour': h,
                'datetime': d + timedelta(hours=h),
                'price': round(price, 2),
                'is_weekend': is_weekend,
            })
    
    df = pd.DataFrame(records)
    df['datetime'] = pd.to_datetime(df['datetime'])
    return df


def prepare_series(df: pd.DataFrame) -> np.ndarray:
    """
    将DataFrame转为1D时间序列（按时间排序的电价序列）
    """
    df = df.sort_values('datetime').reset_index(drop=True)
    return df['price'].values


# ============================================================
# 第二部分：TSFM预测模块
# ============================================================

def forecast_with_chronos(series: np.ndarray, pred_len: int = 24) -> dict:
    """
    使用Amazon Chronos-Bolt进行零样本预测
    """
    try:
        import torch
        from chronos import ChronosPipeline
        
        print("[Chronos] 加载模型...")
        pipeline = ChronosPipeline.from_pretrained(
            "amazon/chronos-bolt-base",
            device_map="cpu",  # CPU模式，兼容性更好
        )
        
        context = torch.tensor(series.astype(np.float32))
        
        print(f"[Chronos] 预测未来{pred_len}步...")
        forecast = pipeline.predict(
            context,
            prediction_length=pred_len,
            num_samples=20,
        )
        
        # forecast shape: (num_samples, pred_len)
        median = np.median(forecast[0].numpy(), axis=0)
        q10 = np.percentile(forecast[0].numpy(), 10, axis=0)
        q90 = np.percentile(forecast[0].numpy(), 90, axis=0)
        
        return {
            'model': 'Chronos-Bolt-Base',
            'point_forecast': median,
            'q10': q10,
            'q90': q90,
            'success': True,
        }
    except Exception as e:
        print(f"[Chronos] 失败: {e}")
        return {'model': 'Chronos-Bolt-Base', 'success': False, 'error': str(e)}


def forecast_with_timesfm(series: np.ndarray, pred_len: int = 24) -> dict:
    """
    使用Google TimesFM进行零样本预测
    注意：TimesFM需要≥32GB内存，且不支持Apple Silicon的lingvo后端
    """
    try:
        import timesfm
        
        print("[TimesFM] 加载模型...")
        tfm = timesfm.TimesFm(
            hparams=timesfm.TimesFmHparams(
                backend="cpu",
                per_core_batch_size=32,
                horizon_len=pred_len,
                context_len=512,
                use_positional_embedding=False,
            ),
            checkpoint=timesfm.TimesFmCheckpoint(
                huggingface_repo_id="google/timesfm-2.0-500m-pytorch"
            ),
        )
        
        # TimesFM接受list of 1D arrays
        input_series = [series]
        freq_input = [0]  # 0=高频(daily/hourly)
        
        print(f"[TimesFM] 预测未来{pred_len}步...")
        point_forecast, quantile_forecast = tfm.forecast(
            input_series, freq=freq_input
        )
        
        return {
            'model': 'TimesFM-2.0',
            'point_forecast': point_forecast[0][:pred_len],
            'q10': quantile_forecast[0][:pred_len, 1],  # 10th percentile
            'q90': quantile_forecast[0][:pred_len, -2],  # 90th percentile
            'success': True,
        }
    except Exception as e:
        print(f"[TimesFM] 失败: {e}")
        return {'model': 'TimesFM-2.0', 'success': False, 'error': str(e)}


def forecast_with_persistence(series: np.ndarray, pred_len: int = 24) -> dict:
    """
    持久化预测（Baseline）：用最近24小时值重复作为预测
    """
    last_24 = series[-24:]
    forecast = np.tile(last_24, pred_len // 24 + 1)[:pred_len]
    return {
        'model': 'Persistence (Baseline)',
        'point_forecast': forecast,
        'success': True,
    }


def forecast_with_seasonal_naive(series: np.ndarray, pred_len: int = 24) -> dict:
    """
    季节性朴素预测（Baseline）：用前一天同时刻值
    """
    if len(series) < 24:
        return forecast_with_persistence(series, pred_len)
    
    last_day = series[-24:]
    n_days = pred_len // 24 + 1
    forecast = np.tile(last_day, n_days)[:pred_len]
    
    return {
        'model': 'Seasonal-Naive (Baseline)',
        'point_forecast': forecast,
        'success': True,
    }


# ============================================================
# 第三部分：评估指标
# ============================================================

def calc_metrics(actual: np.ndarray, predicted: np.ndarray) -> dict:
    """计算预测评估指标"""
    actual = np.array(actual, dtype=float)
    predicted = np.array(predicted, dtype=float)
    
    mask = (actual != 0) & (~np.isnan(actual))
    actual = actual[mask]
    predicted = predicted[mask]
    
    if len(actual) == 0:
        return {}
    
    mae = np.mean(np.abs(actual - predicted))
    mse = np.mean((actual - predicted) ** 2)
    rmse = np.sqrt(mse)
    mape = np.mean(np.abs((actual - predicted) / actual)) * 100
    
    # R²
    ss_res = np.sum((actual - predicted) ** 2)
    ss_tot = np.sum((actual - np.mean(actual)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
    
    return {
        'MAE': round(mae, 2),
        'MSE': round(mse, 2),
        'RMSE': round(rmse, 2),
        'MAPE(%)': round(mape, 2),
        'R²': round(r2, 4),
    }


# ============================================================
# 第四部分：主实验流程
# ============================================================

def run_experiment():
    """
    完整实验流程：
    1. 生成/加载数据
    2. 划分训练/测试集
    3. 多模型零样本预测
    4. 评估对比
    """
    print("=" * 60)
    print("TSFM广东电价预测预实验")
    print("=" * 60)
    
    # 1. 数据准备
    print("\n[1/4] 生成广东日前电价数据（90天 × 24小时）...")
    df = generate_guangdong_price_data(days=90)
    series = prepare_series(df)
    print(f"  数据量: {len(series)} 个时间步")
    print(f"  价格范围: {series.min():.0f} ~ {series.max():.0f} 元/MWh")
    print(f"  均值: {series.mean():.0f} 元/MWh")
    
    # 2. 划分
    pred_len = 24  # 预测未来24小时
    train = series[:-pred_len]
    actual = series[-pred_len:]
    
    print(f"\n[2/4] 训练集: {len(train)}步, 测试集: {pred_len}步")
    
    # 3. 多模型预测
    print(f"\n[3/4] 运行多模型零样本预测...")
    
    results = []
    
    # Baseline: 持久化
    r = forecast_with_persistence(train, pred_len)
    if r['success']:
        metrics = calc_metrics(actual, r['point_forecast'])
        results.append({'模型': r['model'], **metrics})
        print(f"  {r['model']}: MAPE={metrics.get('MAPE(%)', 'N/A')}%")
    
    # Baseline: 季节性朴素
    r = forecast_with_seasonal_naive(train, pred_len)
    if r['success']:
        metrics = calc_metrics(actual, r['point_forecast'])
        results.append({'模型': r['model'], **metrics})
        print(f"  {r['model']}: MAPE={metrics.get('MAPE(%)', 'N/A')}%")
    
    # Chronos-Bolt
    r = forecast_with_chronos(train, pred_len)
    if r['success']:
        metrics = calc_metrics(actual, r['point_forecast'])
        results.append({'模型': r['model'], **metrics})
        print(f"  {r['model']}: MAPE={metrics.get('MAPE(%)', 'N/A')}%")
    
    # TimesFM（可能因环境限制失败）
    r = forecast_with_timesfm(train, pred_len)
    if r['success']:
        metrics = calc_metrics(actual, r['point_forecast'])
        results.append({'模型': r['model'], **metrics})
        print(f"  {r['model']}: MAPE={metrics.get('MAPE(%)', 'N/A')}%")
    
    # 4. 结果汇总
    print(f"\n[4/4] 结果汇总")
    print("=" * 60)
    
    if results:
        result_df = pd.DataFrame(results)
        result_df = result_df.sort_values('MAPE(%)')
        print(result_df.to_string(index=False))
        
        # 保存结果
        output_path = '/Users/duchaochao/Desktop/tsfm_experiment_results.csv'
        result_df.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"\n结果已保存: {output_path}")
        
        return result_df
    
    print("所有模型运行失败")
    return pd.DataFrame()


# ============================================================
# 第五部分：可视化（可选）
# ============================================================

def plot_comparison(actual: np.ndarray, predictions: dict, save_path: str = None):
    """
    绘制多模型预测对比图
    predictions: {model_name: forecast_array}
    """
    try:
        import matplotlib.pyplot as plt
        import matplotlib
        matplotlib.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei']
        matplotlib.rcParams['axes.unicode_minus'] = False
        
        fig, axes = plt.subplots(2, 1, figsize=(14, 8), gridspec_kw={'height_ratios': [3, 1]})
        
        x = range(len(actual))
        
        # 上图：预测对比
        ax = axes[0]
        ax.plot(x, actual, 'k-', linewidth=2, label='实际电价', marker='o', markersize=4)
        
        colors = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#feca57']
        for i, (name, pred) in enumerate(predictions.items()):
            ax.plot(x, pred[:len(actual)], '--', color=colors[i % len(colors)],
                    linewidth=1.5, label=name, marker='s', markersize=3)
        
        ax.set_ylabel('电价 (元/MWh)')
        ax.set_title('TSFM广东电价预测对比')
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3)
        
        # 下图：误差
        ax2 = axes[1]
        for i, (name, pred) in enumerate(predictions.items()):
            error = (pred[:len(actual)] - actual) / actual * 100
            ax2.bar([x + i * 0.2 for x in range(len(actual))], error,
                    width=0.2, color=colors[i % len(colors)], alpha=0.7, label=name)
        
        ax2.set_ylabel('预测误差 (%)')
        ax2.set_xlabel('小时')
        ax2.axhline(y=0, color='k', linewidth=0.5)
        ax2.legend(loc='upper right', fontsize=8)
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"图表已保存: {save_path}")
        
        plt.show()
        
    except Exception as e:
        print(f"可视化失败: {e}")


# ============================================================
# 入口
# ============================================================

if __name__ == "__main__":
    result_df = run_experiment()
