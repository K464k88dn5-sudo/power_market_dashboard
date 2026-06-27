"""
气象数据共享缓存模块
- 实时数据页面负责更新缓存
- 电力大屏页面从缓存读取
"""
import json
import os
import pandas as pd
from datetime import datetime, timedelta, timezone
from pathlib import Path

_CN_TZ = timezone(timedelta(hours=8))
CACHE_DIR = Path(__file__).parent
CITIES_CACHE = CACHE_DIR / "weather_cities.json"
CITY_CACHE_TPL = CACHE_DIR / "weather_{city}.json"
CACHE_MAX_AGE_HOURS = 6  # 缓存有效期6小时

def _now():
    return datetime.now(_CN_TZ)

def save_city_weather(city: str, df: pd.DataFrame):
    """保存单城市气象数据到缓存"""
    fp = CITY_CACHE_TPL.with_name(f"weather_{city}.json")
    data = {
        "timestamp": _now().isoformat(),
        "city": city,
        "rows": len(df),
        "data": df.to_dict(orient="records")
    }
    with open(fp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, default=str)

def load_city_weather(city: str, max_age_hours=CACHE_MAX_AGE_HOURS) -> pd.DataFrame:
    """从缓存读取单城市气象数据"""
    fp = CITY_CACHE_TPL.with_name(f"weather_{city}.json")
    if not fp.exists():
        return pd.DataFrame()
    try:
        with open(fp, 'r', encoding='utf-8') as f:
            data = json.load(f)
        ts = datetime.fromisoformat(data["timestamp"])
        if (_now() - ts).total_seconds() > max_age_hours * 3600:
            return pd.DataFrame()  # 缓存过期
        df = pd.DataFrame(data["data"])
        if "时间" in df.columns:
            df["时间"] = pd.to_datetime(df["时间"])
        return df
    except:
        return pd.DataFrame()

def save_cities_weather(cities_data: dict):
    """批量保存多个城市气象数据"""
    for city, df in cities_data.items():
        if not df.empty:
            save_city_weather(city, df)

def load_all_cities_weather(max_age_hours=CACHE_MAX_AGE_HOURS) -> pd.DataFrame:
    """从缓存读取所有城市气象数据"""
    dfs = []
    for fp in CACHE_DIR.glob("weather_*.json"):
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                data = json.load(f)
            ts = datetime.fromisoformat(data["timestamp"])
            if (_now() - ts).total_seconds() > max_age_hours * 3600:
                continue  # 缓存过期
            df = pd.DataFrame(data["data"])
            if "时间" in df.columns:
                df["时间"] = pd.to_datetime(df["时间"])
            dfs.append(df)
        except:
            continue
    if dfs:
        return pd.concat(dfs, ignore_index=True)
    return pd.DataFrame()

def is_cache_fresh(city: str, max_age_hours=CACHE_MAX_AGE_HOURS) -> bool:
    """检查缓存是否新鲜"""
    fp = CITY_CACHE_TPL.with_name(f"weather_{city}.json")
    if not fp.exists():
        return False
    try:
        with open(fp, 'r', encoding='utf-8') as f:
            data = json.load(f)
        ts = datetime.fromisoformat(data["timestamp"])
        return (_now() - ts).total_seconds() <= max_age_hours * 3600
    except:
        return False
