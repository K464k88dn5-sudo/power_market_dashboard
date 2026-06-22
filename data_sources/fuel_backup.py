"""
备用燃料价格数据源
当主数据源不可用时使用
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
import json
import os

def fetch_coal_price_backup():
    """
    备用煤价数据源 - 从其他网站获取
    返回: DataFrame with columns [日期, 动力煤价格(元/吨), 煤价环比(%)]
    """
    # 尝试从金十数据或其他来源获取
    try:
        # 这里可以添加其他煤价数据源
        # 例如：金十数据、Wind、东方财富等
        pass
    except Exception as e:
        print(f"备用煤价数据源失败: {e}")
    
    return pd.DataFrame()

def fetch_lng_price_backup():
    """
    备用LNG价格数据源
    返回: dict with keys [日期, LNG出厂价(元/吨), LNG参考价(元/m³)]
    """
    # 尝试从其他来源获取
    try:
        # 例如：隆众资讯、百川盈孚等
        pass
    except Exception as e:
        print(f"备用LNG数据源失败: {e}")
    
    return {}

def get_cached_fuel_data(cache_file="fuel_cache.json", max_age_hours=24):
    """
    获取缓存的燃料价格数据
    当API不可用时使用缓存数据
    """
    cache_path = os.path.join(os.path.dirname(__file__), cache_file)
    
    if not os.path.exists(cache_path):
        return None
    
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        # 检查缓存是否过期
        cache_time = datetime.fromisoformat(cache_data.get('timestamp', '2000-01-01'))
        if datetime.now() - cache_time > timedelta(hours=max_age_hours):
            print("缓存数据已过期")
            return None
        
        return cache_data
    except Exception as e:
        print(f"读取缓存失败: {e}")
        return None

def save_fuel_cache(data, cache_file="fuel_cache.json"):
    """
    保存燃料价格数据到缓存
    """
    cache_path = os.path.join(os.path.dirname(__file__), cache_file)
    
    try:
        # 转换DataFrame为可序列化的格式
        serializable_data = {}
        for key, value in data.items():
            if isinstance(value, pd.DataFrame):
                # 转换DataFrame为字典列表，处理Timestamp
                records = []
                for _, row in value.iterrows():
                    record = {}
                    for col, val in row.items():
                        if isinstance(val, pd.Timestamp):
                            record[col] = val.isoformat()
                        elif pd.isna(val):
                            record[col] = None
                        else:
                            record[col] = val
                    records.append(record)
                serializable_data[key] = records
            elif isinstance(value, dict):
                # 处理字典中的Timestamp
                serializable_dict = {}
                for k, v in value.items():
                    if isinstance(v, pd.Timestamp):
                        serializable_dict[k] = v.isoformat()
                    elif pd.isna(v):
                        serializable_dict[k] = None
                    else:
                        serializable_dict[k] = v
                serializable_data[key] = serializable_dict
            else:
                serializable_data[key] = value
        
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'data': serializable_data
        }
        
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        
        print(f"缓存已保存: {cache_path}")
    except Exception as e:
        print(f"保存缓存失败: {e}")

def get_fuel_price_with_fallback():
    """
    获取燃料价格，带备用方案
    优先级：主API -> 备用API -> 缓存数据
    """
    # 1. 尝试主数据源
    from data_sources.fuel_api import fetch_coal_price_cctd, fetch_lng_price_shpgx
    
    coal_df = fetch_coal_price_cctd(60)
    lng_data = fetch_lng_price_shpgx()
    
    # 检查主数据源是否正常
    coal_ok = not coal_df.empty
    lng_ok = lng_data and lng_data.get('LNG出厂价(元/吨)', 0) > 0
    
    if coal_ok and lng_ok:
        # 主数据源正常，保存缓存
        save_fuel_cache({
            'coal': coal_df.to_dict('records'),
            'lng': lng_data
        })
        return coal_df, lng_data
    
    # 2. 主数据源异常，尝试备用数据源
    print("主数据源异常，尝试备用数据源...")
    
    if not coal_ok:
        backup_coal = fetch_coal_price_backup()
        if not backup_coal.empty:
            coal_df = backup_coal
            coal_ok = True
    
    if not lng_ok:
        backup_lng = fetch_lng_price_backup()
        if backup_lng:
            lng_data = backup_lng
            lng_ok = True
    
    # 3. 备用数据源也失败，使用缓存
    if not coal_ok or not lng_ok:
        print("备用数据源失败，使用缓存数据...")
        cached = get_cached_fuel_data()
        if cached:
            if not coal_ok and 'coal' in cached['data']:
                coal_df = pd.DataFrame(cached['data']['coal'])
                coal_ok = True
            if not lng_ok and 'lng' in cached['data']:
                lng_data = cached['data']['lng']
                lng_ok = True
    
    return coal_df, lng_data
