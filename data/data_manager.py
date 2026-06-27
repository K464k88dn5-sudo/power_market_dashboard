"""
共享数据管理器 - 所有页面共用
自动读写文件缓存，任何页面均可更新
"""
import json
import os
import pandas as pd
from datetime import datetime, timedelta, timezone
from pathlib import Path

_CN_TZ = timezone(timedelta(hours=8))
CACHE_DIR = Path(__file__).parent
WEATHER_CACHE = CACHE_DIR / "weather_cache.json"
FUEL_CACHE = CACHE_DIR / "fuel_cache.json"
WEATHER_MAX_AGE = timedelta(hours=6)   # 气象缓存6小时
FUEL_MAX_AGE = timedelta(hours=2)      # 燃料缓存2小时

def _now():
    return datetime.now(_CN_TZ)

def _is_cache_fresh(cache_file, max_age):
    """检查缓存是否新鲜"""
    if not cache_file.exists():
        return False
    try:
        with open(cache_file, 'r') as f:
            data = json.load(f)
        ts = datetime.fromisoformat(data["timestamp"])
        return (_now() - ts) < max_age
    except:
        return False

def _save_cache(cache_file, data):
    """保存缓存"""
    cache_data = {"timestamp": _now().isoformat(), "data": data}
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(cache_data, f, ensure_ascii=False, default=str)

def _load_cache(cache_file):
    """读取缓存"""
    if not cache_file.exists():
        return None
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)["data"]
    except:
        return None

# ============================================================
# 气象数据
# ============================================================
def get_weather_data(city="广州", forecast_days=2):
    """
    获取气象数据（优先缓存，过期自动更新）
    """
    from data_sources.weather_api import fetch_weather_single
    
    cache_key = f"{city}_{forecast_days}d"
    
    # 检查缓存
    if _is_cache_fresh(WEATHER_CACHE, WEATHER_MAX_AGE):
        cached = _load_cache(WEATHER_CACHE)
        if cached and cache_key in cached:
            df = pd.DataFrame(cached[cache_key])
            if not df.empty and "时间" in df.columns:
                df["时间"] = pd.to_datetime(df["时间"])
            return df
    
    # 缓存过期，从API获取
    df = fetch_weather_single(city, forecast_days=forecast_days)
    
    # 更新缓存
    try:
        existing = _load_cache(WEATHER_CACHE) or {}
        if not df.empty:
            df_save = df.copy()
            if "时间" in df_save.columns:
                df_save["时间"] = df_save["时间"].astype(str)
            existing[cache_key] = df_save.to_dict(orient="records")
        _save_cache(WEATHER_CACHE, existing)
    except:
        pass
    
    return df

def get_all_cities_weather(forecast_days=2):
    """
    获取所有城市气象数据（优先缓存，过期自动更新）
    """
    from data_sources.weather_api import fetch_all_cities_parallel
    
    cache_key = f"all_cities_{forecast_days}d"
    
    # 检查缓存
    if _is_cache_fresh(WEATHER_CACHE, WEATHER_MAX_AGE):
        cached = _load_cache(WEATHER_CACHE)
        if cached and cache_key in cached:
            df = pd.DataFrame(cached[cache_key])
            if not df.empty and "时间" in df.columns:
                df["时间"] = pd.to_datetime(df["时间"])
            return df
    
    # 缓存过期，从API获取
    results, errors = fetch_all_cities_parallel(forecast_days=forecast_days)
    dfs = []
    for city, city_df in results.items():
        if not city_df.empty:
            dfs.append(city_df)
    df = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
    
    # 更新缓存
    try:
        existing = _load_cache(WEATHER_CACHE) or {}
        if not df.empty:
            df_save = df.copy()
            if "时间" in df_save.columns:
                df_save["时间"] = df_save["时间"].astype(str)
            existing[cache_key] = df_save.to_dict(orient="records")
        _save_cache(WEATHER_CACHE, existing)
    except:
        pass
    
    return df

def get_current_city_temps():
    """
    获取当前城市温度（优先缓存，过期自动更新）
    """
    from data_sources.weather_api import fetch_all_cities_current
    
    cache_key = "current_temps"
    
    # 检查缓存（15分钟）
    if _is_cache_fresh(WEATHER_CACHE, timedelta(minutes=15)):
        cached = _load_cache(WEATHER_CACHE)
        if cached and cache_key in cached:
            return pd.DataFrame(cached[cache_key])
    
    # 缓存过期，从API获取
    df = fetch_all_cities_current()
    
    # 更新缓存
    try:
        existing = _load_cache(WEATHER_CACHE) or {}
        if not df.empty:
            existing[cache_key] = df.to_dict(orient="records")
        _save_cache(WEATHER_CACHE, existing)
    except:
        pass
    
    return df


# ============================================================
# 燃料数据
# ============================================================
def get_fuel_data(days=30):
    """
    获取燃料价格数据（优先缓存，过期自动更新）
    """
    from data_sources.fuel_api import build_fuel_display_data
    
    cache_key = f"fuel_{days}d"
    
    # 检查缓存
    if _is_cache_fresh(FUEL_CACHE, FUEL_MAX_AGE):
        cached = _load_cache(FUEL_CACHE)
        if cached and cache_key in cached:
            df = pd.DataFrame(cached[cache_key])
            if not df.empty and "日期" in df.columns:
                df["日期"] = pd.to_datetime(df["日期"])
            return df
    
    # 缓存过期，从API获取
    df = build_fuel_display_data(days)
    
    # 更新缓存
    try:
        existing = _load_cache(FUEL_CACHE) or {}
        if not df.empty:
            df_save = df.copy()
            if "日期" in df_save.columns:
                df_save["日期"] = df_save["日期"].astype(str)
            existing[cache_key] = df_save.to_dict(orient="records")
        _save_cache(FUEL_CACHE, existing)
    except:
        pass
    
    return df

def get_fuel_summary():
    """
    获取燃料价格摘要（优先缓存）
    """
    from data_sources.fuel_api import get_fuel_latest_summary
    
    cache_key = "fuel_summary"
    
    # 检查缓存
    if _is_cache_fresh(FUEL_CACHE, FUEL_MAX_AGE):
        cached = _load_cache(FUEL_CACHE)
        if cached and cache_key in cached:
            return cached[cache_key]
    
    # 缓存过期，从API获取
    summary = get_fuel_latest_summary()
    
    # 更新缓存
    try:
        existing = _load_cache(FUEL_CACHE) or {}
        existing[cache_key] = summary
        _save_cache(FUEL_CACHE, existing)
    except:
        pass
    
    return summary
