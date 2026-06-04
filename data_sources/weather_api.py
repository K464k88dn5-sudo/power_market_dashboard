"""
气象数据接口
数据源：
  - 实时实况：Open-Meteo /v1/forecast?current=...（当前15分钟间隔观测分析）
  - 预报数据：Open-Meteo /v1/forecast?hourly=...（逐时预报）
覆盖广东21地市
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional

# 广东21地市坐标
GUANGDONG_CITIES = {
    "广州": {"lat": 23.13, "lon": 113.26},
    "深圳": {"lat": 22.54, "lon": 114.06},
    "珠海": {"lat": 22.27, "lon": 113.58},
    "汕头": {"lat": 23.35, "lon": 116.68},
    "佛山": {"lat": 23.02, "lon": 113.12},
    "韶关": {"lat": 24.81, "lon": 113.60},
    "湛江": {"lat": 21.27, "lon": 110.36},
    "肇庆": {"lat": 23.05, "lon": 112.47},
    "江门": {"lat": 22.58, "lon": 113.08},
    "茂名": {"lat": 21.66, "lon": 110.93},
    "惠州": {"lat": 23.11, "lon": 114.42},
    "梅州": {"lat": 24.29, "lon": 116.12},
    "汕尾": {"lat": 22.79, "lon": 115.37},
    "河源": {"lat": 23.74, "lon": 114.70},
    "阳江": {"lat": 21.86, "lon": 111.98},
    "清远": {"lat": 23.68, "lon": 113.06},
    "东莞": {"lat": 23.02, "lon": 113.75},
    "中山": {"lat": 22.52, "lon": 113.39},
    "潮州": {"lat": 23.66, "lon": 116.62},
    "揭阳": {"lat": 23.55, "lon": 116.37},
    "云浮": {"lat": 22.92, "lon": 112.04},
}

# WMO 天气代码 → 中文描述
WMO_WEATHER = {
    0: "晴", 1: "大部晴", 2: "多云", 3: "阴",
    45: "雾", 48: "雾凇", 51: "小毛毛雨", 53: "中毛毛雨", 55: "大毛毛雨",
    61: "小雨", 63: "中雨", 65: "大雨", 66: "冻雨小", 67: "冻雨大",
    71: "小雪", 73: "中雪", 75: "大雪", 77: "雪粒",
    80: "小阵雨", 81: "中阵雨", 82: "大阵雨",
    85: "小阵雪", 86: "大阵雪",
    95: "雷暴", 96: "雷暴+小冰雹", 99: "雷暴+大冰雹",
}

# Open-Meteo 预报变量映射
VARIABLES = {
    "temperature_2m": "温度(℃)",
    "shortwave_radiation": "辐照度(W/m²)",
    "wind_speed_10m": "风速(m/s)",
    "precipitation": "降水量(mm)",
    "relative_humidity_2m": "湿度(%)",
    "cloud_cover": "云量(%)",
}

VARIABLE_KEYS = ",".join(VARIABLES.keys())


# ============================================================
# 实时实况数据（Open-Meteo current）
# ============================================================
def fetch_current_observation(city: str) -> dict:
    """
    从 Open-Meteo 获取当前实况数据（15分钟间隔观测分析）
    返回 dict: {"温度": float, "湿度": float, "风速": float, "天气": str, "时间": str}
    """
    coords = GUANGDONG_CITIES.get(city, GUANGDONG_CITIES["广州"])
    try:
        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": coords["lat"],
                "longitude": coords["lon"],
                "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
                "timezone": "Asia/Shanghai",
                "wind_speed_unit": "ms",
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        c = data.get("current", {})
        wmo = c.get("weather_code", 0)
        return {
            "温度": c.get("temperature_2m", 0),
            "湿度": c.get("relative_humidity_2m", 0),
            "风速": c.get("wind_speed_10m", 0),
            "天气": WMO_WEATHER.get(wmo, f"代码{wmo}"),
            "时间": c.get("time", ""),
        }
    except Exception as e:
        print(f"[Open-Meteo] {city} 实况获取失败: {e}")
        return {}


def fetch_all_cities_current() -> pd.DataFrame:
    """
    获取广东21地市当前实况温度
    返回 DataFrame: 城市, adcode, 温度, 湿度, 风速, 天气
    """
    city_adcode = {
        "广州":"440100","韶关":"440200","深圳":"440300","珠海":"440400",
        "汕头":"440500","佛山":"440600","江门":"440700","湛江":"440800",
        "茂名":"440900","肇庆":"441200","惠州":"441300","梅州":"441400",
        "汕尾":"441500","河源":"441600","阳江":"441700","清远":"441800",
        "东莞":"441900","中山":"442000","潮州":"445100","揭阳":"445200","云浮":"445300",
    }

    results = []
    for city in GUANGDONG_CITIES:
        obs = fetch_current_observation(city)
        if obs:
            results.append({
                "城市": city,
                "adcode": city_adcode.get(city, ""),
                "温度": obs["温度"],
                "湿度": obs["湿度"],
                "风速": obs["风速"],
                "天气": obs["天气"],
            })
    return pd.DataFrame(results)


# ============================================================
# 预报数据（Open-Meteo hourly）
# ============================================================
def fetch_weather_single(city: str = "广州", forecast_days: int = 7) -> pd.DataFrame:
    """
    获取单个城市逐时气象预报数据
    返回DataFrame: 时间、温度、辐照度、风速、降水量、湿度、云量
    """
    coords = GUANGDONG_CITIES.get(city, GUANGDONG_CITIES["广州"])

    params = {
        "latitude": coords["lat"],
        "longitude": coords["lon"],
        "hourly": VARIABLE_KEYS,
        "timezone": "Asia/Shanghai",
        "forecast_days": min(forecast_days, 16),
        "wind_speed_unit": "ms",
    }

    try:
        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params=params,
            timeout=15
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[Open-Meteo] {city} 预报获取失败: {e}")
        return pd.DataFrame()

    hourly = data.get("hourly", {})
    if not hourly:
        return pd.DataFrame()

    df = pd.DataFrame({
        "时间": pd.to_datetime(hourly["time"]),
    })

    for api_key, cn_name in VARIABLES.items():
        if api_key in hourly:
            df[cn_name] = hourly[api_key]

    df["城市"] = city
    return df


def fetch_weather_multi(cities: Optional[list] = None, forecast_days: int = 7) -> pd.DataFrame:
    """获取多个城市气象数据（合并）"""
    if cities is None:
        cities = ["广州", "深圳", "佛山", "惠州"]

    frames = []
    for city in cities:
        df = fetch_weather_single(city, forecast_days)
        if not df.empty:
            frames.append(df)

    if not frames:
        return pd.DataFrame()

    return pd.concat(frames, ignore_index=True)


def fetch_weather_guangdong_avg(forecast_days: int = 7) -> pd.DataFrame:
    """获取广东平均气象数据（多城市加权平均）"""
    df = fetch_weather_multi(forecast_days=forecast_days)
    if df.empty:
        return df

    numeric_cols = [c for c in df.columns if c not in ["时间", "城市"]]
    avg_df = df.groupby("时间")[numeric_cols].mean().reset_index()
    avg_df["城市"] = "广东平均"
    return avg_df


# ============================================================
# 测试
# ============================================================
if __name__ == "__main__":
    print("=== 测试实时实况（Open-Meteo current）===")
    obs = fetch_current_observation("广州")
    print(f"广州实况: {obs}")

    print("\n=== 测试预报（Open-Meteo hourly）===")
    df = fetch_weather_single("广州", forecast_days=2)
    print(f"获取到 {len(df)} 条记录")
    print(df.head(5))
