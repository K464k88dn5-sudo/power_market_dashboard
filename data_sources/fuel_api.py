"""
燃料价格数据接口 — 与预测模型数据源一致

数据源优先级（与 predict_auto.py / fuel_api.py 对齐）：
  1. 国内参考数据 (domestic_fuel_reference.json) — 月度国内实际价格
  2. CCTD 环渤海港口动力煤日度API — 煤价日度更新
  3. SHPGX 上海石油天然气交易中心 — LNG实时最新值
  4. FRED API (Brent原油 × 校准系数) — LNG历史兜底
"""

import pandas as pd
import requests
import logging

_log = logging.getLogger(fname.split("/")[-1].replace(".py",""))
_log.addHandler(logging.NullHandler())
import numpy as np
from datetime import datetime, timedelta
import subprocess
import json
import os

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "http://www.cctd.com.cn/",
}

# 与预测模型一致的换算系数
COAL_CONV_FACTOR = 5.883  # 纽卡斯尔USD/ton → 国内Q5500元/吨
LNG_CONV_FACTOR = 68.75   # 布伦特USD/bbl → LNG元/吨

# 国内参考数据路径（与预测模型共用）
REF_PATH = os.path.join(os.path.dirname(__file__), "domestic_fuel_reference.json")


# ============================================================
# 国内参考数据（月度实际价格，与预测模型一致）
# ============================================================

