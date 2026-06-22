"""
燃料价格数据管理
包含主数据源、备用数据源和缓存机制
"""

import requests
import pandas as pd
import json
import os
from datetime import datetime, timedelta
import logging

_log = logging.getLogger(__name__)

# 缓存文件路径
CACHE_DIR = os.path.dirname(os.path.abspath(__file__))
COAL_CACHE = os.path.join(CACHE_DIR, "coal_cache.json")
LNG_CACHE = os.path.join(CACHE_DIR, "lng_cache.json")

def fetch_coal_price_cctd(days=60):
    """
    主数据源：CCTD环渤海港口动力煤价格
    """
    try:
        url = "http://www.cctd.com.cn/Echarts/data/HBHCKJ_DLMQH.php"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.post(url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        
        if not isinstance(data, list) or len(data) == 0:
            return pd.DataFrame()
        
        records = []
        for item in data:
            try:
                p5500 = float(item.get("age", "~"))
            except (ValueError, TypeError):
                continue
            try:
                p5000 = float(item.get("product", "~"))
            except (ValueError, TypeError):
                p5000 = None
            records.append({
                "日期": item["name"],
                "5500K煤价(元/吨)": p5500,
                "5000K煤价(元/吨)": p5000
            })
        
        if not records:
            return pd.DataFrame()
        
        df = pd.DataFrame(records)
        df["日期"] = pd.to_datetime(df["日期"])
        df = df.sort_values("日期").tail(days).reset_index(drop=True)
        df["煤价环比(%)"] = df["5500K煤价(元/吨)"].pct_change() * 100
        
        # 保存到缓存
        save_cache(df, COAL_CACHE)
        
        return df
    except Exception as e:
        _log.info(f"[CCTD煤价] 获取失败: {e}")
        return load_cache(COAL_CACHE)

def fetch_lng_price_shpgx():
    """
    主数据源：上海石油天然气交易中心LNG出厂价
    """
    try:
        url = "https://www.shpgx.com/marketzhishu/list/3/22"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.shpgx.com/html/qgjg.html"
        }
        resp = requests.post(url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        
        price = float(data.get("BASEPRICE", 0))
        date_str = data.get("DATA", "")
        
        if price > 0:
            result = {
                "日期": date_str,
                "LNG出厂价(元/吨)": price,
                "LNG参考价(元/m³)": round(price / 1000 * 1.4, 2),
                "来源": "上海石油天然气交易中心"
            }
            # 保存到缓存
            save_cache(result, LNG_CACHE)
            return result
        else:
            return load_cache(LNG_CACHE)
    except Exception as e:
        _log.info(f"[LNG价格] 获取失败: {e}")
        return load_cache(LNG_CACHE)

def save_cache(data, cache_file):
    """保存数据到缓存"""
    try:
        if isinstance(data, pd.DataFrame):
            # 处理DataFrame
            records = []
            for _, row in data.iterrows():
                record = {}
                for col, val in row.items():
                    if isinstance(val, pd.Timestamp):
                        record[col] = val.isoformat()
                    elif pd.isna(val):
                        record[col] = None
                    else:
                        record[col] = val
                records.append(record)
            cache_data = {
                "timestamp": datetime.now().isoformat(),
                "data": records
            }
        elif isinstance(data, dict):
            # 处理字典
            serializable = {}
            for k, v in data.items():
                if isinstance(v, pd.Timestamp):
                    serializable[k] = v.isoformat()
                elif pd.isna(v):
                    serializable[k] = None
                else:
                    serializable[k] = v
            cache_data = {
                "timestamp": datetime.now().isoformat(),
                "data": serializable
            }
        else:
            return
        
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        
        _log.info(f"[缓存] 已保存: {cache_file}")
    except Exception as e:
        _log.info(f"[缓存] 保存失败: {e}")

def load_cache(cache_file, max_hours=48):
    """从缓存加载数据"""
    try:
        if not os.path.exists(cache_file):
            return None
        
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        # 检查缓存是否过期
        cache_time = datetime.fromisoformat(cache_data.get("timestamp", "2000-01-01"))
        if datetime.now() - cache_time > timedelta(hours=max_hours):
            _log.info(f"[缓存] 已过期: {cache_file}")
            return None
        
        data = cache_data.get("data")
        if isinstance(data, list):
            # 是DataFrame缓存
            df = pd.DataFrame(data)
            df["日期"] = pd.to_datetime(df["日期"])
            return df
        else:
            # 是字典缓存
            return data
    except Exception as e:
        _log.info(f"[缓存] 加载失败: {e}")
        return None

def get_coal_price(days=60):
    """获取煤价数据（带缓存）"""
    df = fetch_coal_price_cctd(days)
    if df.empty:
        df = load_cache(COAL_CACHE)
        if df is not None:
            _log.info("[煤价] 使用缓存数据")
    return df if df is not None else pd.DataFrame()

def get_lng_price():
    """获取LNG价格（带缓存）"""
    data = fetch_lng_price_shpgx()
    if not data or data.get('LNG出厂价(元/吨)', 0) == 0:
        data = load_cache(LNG_CACHE)
        if data:
            _log.info("[LNG] 使用缓存数据")
    return data if data else {}

def build_fuel_display_data(days=60):
    """构建可视化展示用的燃料价格DataFrame"""
    coal_df = get_coal_price(days)
    if coal_df.empty:
        return pd.DataFrame()
    
    result = coal_df[["日期", "5500K煤价(元/吨)", "煤价环比(%)"]].copy()
    result = result.rename(columns={"5500K煤价(元/吨)": "动力煤价格(元/吨)"})
    
    # 添加LNG数据
    lng_data = get_lng_price()
    if lng_data and lng_data.get('LNG出厂价(元/吨)', 0) > 0:
        result["LNG出厂价(元/吨)"] = lng_data['LNG出厂价(元/吨)']
        result["LNG参考价(元/m³)"] = lng_data.get('LNG参考价(元/m³)', 0)
    else:
        result["LNG出厂价(元/吨)"] = None
        result["LNG参考价(元/m³)"] = None
    
    return result.tail(days)

def get_fuel_latest_summary():
    """获取燃料价格摘要"""
    coal_df = get_coal_price(10)
    lng_data = get_lng_price()
    
    summary = {
        "煤价最新": None,
        "煤价环比": 0,
        "LNG出厂价": None,
        "LNG参考价": None,
        "煤价来源": "CCTD环渤海港口",
        "LNG来源": "上海石油天然气交易中心"
    }
    
    if not coal_df.empty:
        summary["煤价最新"] = coal_df["5500K煤价(元/吨)"].iloc[-1]
        summary["煤价环比"] = coal_df["煤价环比(%)"].iloc[-1] if "煤价环比(%)" in coal_df.columns else 0
    
    if lng_data:
        summary["LNG出厂价"] = lng_data.get("LNG出厂价(元/吨)")
        summary["LNG参考价"] = lng_data.get("LNG参考价(元/m³)")
    
    return summary

def update_manual_coal_price(date_str, price_5500, price_5000=None):
    """手动更新煤价数据"""
    try:
        # 读取现有缓存
        cached = load_cache(COAL_CACHE)
        if cached is None:
            cached = pd.DataFrame()
        
        # 添加新数据
        new_row = {
            "日期": pd.to_datetime(date_str),
            "5500K煤价(元/吨)": price_5500,
            "5000K煤价(元/吨)": price_5000
        }
        
        if isinstance(cached, pd.DataFrame):
            cached = pd.concat([cached, pd.DataFrame([new_row])], ignore_index=True)
            cached = cached.sort_values("日期").drop_duplicates(subset=["日期"], keep="last")
            cached["煤价环比(%)"] = cached["5500K煤价(元/吨)"].pct_change() * 100
            save_cache(cached, COAL_CACHE)
        
        return True
    except Exception as e:
        _log.info(f"[手动更新] 失败: {e}")
        return False

def update_manual_lng_price(date_str, price):
    """手动更新LNG价格数据"""
    try:
        result = {
            "日期": date_str,
            "LNG出厂价(元/吨)": price,
            "LNG参考价(元/m³)": round(price / 1000 * 1.4, 2),
            "来源": "手动输入"
        }
        save_cache(result, LNG_CACHE)
        return True
    except Exception as e:
        _log.info(f"[手动更新] 失败: {e}")
        return False
