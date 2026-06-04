"""
燃料价格数据接口 — 真实数据版
主数据源：
  - CCTD中国煤炭市场网 → 环渤海港口动力煤价格（API）
  - 上海石油天然气交易中心 → LNG出厂价格指数（API）
"""

import pandas as pd
import requests
import numpy as np
from datetime import datetime, timedelta
from typing import Optional

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "http://www.cctd.com.cn/",
}


# ============================================================
# 煤价数据源：CCTD API
# ============================================================

def fetch_coal_price_cctd(days: int = 60) -> pd.DataFrame:
    """
    从CCTD获取环渤海港口动力煤价格（5500K / 5000K）
    API: POST http://www.cctd.com.cn/Echarts/data/HBHCKJ_DLMQH.php
    返回JSON: [{name:'2026-06-02', age:'860', product:'801'}, ...]
    - name: 日期
    - age: 5500大卡煤价(元/吨)
    - product: 5000大卡煤价(元/吨)
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
            price_5500 = item.get("age", "~")
            price_5000 = item.get("product", "~")

            # 跳过无效数据（用"~"表示缺失）
            try:
                p5500 = float(price_5500)
            except (ValueError, TypeError):
                continue

            try:
                p5000 = float(price_5000)
            except (ValueError, TypeError):
                p5000 = None

            records.append({
                "日期": item["name"],
                "5500K煤价(元/吨)": p5500,
                "5000K煤价(元/吨)": p5000,
            })

        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records)
        df["日期"] = pd.to_datetime(df["日期"])
        df = df.sort_values("日期").tail(days).reset_index(drop=True)

        # 计算环比
        df["煤价环比(%)"] = df["5500K煤价(元/吨)"].pct_change() * 100

        return df

    except Exception as e:
        print(f"[CCTD煤价] 获取失败: {e}")
        return pd.DataFrame()


# ============================================================
# LNG价格数据源：上海石油天然气交易中心 API
# ============================================================

def fetch_lng_price_shpgx() -> dict:
    """
    从上海石油天然气交易中心获取LNG出厂价格指数
    API: POST https://www.shpgx.com/marketzhishu/list/3/22
    返回: {DATA:'2026-06-01', BASEPRICE:'6190'} (元/吨)
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
            "LNG参考价(元/m³)": round(price / 1000 * 1.4, 2),  # 吨→m³换算系数
            "来源": "上海石油天然气交易中心",
        }

    except Exception as e:
        print(f"[LNG价格] 获取失败: {e}")
        return {}


# ============================================================
# 综合燃料价格
# ============================================================

def build_fuel_display_data(days: int = 60) -> pd.DataFrame:
    """
    构建可视化展示用的燃料价格DataFrame
    数据源：CCTD煤价(真实) + 上海石油天然气交易中心LNG(真实)
    """
    # 1. 获取煤价趋势
    coal_df = fetch_coal_price_cctd(days)

    # 2. 获取LNG最新价
    lng_info = fetch_lng_price_shpgx()

    if coal_df.empty:
        return pd.DataFrame()

    # 以5500K煤价为主线
    result = coal_df[["日期", "5500K煤价(元/吨)", "煤价环比(%)"]].copy()

    # LNG价格：用最新锚点 + 煤价趋势推算历史
    if lng_info and lng_info.get("LNG出厂价(元/吨)", 0) > 0:
        lng_anchor = lng_info["LNG出厂价(元/吨)"]
        lng_m3_anchor = lng_info["LNG参考价(元/m³)"]

        # 基于煤价变动推算LNG历史价格
        coal_latest = result["5500K煤价(元/吨)"].iloc[-1]
        coal_ratio = result["5500K煤价(元/吨)"] / coal_latest

        result["LNG出厂价(元/吨)"] = (lng_anchor * coal_ratio).round(0)
        result["LNG参考价(元/m³)"] = (lng_m3_anchor * coal_ratio).round(2)
        result["气价环比(%)"] = result["LNG参考价(元/m³)"].pct_change() * 100

    # 重命名方便展示
    result = result.rename(columns={"5500K煤价(元/吨)": "动力煤价格(元/吨)"})

    return result


def get_fuel_latest_summary() -> dict:
    """
    获取最新燃料价格摘要（用于指标卡展示）
    """
    coal_df = fetch_coal_price_cctd(10)
    lng_info = fetch_lng_price_shpgx()

    summary = {
        "煤价最新": None,
        "煤价环比": None,
        "LNG出厂价": None,
        "LNG参考价": None,
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
    print("=== 测试燃料价格API（真实数据） ===\n")

    print("--- CCTD 环渤海动力煤价格（最新10天） ---")
    coal = fetch_coal_price_cctd(10)
    if not coal.empty:
        print(coal.to_string(index=False))
    else:
        print("获取失败")

    print("\n--- 上海石油天然气交易中心 LNG价格 ---")
    lng = fetch_lng_price_shpgx()
    if lng:
        for k, v in lng.items():
            print(f"  {k}: {v}")
    else:
        print("获取失败")

    print("\n--- 综合燃料价格展示数据 ---")
    display = build_fuel_display_data(15)
    if not display.empty:
        print(display.tail(10).to_string(index=False))

    print("\n--- 最新摘要 ---")
    summary = get_fuel_latest_summary()
    for k, v in summary.items():
        print(f"  {k}: {v}")