def load_domestic_reference() -> dict:
    """加载国内参考燃料价格数据"""
    if not os.path.exists(REF_PATH):
        return {}
    try:
        with open(REF_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        _log.info(f"[国内参考数据] 加载失败: {e}")
        return {}


def get_domestic_lng_for_month(month_key: str) -> float:
    """从国内参考数据获取指定月份的LNG价格"""
    ref = load_domestic_reference()
    return ref.get("gas_lng", {}).get(month_key)


def get_domestic_coal_for_month(month_key: str) -> float:
    """从国内参考数据获取指定月份的煤价"""
    ref = load_domestic_reference()
    return ref.get("coal_price_5500", {}).get(month_key)


# ============================================================
# CCTD 环渤海港口动力煤（日度，与预测模型煤价来源一致）
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
        _log.info(f"[CCTD煤价] 获取失败: {e}")
        return pd.DataFrame()


# ============================================================
# SHPGX LNG实时价格
# ============================================================

def fetch_lng_price_shpgx() -> dict:
    """
    上海石油天然气交易中心 LNG出厂价（真实API，仅最新值）
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
        _log.info(f"[LNG价格] 获取失败: {e}")
        return {}


# ============================================================
# FRED 国际价格（LNG兜底）
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
            _log.info(f"[FRED] curl失败: {series_id}")
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
        _log.info(f"[FRED] {series_id} 获取失败: {e}")
        return pd.DataFrame()


def brent_to_lng_cn(brent_usd: float) -> float:
    """
    布伦特原油(USD/bbl) → 中国LNG出厂价(元/吨)
    与预测模型换算系数一致：LNG_CONV_FACTOR = 68.75
    """
    if brent_usd is None or brent_usd <= 0:
        return 0
    month = datetime.now().month
    if month in [11, 12, 1, 2]:
        sf = 1.15  # 冬季溢价
    elif month in [6, 7, 8]:
        sf = 1.05  # 夏季
    else:
        sf = 1.0
    return brent_usd * LNG_CONV_FACTOR * sf


def fetch_lng_history_fred(days: int = 60) -> pd.DataFrame:
    """
    LNG历史价格兜底（FRED Brent → 国内换算，与预测模型一致）
    """
    start = (datetime.now() - timedelta(days=days + 10)).strftime("%Y-%m-%d")
    brent_df = fetch_fred_series("DCOILBRENTEU", start)

    if brent_df.empty:
        return pd.DataFrame()

    # 过滤异常值
    brent_df = brent_df[(brent_df["value"] > 30) & (brent_df["value"] < 150)]

    # 换算为国内LNG参考价
    brent_df["LNG出厂价(元/吨)"] = brent_df["value"].apply(brent_to_lng_cn).round(0)
    brent_df["LNG参考价(元/m³)"] = (brent_df["LNG出厂价(元/吨)"] / 1000 * 1.4).round(2)
    brent_df = brent_df[["日期", "LNG出厂价(元/吨)", "LNG参考价(元/m³)"]].copy()
    brent_df = brent_df.sort_values("日期").tail(days).reset_index(drop=True)

    return brent_df


# ============================================================
# 综合燃料价格（与预测模型数据源一致）
# ============================================================

def build_fuel_display_data(days: int = 60) -> pd.DataFrame:
    """
    构建可视化展示用的燃料价格DataFrame

    LNG数据源优先级（与预测模型一致）：
      1. domestic_fuel_reference.json — 月度国内实际价格
      2. SHPGX API — 实时最新值覆盖
      3. FRED Brent × 校准系数 — 历史兜底
      4. 煤价比例法 — 缺失值插值

    煤价：CCTD API日度数据（与预测模型煤价来源一致）
    """
    # 1. 煤价（CCTD真实）
    coal_df = fetch_coal_price_cctd(days)
    if coal_df.empty:
        return pd.DataFrame()

    result = coal_df[["日期", "5500K煤价(元/吨)", "煤价环比(%)"]].copy()
    result = result.rename(columns={"5500K煤价(元/吨)": "动力煤价格(元/吨)"})

    # 2. LNG价格 — 优先用国内参考数据（与预测模型一致）
    ref = load_domestic_reference()
    gas_lng_ref = ref.get("gas_lng", {})

    # 为每个月填充参考价格
    result["月份key"] = result["日期"].dt.strftime("%Y-%m")
    result["LNG出厂价(元/吨)"] = result["月份key"].map(gas_lng_ref)
    result["LNG参考价(元/m³)"] = (result["LNG出厂价(元/吨)"] / 1000 * 1.4).round(2)

    # 3. SHPGX实时数据覆盖最新值
    lng_real = fetch_lng_price_shpgx()
    if lng_real and lng_real.get("LNG出厂价(元/吨)", 0) > 0:
        # 找到最新有数据的行，用实时值覆盖
        latest_idx = result["LNG出厂价(元/吨)"].last_valid_index()
        if latest_idx is not None:
            result.loc[latest_idx, "LNG出厂价(元/吨)"] = lng_real["LNG出厂价(元/吨)"]
            result.loc[latest_idx, "LNG参考价(元/m³)"] = lng_real["LNG参考价(元/m³)"]
        else:
            # 月度参考数据全部缺失，直接用实时值
            result.iloc[-1, result.columns.get_loc("LNG出厂价(元/吨)")] = lng_real["LNG出厂价(元/吨)"]
            result.iloc[-1, result.columns.get_loc("LNG参考价(元/m³)")] = lng_real["LNG参考价(元/m³)"]

    # 4. 仍缺失的行，用FRED Brent兜底
    nan_mask = result["LNG出厂价(元/吨)"].isna()
    if nan_mask.any():
        lng_hist = fetch_lng_history_fred(days)
        if not lng_hist.empty:
            result = result.merge(lng_hist, on="日期", how="left", suffixes=("", "_fred"))
            fred_col = "LNG出厂价(元/吨)_fred"
            if fred_col in result.columns:
                result["LNG出厂价(元/吨)"] = result["LNG出厂价(元/吨)"].fillna(result[fred_col])
                result = result.drop(columns=[fred_col])
                # 清理可能产生的重复列
                for col in result.columns:
                    if col.endswith("_fred"):
                        result = result.drop(columns=[col])

    # 5. 仍有缺失 → 煤价比例法插值
    nan_mask = result["LNG出厂价(元/吨)"].isna()
    if nan_mask.any():
        last_valid = result["LNG出厂价(元/吨)"].last_valid_index()
        if last_valid is not None:
            anchor_lng = result.loc[last_valid, "LNG出厂价(元/吨)"]
            anchor_coal = result.loc[last_valid, "动力煤价格(元/吨)"]
            if anchor_coal > 0:
                coal_ratio = result["动力煤价格(元/吨)"] / anchor_coal
                result.loc[nan_mask, "LNG出厂价(元/吨)"] = (anchor_lng * coal_ratio[nan_mask]).round(0)
                result.loc[nan_mask, "LNG参考价(元/m³)"] = (result.loc[nan_mask, "LNG出厂价(元/吨)"] / 1000 * 1.4).round(2)

    # 清理临时列
    result = result.drop(columns=["月份key"], errors="ignore")

    return result


def get_fuel_latest_summary() -> dict:
    """
    获取最新燃料价格摘要（用于指标卡展示）
    数据源与 predict_auto.py 一致
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
    _log.info("=== 燃料价格测试（数据源与预测模型一致）===\n")

    _log.info("--- 国内参考数据 ---")
    ref = load_domestic_reference()
    if ref:
        _log.info(f"  煤价最新月份: {max(ref.get('coal_price_5500', {}).keys())}")
        _log.info(f"  LNG最新月份: {max(ref.get('gas_lng', {}).keys())}")

    _log.info("\n--- CCTD 煤价（最新5天） ---")
    coal = fetch_coal_price_cctd(5)
    if not coal.empty:
        print(coal.to_string(index=False))

    _log.info("\n--- SHPGX LNG实时 ---")
    lng = fetch_lng_price_shpgx()
    if lng:
        for k, v in lng.items():
            _log.info(f"  {k}: {v}")

    _log.info("\n--- 综合燃料数据（最新5天） ---")
    df = build_fuel_display_data(30)
    if not df.empty:
        print(df.tail(5).to_string(index=False))
