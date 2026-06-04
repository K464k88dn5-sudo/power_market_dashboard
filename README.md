# 电力市场多源数据监控大屏

## 数据源接入状态

| 模块 | 数据源 | 接入方式 | 状态 |
|------|--------|---------|------|
| 🌤️ 气象 | Open-Meteo API | REST API（免费，无需Key） | ✅ 已接入 |
| ⛽ 煤价 | CCTD中国煤炭市场网 | POST API（环渤海港口5500K/5000K） | ✅ 已接入 |
| ⛽ LNG | 上海石油天然气交易中心 | POST API（LNG出厂价格指数） | ✅ 已接入 |
| 📊 电价 | 广东电力交易中心/北极星 | 网页爬取（需网络可达） | ⚠️ 参考模板兜底 |
| 🔧 检修 | 调度系统导出 | Excel导入 | ✅ 模板就绪 |

## 快速启动

```bash
cd ~/Desktop/power_market_dashboard
pip install streamlit plotly pandas numpy requests beautifulsoup4 lxml
streamlit run app.py
# 访问 http://localhost:8501
```

## 真实数据API说明

### 煤价 API（CCTD）
```
POST http://www.cctd.com.cn/Echarts/data/HBHCKJ_DLMQH.php
返回: [{name:'日期', age:'5500K价格', product:'5000K价格'}, ...]
```

### LNG API（上海石油天然气交易中心）
```
POST https://www.shpgx.com/marketzhishu/list/3/22
返回: {DATA:'日期', BASEPRICE:'价格(元/吨)'}
```

### 气象 API（Open-Meteo）
```
GET https://api.open-meteo.com/v1/forecast?latitude=23.13&longitude=113.26&hourly=temperature_2m,shortwave_radiation,wind_speed_10m,precipitation&timezone=Asia/Shanghai
```

## 目录结构

```
power_market_dashboard/
├── app.py                      # Streamlit主应用
├── requirements.txt            # 依赖
├── README.md                   # 说明
└── data_sources/               # 数据接口模块
    ├── __init__.py
    ├── weather_api.py          # 气象（Open-Meteo）
    ├── fuel_api.py             # 燃料（CCTD + 上油所）
    ├── price_api.py            # 电价（爬取 + 模板）
    └── maintenance_api.py      # 检修（Excel导入）
```

## 检修数据使用

1. 点击侧边栏"下载检修模板"
2. 用Excel填写检修计划（线路名称、检修类型、开始/结束时间、影响容量MW、影响区域、状态）
3. 上传Excel文件，自动解析展示

## 后续扩展

- [ ] 接入广东电力交易中心日前电价（需解决网络可达性）
- [ ] 接入电价预测模型输出（V10模型）
- [ ] Docker部署
- [ ] 告警推送（电价异常/高温预警）
