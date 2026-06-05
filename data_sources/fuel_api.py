"""
燃料价格数据接口 — 真实数据版（改进）
数据源：
  - 实时：CCTD中国煤炭市场网（动力煤5500K）
  - 实时：上海石油天然气交易中心（LNG出厂价）
  - 历史：FRED API（Henry Hub天然气日度 + 布伦特原油日度）
  - 换算：国际价格→国内LNG参考价
"""

import pandas as pd
import requests
import numpy as np
from datetime import datetime, timedelta
import subprocess
import json
import os

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "http://www.cctd.com.cn/",
}

# FRED 指标
FRED_SERIES = {
    "DHHNGSP": "Henry Hub天然气(USD/MMBtu)",
    "DCOILBRENTEU": "布伦特原油(USD/bbl)",
    "PCOALAUUSDM": "纽卡斯尔煤价(USD/吨)",
}


# ============================================================
# 国内实时数据（CCTD + SHPGX）
# ============================================================

def fetch_coal_price_cctd(days: int = 60) -> pd.DataFrame:
    """
    CCTD 环渤海港口动力煤价格（真实API）
    """
    url = "http://www.cctd.com.cn/Echarts/data/HBHCKJ_DLMQH.php"
    try:
        resp = requests.post(url, headers=HEADERS, timeout=15)
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
            records.append({"日期": item["name"], "5500K煤价(元/吨)": p5500, "5000K煤价(元/吨)": p5000})

        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records)
        df["日期"] = pd.to_datetime(df["日期"])
        df = df.sort_values("日期").tail(days).reset_index(drop=True)
        df["煤价环比(%)"] = df["5500K煤价(元/吨)"].pct_change() * 100
        return df
    except Exception as e:
        print(f"[CCTD煤价] 获取失败: {e}")
        return pd.DataFrame()


def fetch_lng_price_shpgx() -> dict:
    """
    上海石油天然气交易中心 LNG出厂价（真实API）
    """
    url = "https://www.shpgx.com/marketzhishu/list/3/22"
    headers = {**HEADERS, "Referer": "https://www.shpgx.com/html/qgjg.html"}
    try:
        resp = requests.post(url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        price = float(data.get("BASEPRICE", 0))
        date_str = data.get("DATA", "")
        return {
            "日期": date_str,
            "LNG出厂价(元/吨)": price,
            "LNG参考价(元/m³)": round(price / 1000 * 1.4, 2),
            "来源": "上海石油天然气交易中心",
        }
    except Exception as e:
        print(f"[LNG价格] 获取失败: {e}")
        return {}


# ============================================================
# FRED 国际价格（历史数据）
# ============================================================

def fetch_fred_series(series_id: str, start_date: str = "2024-01-01") -> pd.DataFrame:
    """
    从FRED获取时间序列（curl方式，避免urllib超时）
    """
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}&cosd={start_date}"
    tmp = f"/tmp/fred_{series_id}.csv"

    try:
        result = subprocess.run(
            ["curl", "-sL", "--connect-timeout", "10", "--max-time", "20", url, "-o", tmp],
            capture_output=True, timeout=30
        )
        if result.returncode != 0:
            print(f"[FRED] curl失败: {series_id}")
            return pd.DataFrame()

        df = pd.read_csv(tmp)
        if df.empty or series_id not in df.columns:
            return pd.DataFrame()

        df = df.rename(columns={"observation_date": "日期", series_id: "value"})
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df["日期"] = pd.to_datetime(df["日期"])
        df = df.dropna(subset=["value"])
        return df
    except Exception as e:
        print(f"[FRED] {series_id} 获取失败: {e}")
        return pd.DataFrame()


def henry_hub_to_lng_cn(hh_price_usd: float, brent_usd: float = None) -> float:
    """
    Henry Hub(USD/MMBtu) → 中国LNG出厂价(元/吨) 估算
    公式：LNG元/吨 = HH × 52 × 7.25 × seasonal_factor
    其中 52 = 1吨LNG ≈ 52 MMBtu, 7.25 = 汇率
    """
    if hh_price_usd is None or hh_price_usd <= 0:
        return 0
    month = datetime.now().month
    if month in [11, 12, 1, 2]:
        sf = 1.15  # 冬季溢价
    elif month in [6, 7, 8]:
        sf = 1.05  # 夏季
    else:
        sf = 1.0
    return hh_price_usd * 52 * 7.25 * sf


