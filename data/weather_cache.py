"""
气象数据共享缓存模块
- 实时数据页面负责实时获取并更新缓存
- 电力大屏页面从缓存读取最新数据
"""
import json
import os
import pandas as pd
from datetime import datetime, timedelta, timezone
from pathlib import Path

_CN_TZ = timezone(timedelta(hours=8))
CACHE_DIR = Path(__file__).parent
WEATHER_CACHE = CACHE_DIR / "weather_cache.json"
CACHE_MAX_AGE = timedelta(minutes=30)  # 缓存有效期30分钟

def _now():
    return datetime.now(_CN_TZ)

def _load_cache():
    """加载缓存文件"""
    if not WEATHER_CACHE.exists():
        return {}
    try:
        with open(WEATHER_CACHE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def _save_cache(data):
    """保存缓存文件"""
    with open(WEATHER_CACHE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, default=str)

def is_cache_fresh(key: str) -> bool:
    """检查缓存是否新鲜"""
    cache = _load_cache()
    if key not in cache:
        return False
    try:
        ts = datetime.fromisoformat(cache[key]["timestamp"])
        return (_now() - ts) < CACHE_MAX_AGE
    except:
        return False

def get_cached_weather(city: str, forecast_days: int = 2) -> pd.DataFrame:
    """从缓存获取气象数据"""
    cache = _load_cache()
    key = f"{city}_{forecast_days}d"
    
    if key not in cache:
        return pd.DataFrame()
    
    try:
        ts = datetime.fromisoformat(cache[key]["timestamp"])
        if (_now() - ts) >= CACHE_MAX_AGE:
            return pd.DataFrame()  # 缓存过期
        
        df = pd.DataFrame(cache[key]["data"])
        if not df.empty and "时间" in df.columns:
            df["时间"] = pd.to_datetime(df["时间"])
        return df
    except:
        return pd.DataFrame()

def save_weather_cache(city: str, forecast_days: int, df: pd.DataFrame):
    """保存气象数据到缓存"""
    if df.empty:
        return
    
    cache = _load_cache()
    key = f"{city}_{forecast_days}d"
    
    df_save = df.copy()
    if "时间" in df_save.columns:
        df_save["时间"] = df_save["时间"].astype(str)
    
    cache[key] = {
        "timestamp": _now().isoformat(),
        "city": city,
        "forecast_days": forecast_days,
        "data": df_save.to_dict(orient="records")
    }
    
    _save_cache(cache)

def get_cached_all_cities() -> pd.DataFrame:
    """从缓存获取所有城市温度"""
    cache = _load_cache()
    key = "all_cities_current"
    
    if key not in cache:
        return pd.DataFrame()
    
    try:
        ts = datetime.fromisoformat(cache[key]["timestamp"])
        if (_now() - ts) >= CACHE_MAX_AGE:
            return pd.DataFrame()
        
        return pd.DataFrame(cache[key]["data"])
    except:
        return pd.DataFrame()

def save_all_cities_cache(df: pd.DataFrame):
    """保存所有城市温度到缓存"""
    if df.empty:
        return
    
    cache = _load_cache()
    key = "all_cities_current"
    
    cache[key] = {
        "timestamp": _now().isoformat(),
        "data": df.to_dict(orient="records")
    }
    
    _save_cache(cache)

def get_cached_city(city: str) -> pd.DataFrame:
    """从缓存获取单个城市温度"""
    cache = _load_cache()
    key = f"city_{city}"
    
    if key not in cache:
        return pd.DataFrame()
    
    try:
        ts = datetime.fromisoformat(cache[key]["timestamp"])
        if (_now() - ts) >= CACHE_MAX_AGE:
            return pd.DataFrame()
        
        return pd.DataFrame(cache[key]["data"])
    except:
        return pd.DataFrame()

def save_city_cache(city: str, df: pd.DataFrame):
    """保存单个城市温度到缓存"""
    if df.empty:
        return
    
    cache = _load_cache()
    key = f"city_{city}"
    
    cache[key] = {
        "timestamp": _now().isoformat(),
        "city": city,
        "data": df.to_dict(orient="records")
    }
    
    _save_cache(cache)

def get_cache_status() -> dict:
    """获取缓存状态信息"""
    cache = _load_cache()
    status = {}
    
    for key, value in cache.items():
        try:
            ts = datetime.fromisoformat(value["timestamp"])
            age = _now() - ts
            status[key] = {
                "timestamp": value["timestamp"],
                "age_minutes": age.total_seconds() / 60,
                "is_fresh": age < CACHE_MAX_AGE
            }
        except:
            status[key] = {"error": "invalid cache entry"}
    
    return status

# 兼容旧接口
def load_city_weather(city: str, max_age_hours=6) -> pd.DataFrame:
    """兼容旧接口：从缓存读取单城市气象数据"""
    return get_cached_weather(city, forecast_days=2)

def load_all_cities_weather(max_age_hours=6) -> pd.DataFrame:
    """兼容旧接口：从缓存读取所有城市气象数据"""
    return get_cached_all_cities()
