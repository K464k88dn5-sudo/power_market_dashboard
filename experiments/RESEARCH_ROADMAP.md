# TSFM + 电力电价预测 研究路线图

## 研究定位

**创新点：** 国内首个将TSFM应用于电力现货市场电价预测的系统研究
**对标论文：** FutureBoosting (arXiv:2603.06726) — 清华thulab，已在山西市场验证
**目标市场：** 广东电力现货市场（中国最成熟的现货试点之一）

---

## 阶段一：环境搭建与基线建立（1-2周）

### 1.1 TSFM环境配置
```bash
# 核心依赖
pip install timesfm[torch]       # Google TimesFM
pip install chronos-forecasting   # Amazon Chronos
pip install uni2ts               # Salesforce Moirai
pip install lightgbm scikit-learn pandas numpy
```

### 1.2 数据准备
- [ ] 获取广东日前市场电价数据（爬取/购买/合作）
- [ ] 获取协变量数据：气象（Open-Meteo）、负荷（南网公开数据）、煤价（CCTD）
- [ ] 数据清洗、对齐、划分（训练/验证/测试）

### 1.3 基线模型
- [ ] 持久化预测（Persistence）
- [ ] 季节性朴素（Seasonal-Naive）
- [ ] LightGBM（你的V10模型）
- [ ] LSTM / Transformer（标准深度学习基线）

---

## 阶段二：TSFM零样本评估（2-3周）

### 2.1 单模型零样本测试
- [ ] Chronos-Bolt-Base/Small（CPU可运行）
- [ ] TimesFM-2.0（需32GB+ RAM）
- [ ] Moirai-1.0-R-Small/Base
- [ ] Timer-XL（清华，需从HuggingFace加载）

### 2.2 评估维度
| 维度 | 指标 |
|------|------|
| 点预测精度 | MAE, RMSE, MAPE |
| 概率预测 | CRPS, Pinball Loss |
| 计算效率 | 推理时间, GPU显存 |
| 不同场景 | 工作日/周末, 高温日, 节假日 |

### 2.3 输出
- TSFM零样本 vs 传统基线的对比表
- 各TSFM的优劣势分析

---

## 阶段三：FutureBoosting复现与改进（3-4周）

### 3.1 复现原始FutureBoosting
```bash
git clone https://github.com/thulab/FutureBoosting.git
cd FutureBoosting
pip install -r requirements.txt
# 用广东数据替换山西数据
```

### 3.2 改进方向（创新点）
1. **多TSFM集成：** Chronos + TimesFM + Moirai 集成预测协变量
2. **广东特色特征：** 
   - 西电东送通道容量
   - 港澳跨境交易
   - 热带气旋影响（台风季）
3. **动态回归器选择：** 根据市场状态（峰/谷/平）切换LightGBM/线性回归
4. **实时更新机制：** 每日增量更新TSFM预测，而非固定窗口

### 3.3 消融实验
- 固定LightGBM，对比不同TSFM的贡献
- 固定TSFM，对比不同回归器的贡献
- 特征重要性分析（SHAP）

---

## 阶段四：论文撰写（2-3周）

### 4.1 论文框架
```
Title: FutureBoosting for Guangdong Electricity Spot Market: 
       A Time Series Foundation Model Enhanced Forecasting Approach

1. Introduction
   - 电力现货市场电价预测的重要性
   - TSFM的兴起与电力领域应用空白
   - 本文贡献

2. Related Work
   - 传统电价预测方法
   - TSFM综述（TimesFM/Chronos/Moirai/Timer）
   - FutureBoosting范式

3. Methodology
   - 广东电力市场特征分析
   - FutureBoosting框架适配
   - 改进：多TSFM集成 + 广东领域特征

4. Experiments
   - 数据集描述
   - 基线对比
   - 消融实验
   - 可解释性分析

5. Conclusion & Future Work
```

### 4.2 目标期刊/会议
- **期刊：** Applied Energy / Energy / IEEE TPWRS
- **会议：** NeurIPS Workshop / ICML Workshop / EEM

---

## 关键资源

| 资源 | 链接 |
|------|------|
| FutureBoosting代码 | github.com/thulab/FutureBoosting |
| TimesFM | github.com/google-research/timesfm |
| Chronos | github.com/amazon-science/chronos-forecasting |
| Moirai | github.com/SalesforceAIResearch/uni2ts |
| Timer-XL | github.com/thuml/Timer-XL |
| TSFM对比平台 | tsfm.ai/compare |
| TSFM+电价论文 | IEEE EEM 2025 (11050326) |
| FutureBoosting论文 | arXiv:2603.06726 |

---

## 时间线（总计8-12周）

```
Week 1-2:   环境搭建 + 数据准备 + 基线建立
Week 3-5:   TSFM零样本评估 + FutureBoosting复现
Week 6-8:   改进实验 + 消融实验
Week 9-10:  论文撰写
Week 11-12: 修改投稿
```