def fetch_lng_history(days: int = 60) -> pd.DataFrame:
    """
    获取LNG历史价格（FRED Henry Hub → 国内换算）
    """
    start = (datetime.now() - timedelta(days=days + 10)).strftime("%Y-%m-%d")
    hh_df = fetch_fred_series("DHHNGSP", start)

    if hh_df.empty:
        return pd.DataFrame()

    # 过滤异常值
    hh_df = hh_df[(hh_df["value"] > 0.5) & (hh_df["value"] < 15)]

    # 换算为国内LNG参考价
    hh_df["LNG参考价(元/吨)"] = hh_df["value"].apply(henry_hub_to_lng_cn)
    hh_df["LNG参考价(元/m³)"] = (hh_df["LNG参考价(元/吨)"] / 1000 * 1.4).round(2)
    hh_df = hh_df[["日期", "LNG参考价(元/吨)", "LNG参考价(元/m³)"]].copy()
    hh_df = hh_df.sort_values("日期").tail(days).reset_index(drop=True)

    return hh_df


# ============================================================
# 综合燃料价格（真实数据）
# ============================================================

def build_fuel_display_data(days: int = 60) -> pd.DataFrame:
    """
    构建可视化展示用的燃料价格DataFrame
    煤价：CCTD真实数据
    LNG：上海石油天然气交易中心实时 + FRED历史换算
    """
    # 1. 煤价（CCTD真实）
    coal_df = fetch_coal_price_cctd(days)
    if coal_df.empty:
        return pd.DataFrame()

    result = coal_df[["日期", "5500K煤价(元/吨)", "煤价环比(%)"]].copy()
    result = result.rename(columns={"5500K煤价(元/吨)": "动力煤价格(元/吨)"})

    # 2. LNG价格（实时+历史）
    lng_real = fetch_lng_price_shpgx()
    lng_hist = fetch_lng_history(days)

    if not lng_hist.empty:
        # 用FRED换算的历史数据作为基础
        lng_hist = lng_hist.rename(columns={"LNG参考价(元/吨)": "LNG出厂价(元/吨)"})
        # 合并到result
        result = result.merge(lng_hist[["日期", "LNG出厂价(元/吨)", "LNG参考价(元/m³)"]],
                              on="日期", how="left")

        # 用实时数据覆盖最新值
        if lng_real and lng_real.get("LNG出厂价(元/吨)", 0) > 0:
            latest_idx = result["LNG出厂价(元/吨)"].last_valid_index()
            if latest_idx is not None:
                result.loc[latest_idx, "LNG出厂价(元/吨)"] = lng_real["LNG出厂价(元/吨)"]
                result.loc[latest_idx, "LNG参考价(元/m³)"] = lng_real["LNG参考价(元/m³)"]
    elif lng_real and lng_real.get("LNG出厂价(元/吨)", 0) > 0:
        # FRED不可用，回退到比例推算
        lng_anchor = lng_real["LNG出厂价(元/吨)"]
        lng_m3_anchor = lng_real["LNG参考价(元/m³)"]
        coal_latest = result["动力煤价格(元/吨)"].iloc[-1]
        coal_ratio = result["动力煤价格(元/吨)"] / coal_latest
        result["LNG出厂价(元/吨)"] = (lng_anchor * coal_ratio).round(0)
        result["LNG参考价(元/m³)"] = (lng_m3_anchor * coal_ratio).round(2)

    return result


def get_fuel_latest_summary() -> dict:
    """
    获取最新燃料价格摘要（用于指标卡展示）
    """
    coal_df = fetch_coal_price_cctd(10)
    lng_info = fetch_lng_price_shpgx()

    summary = {
        "煤价最新": None, "煤价环比": None,
        "LNG出厂价": None, "LNG参考价": None,
        "煤价来源": "CCTD环渤海港口",
        "LNG来源": "上海石油天然气交易中心",
    }

    if not coal_df.empty and "5500K煤价(元/吨)" in coal_df.columns:
        summary["煤价最新"] = coal_df["5500K煤价(元/吨)"].iloc[-1]
        if len(coal_df) > 1:
            summary["煤价环比"] = coal_df["5500K煤价(元/吨)"].pct_change().iloc[-1] * 100

    if lng_info:
        summary["LNG出厂价"] = lng_info.get("LNG出厂价(元/吨)")
        summary["LNG参考价"] = lng_info.get("LNG参考价(元/m³)")

    return summary


# ============================================================
# 测试
# ============================================================
if __name__ == "__main__":
    print("=== 燃料价格测试 ===\n")

    print("--- CCTD 煤价（最新5天） ---")
    coal = fetch_coal_price_cctd(5)
    if not coal.empty:
        print(coal.to_string(index=False))

    print("\n--- SHPGX LNG实时 ---")
    lng = fetch_lng_price_shpgx()
    if lng:
        for k, v in lng.items():
            print(f"  {k}: {v}")

    print("\n--- FRED Henry Hub（最新5天） ---")
    hh = fetch_fred_series("DHHNGSP", (datetime.now()-timedelta(days=10)).strftime("%Y-%m-%d"))
    if not hh.empty:
        print(hh.tail(5).to_string(index=False))

    print("\n--- LNG历史换算（最新5天） ---")
    lng_h = fetch_lng_history(30)
    if not lng_h.empty:
        print(lng_h.tail(5).to_string(index=False))
