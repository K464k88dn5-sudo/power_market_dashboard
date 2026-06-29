"""
数据管理模块
- 实时数据页面：实时获取数据并更新缓存
- 电力大屏：从缓存读取最新数据
"""
import json
import os
import pandas as pd
from datetime import datetime, timedelta, timezone
from pathlib import Path

_CN_TZ = timezone(timedelta(hours=8))

# 导入缓存模块
from data.weather_cache import (
    get_cached_weather, save_weather_cache,
    get_cached_all_cities, save_all_cities_cache,
    get_cached_city, save_city_cache,
    is_cache_fresh
)

# 燃料数据缓存
CACHE_DIR = Path(__file__).parent
FUEL_CACHE = CACHE_DIR / "fuel_cache.json"
FUEL_MAX_AGE = timedelta(hours=2)

def _load_cache(cache_file):
    """加载缓存文件"""
    if not cache_file.exists():
        return None
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None

def _save_cache(cache_file, data):
    """保存缓存文件"""
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, default=str)

def _is_cache_fresh(cache_file, max_age):
    """检查缓存是否新鲜"""
    if not cache_file.exists():
        return False
    try:
        mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
        return (datetime.now() - mtime) < max_age
    except:
        return False


# ============================================================
# 气象数据（实时获取+缓存）
# ============================================================

def get_weather_data(city="广州", forecast_days=2):
    """
    获取气象数据（优先从缓存读取，实时数据页面负责更新）
    """
    # 先从缓存读取
    df = get_cached_weather(city, forecast_days)
    if not df.empty:
        return df
    
    # 缓存为空，从API获取并缓存
    from data_sources.weather_api import fetch_weather_single
    try:
        df = fetch_weather_single(city, forecast_days=forecast_days)
        if not df.empty:
            save_weather_cache(city, forecast_days, df)
        return df
    except Exception as e:
        return pd.DataFrame()

def get_all_cities_weather(forecast_days=2):
    """
    获取所有城市气象数据（优先从缓存读取）
    """
    # 先从缓存读取
    df = get_cached_all_cities()
    if not df.empty:
        return df
    
    # 缓存为空，从API获取并缓存
    from data_sources.weather_api import fetch_all_cities_parallel
    try:
        results, errors = fetch_all_cities_parallel(forecast_days=forecast_days)
        dfs = []
        for city, city_df in results.items():
            if not city_df.empty:
                dfs.append(city_df)
        df = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
        
        if not df.empty:
            save_all_cities_cache(df)
        return df
    except Exception as e:
        return pd.DataFrame()

def get_current_city_temps():
    """
    获取当前城市温度（优先从缓存读取）
    """
    # 先从缓存读取
    df = get_cached_all_cities()
    if not df.empty:
        return df
    
    # 缓存为空，从API获取并缓存
    from data_sources.weather_api import fetch_all_cities_current
    try:
        df = fetch_all_cities_current()
        if not df.empty:
            save_all_cities_cache(df)
        return df
    except Exception as e:
        return pd.DataFrame()


# ============================================================
# 燃料数据
# ============================================================

def get_fuel_data(days=30):
    """
    获取燃料价格数据（优先缓存，过期自动更新）
    """
    from data_sources.fuel_api import build_fuel_display_data
    
    cache_key = f"fuel_{days}d"
    
    # 优先从API获取实时数据
    try:
        df = build_fuel_display_data(days)
        if not df.empty:
            # 更新缓存
            try:
                existing = _load_cache(FUEL_CACHE) or {}
                df_save = df.copy()
                if "日期" in df_save.columns:
                    df_save["日期"] = df_save["日期"].astype(str)
                existing[cache_key] = df_save.to_dict(orient="records")
                _save_cache(FUEL_CACHE, existing)
            except:
                pass
            return df
    except Exception as e:
        pass
    
    # API失败，使用缓存作为兜底
    cached = _load_cache(FUEL_CACHE)
    if cached and cache_key in cached:
        df = pd.DataFrame(cached[cache_key])
        if not df.empty and "日期" in df.columns:
            df["日期"] = pd.to_datetime(df["日期"])
        return df
    
    return pd.DataFrame()

def get_fuel_summary():
    """
    获取燃料价格摘要（优先实时获取，缓存作为兜底）
    """
    from data_sources.fuel_api import get_fuel_latest_summary
    
    cache_key = "fuel_summary"
    
    # 优先从API获取实时数据
    try:
        summary = get_fuel_latest_summary()
        if summary:
            # 更新缓存
            try:
                existing = _load_cache(FUEL_CACHE) or {}
                existing[cache_key] = summary
                _save_cache(FUEL_CACHE, existing)
            except:
                pass
            return summary
    except Exception as e:
        pass
    
    # API失败，使用缓存作为兜底
    cached = _load_cache(FUEL_CACHE)
    if cached and cache_key in cached:
        return cached[cache_key]
    
    return {}
