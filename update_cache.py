#!/usr/bin/env python3
"""
定时更新缓存脚本
用于cron定时任务，每15分钟更新一次气象数据缓存
"""
import sys
import os
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

# 设置路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_CN_TZ = timezone(timedelta(hours=8))
CACHE_DIR = Path(__file__).parent / "data"
WEATHER_CACHE = CACHE_DIR / "weather_cache.json"

def update_weather_cache():
    """更新气象数据缓存"""
    from data_sources.weather_api import fetch_all_cities_current, fetch_weather_single
    from data.weather_cache import save_weather_cache, save_all_cities_cache
    
    print(f"[{datetime.now(_CN_TZ).strftime('%Y-%m-%d %H:%M:%S')}] 开始更新缓存...")
    
    # 1. 更新21地市实时温度
    try:
        df = fetch_all_cities_current()
        if not df.empty:
            save_all_cities_cache(df)
            print(f"  ✅ 地市温度: {len(df)}条")
        else:
            print(f"  ⚠️ 地市温度: 无数据")
    except Exception as e:
        print(f"  ❌ 地市温度: {e}")
    
    # 2. 更新广州气象数据
    try:
        df = fetch_weather_single("广州", forecast_days=2)
        if not df.empty:
            save_weather_cache("广州", 2, df)
            print(f"  ✅ 广州气象: {len(df)}行")
        else:
            print(f"  ⚠️ 广州气象: 无数据")
    except Exception as e:
        print(f"  ❌ 广州气象: {e}")
    
    print(f"[{datetime.now(_CN_TZ).strftime('%Y-%m-%d %H:%M:%S')}] 缓存更新完成")

if __name__ == "__main__":
    update_weather_cache()
