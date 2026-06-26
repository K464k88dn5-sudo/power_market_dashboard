"""
电力市场多源数据监控大屏 — 单屏紧凑版（无滚动）
运行：streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, date as _date, timedelta, timezone

# 北京时间（Streamlit Cloud 服务器在美国，需强制 UTC+8）
_CN_TZ = timezone(timedelta(hours=8))
def _now(): return datetime.now(_CN_TZ)
import json, copy, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_sources import (
    fetch_weather_single, GUANGDONG_CITIES, fetch_electricity_data,
    fetch_all_cities_current,
    load_maintenance_from_excel, get_maintenance_template,
    save_maintenance_template, calculate_security_margin,
    generate_guangdong_price_template,
)
from data_sources.fuel_manager import build_fuel_display_data, get_fuel_latest_summary

# ============================================================
# 页面配置 & 自动刷新
# ============================================================
st.set_page_config(page_title="电力市场监控大屏", page_icon="⚡", layout="wide",
                   initial_sidebar_state="collapsed")

from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=5 * 60 * 1000, key="auto_refresh")

# 刷新倒计时进度条
st.markdown('<div class="refresh-bar-wrap"><div class="refresh-bar"></div></div>', unsafe_allow_html=True)


# ============================================================
# 全局样式 — 极致紧凑，无滚动
# ============================================================
st.markdown("""
<style>
    /* ===== macOS Sequoia Neumorphic 极简风 ===== */

    /* 全局 */
    .stApp {
        background: #F5F5F7 !important;
    }
    .block-container {
        padding: 0 1.2rem 0.8rem !important;
        max-width: 100% !important;
    }

    /* 隐藏侧边栏导航，改为顶部显示 */
    [data-testid="stSidebarNav"] {
        display: none !important;
    }
    section[data-testid="stSidebar"] {
        display: none !important;
    }
    /* 自定义顶部导航栏 */
    .top-nav {
        display: flex;
        gap: 8px;
        padding: 6px 0;
        margin-bottom: 8px;
    }
    .top-nav a {
        padding: 4px 12px;
        border-radius: 8px;
        font-size: 0.75rem;
        color: #1D1D1F;
        text-decoration: none;
        background: rgba(255,255,255,0.8);
        border: 1px solid #E5E5EA;
        transition: all 0.2s;
    }
    .top-nav a:hover {
        background: #007bff;
        color: white;
        border-color: #007bff;
    }
    .top-nav a.active {
        background: #0D7A3F;
        color: white;
        border-color: #0D7A3F;
    }

    /* 标题栏 - 简洁科技风 */
    .dash-header {
        margin-top: 6px;
        background: linear-gradient(135deg, rgba(255,255,255,0.9) 0%, rgba(240,242,245,0.95) 100%);
        border: 1px solid #E5E5EA;
        border-radius: 14px;
        padding: 8px 16px;
        margin-bottom: 12px;
        display: flex; align-items: center; justify-content: center; gap: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.06);
        position: relative;
    }
    .dash-logo {
        height: 28px; flex-shrink: 0;
    }
    .dash-title {
        font-size: 1.15rem; font-weight: 700; color: #1D1D1F;
        letter-spacing: 0.2em;
        white-space: nowrap;
    }
    .dash-time {
        position: absolute; right: 16px;
        font-size: 0.65rem; color: #86868B;
    }

    /* KPI 行 */
    .kpi-bar { display: flex; gap: 0.5rem; margin-bottom: 12px; margin-top: -28px; }
    .kpi-card {
        flex: 1;
        background: rgba(255,255,255,0.78);
        backdrop-filter: blur(20px) saturate(180%);
        border: 1px solid rgba(255,255,255,0.5);
        border-radius: 14px;
        padding: 8px 12px 6px;
        text-align: center;
        box-shadow: 0 1px 2px rgba(0,0,0,0.02), 0 4px 8px rgba(0,0,0,0.04), inset 0 1px 0 rgba(255,255,255,0.8), inset 0 0 12px rgba(255,255,255,0.3);
        transition: all 0.15s cubic-bezier(0.25,0.1,0.25,1);
        position: relative;
        overflow: hidden;
    }
    .kpi-card::after {
        content: "";
        position: absolute;
        top: 0; left: -100%; width: 50%; height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.15), transparent);
        transition: left 0.6s ease;
    }
    .kpi-card:hover::after { left: 100%; }
    .kpi-card:hover {
        transform: translateY(-3px) scale(1.02);
        box-shadow: 0 12px 32px rgba(0,0,0,0.12);
    }
    .kpi-label { font-size: 0.55rem; color: #C7C7CC; }
    .kpi-value { 
        font-size: 0.9rem; font-weight: 700; color: #1D1D1F; 
        font-variant-numeric: tabular-nums;
        letter-spacing: -0.02em;
        text-shadow: 0 1px 2px rgba(0,0,0,0.04);
    }
    .kpi-delta { 
        font-size: 0.55rem; color: #86868B;
        display: flex; align-items: center; justify-content: center; gap: 2px;
        margin-top: 1px;
    }
    .kpi-sparkline { margin-top: 2px; line-height: 0; }

    @keyframes kpi-pulse {
        0%, 100% { box-shadow: 0 1px 2px rgba(0,0,0,0.02); }
        50% { box-shadow: 0 0 0 2px rgba(220,53,69,0.15); }
    }
    .kpi-pulse { animation: kpi-pulse 2s ease-in-out infinite; }
    @keyframes value-flash {
        0% { text-shadow: 0 0 8px rgba(13,122,63,0.5); }
        100% { text-shadow: 0 1px 2px rgba(0,0,0,0.04); }
    }
    .kpi-value-flash { animation: value-flash 0.8s ease-out; }
    .kpi-arrow-up { color: #dc3545; font-size: 0.5rem; }
    .kpi-arrow-dn { color: #0D7A3F; font-size: 0.5rem; }
    .kpi-arrow-flat { color: #C7C7CC; font-size: 0.5rem; }

    /* 模块卡片 */
    .mod-card {
        background: linear-gradient(180deg, #ffffff 0%, #f8f9fa 100%);
        border: 1px solid #ffffff;
        border-radius: 12px;
        padding: 12px;
        margin-bottom: 12px;
        box-shadow: 
            0 1px 2px rgba(0,0,0,0.04),
            0 2px 4px rgba(0,0,0,0.06),
            0 4px 8px rgba(0,0,0,0.08),
            0 8px 16px rgba(0,0,0,0.06);
        transition: all 0.25s cubic-bezier(0.25,0.1,0.25,1);
    }

    /* st.container(border=True) 复用 mod-card 样式 */
    [data-testid="stVerticalBlockBorderWrapper"],
    .stVerticalBlock[style*="border"],
    .stVerticalBlock {
        border-color: #ffffff !important;
    }
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: linear-gradient(180deg, #ffffff 0%, #f8f9fa 100%) !important;
        border-radius: 12px !important;
        padding: 12px 12px 20px 12px !important;
        margin-bottom: 12px !important;
        box-shadow: 
            0 1px 2px rgba(0,0,0,0.04),
            0 2px 4px rgba(0,0,0,0.06),
            0 4px 8px rgba(0,0,0,0.08),
            0 8px 16px rgba(0,0,0,0.06) !important;
    }
    .mod-card:hover {
        box-shadow: 
            0 2px 4px rgba(0,0,0,0.06),
            0 4px 8px rgba(0,0,0,0.08),
            0 8px 16px rgba(0,0,0,0.1),
            0 16px 32px rgba(0,0,0,0.08);
        transform: translateY(-2px);
    }
    .mod-head {
        font-size: 0.7rem; font-weight: 600;
        padding: 0.35rem 0.5rem; margin-bottom: 0.3rem;
        border-bottom: 2px solid #e5e5e7;
        color: #1D1D1F;
        display: flex; align-items: baseline; gap: 8px;
        background: #ffffff;
        border-radius: 8px;
    }
    .mod-sub {
        font-size: 0.5rem; font-weight: 400; color: #C7C7CC;
    }

    /* 图表容器 */
    .stPlotlyChart {
        margin: 0 !important; padding: 0.3rem !important;
        background: rgba(255,255,255,0.5) !important;
        border-radius: 10px !important;
        border: 1px solid rgba(0,0,0,0.06) !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.06);
        overflow: hidden !important;
    }
    .stPlotlyChart > div { background: transparent !important; overflow: hidden !important; }
    .stPlotlyChart .plotly .main-svg { background: transparent !important; }
    [data-testid="stChart"] { background: transparent !important; overflow: hidden !important; }
    [data-testid="stMetricValue"] { font-size: 0.8rem !important; color: #1a1a1a !important; }
    [data-testid="stMetricLabel"] { font-size: 0.55rem !important; color: #666 !important; }
    [data-testid="stMetricDelta"] { font-size: 0.55rem !important; }
    [data-testid="stMetric"] { padding: 0.05rem 0 !important; }

    /* 卡片内图表透明化 — 融入卡片背景 */
    .mod-card .stPlotlyChart,
    [data-testid="stVerticalBlockBorderWrapper"] .stPlotlyChart {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0.15rem !important;
    }

    /* Streamlit 隐藏 */
    #MainMenu, footer { visibility: hidden; }
    .stSpinner, [data-testid="stStatusWidget"] { display: none !important; }
    header[data-testid="stHeader"] { display: none !important; height: 0 !important; margin: 0 !important; padding: 0 !important; }
    [data-testid="stToolbar"] { display: none !important; }
    [data-testid="stDecoration"] { display: none !important; }
    
    /* 完全移除顶部间距 */
    .stApp > header { display: none !important; height: 0 !important; margin: 0 !important; padding: 0 !important; }
    section[data-testid="stMain"] { padding-top: 0 !important; margin-top: 0 !important; }
    .stApp > div { padding-top: 0 !important; margin-top: 0 !important; }
    div[data-testid="stAppViewContainer"] > section { padding-top: 0 !important; margin-top: 0 !important; }
    div[data-testid="stAppViewContainer"] { padding-top: 0 !important; margin-top: 0 !important; }
    div[data-testid="stHeader"] { display: none !important; height: 0 !important; margin: 0 !important; padding: 0 !important; }
    
    /* 隐藏侧边栏头部区域 */
    [data-testid="stSidebarHeader"] { display: none !important; height: 0 !important; margin: 0 !important; padding: 0 !important; }
    [data-testid="stLogoSpacer"] { display: none !important; height: 0 !important; margin: 0 !important; padding: 0 !important; }
    [data-testid="stSidebarCollapseButton"] { display: none !important; height: 0 !important; margin: 0 !important; padding: 0 !important; }
    
    /* 隐藏侧边栏导航区域 */
    [data-testid="stSidebarNav"] { display: none !important; height: 0 !important; margin: 0 !important; padding: 0 !important; }
    [data-testid="stSidebarNavItems"] { display: none !important; height: 0 !important; margin: 0 !important; padding: 0 !important; }
    
    /* 移除侧边栏用户内容区域的padding */
    [data-testid="stSidebarUserContent"] { padding-top: 0 !important; margin-top: 0 !important; }
    
    /* 隐藏刷新进度条和CSS样式块的容器 */
    .refresh-bar-wrap { display: none !important; height: 0 !important; margin: 0 !important; padding: 0 !important; }
    
    /* 隐藏autorefresh iframe */
    iframe[title*="autorefresh"] { display: none !important; height: 0 !important; margin: 0 !important; padding: 0 !important; }
    
    /* 隐藏包含autorefresh的容器 */
    .st-key-auto_refresh { display: none !important; height: 0 !important; margin: 0 !important; padding: 0 !important; }
    
    /* 隐藏包含refresh-bar-wrap和CSS样式块的容器 */
    .stElementContainer:has(.refresh-bar-wrap) { display: none !important; height: 0 !important; margin: 0 !important; padding: 0 !important; }
    .stElementContainer:has(.stMarkdownContainer style) { display: none !important; height: 0 !important; margin: 0 !important; padding: 0 !important; }
    .stElementContainer:has(.stMarkdown style) { display: none !important; height: 0 !important; margin: 0 !important; padding: 0 !important; }

    /* folium 地图 — 全面覆盖所有wrapper */
    .stFolium, .stFolium > iframe, .stFolium > div,
    [data-testid="stFolium"], [data-testid="stFolium"] > div,
    [data-testid="stFolium"] > iframe,
    iframe[src*="st_folium"], iframe[src*="st_folium"] + div,
    iframe[src*="streamlit_folium"] {
        background: transparent !important;
        border-radius: 14px;
        overflow: hidden !important;
    }
    /* 隐藏iframe外层所有sibling元素（folium组件常在iframe后追加div） */
    iframe[src*="streamlit_folium"] ~ * {
        display: none !important;
        height: 0 !important;
        width: 0 !important;
    }
    /* 隐藏iframe内所有控件 */
    .stFolium iframe,
    [data-testid="stFolium"] iframe,
    iframe[src*="streamlit_folium"] {
        overflow: hidden !important;
    }
    .stFolium iframe .leaflet-control-zoom,
    .stFolium iframe .leaflet-control-attribution {
        display: none !important;
        visibility: hidden !important;
    }
    /* 地图卡片背景透明，保留边框和阴影 */
    .mod-card-map {
        background: transparent !important;
        border: 1px solid #e5e5e7 !important;
        border-radius: 16px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.02), 0 2px 4px rgba(0,0,0,0.04), 0 4px 8px rgba(0,0,0,0.06) !important;
        padding: 0.6rem !important;
        margin-bottom: 0.6rem !important;
    }

    /* dataframe */
    [data-testid="stDataFrame"] th { background: #F5F5F7 !important; color: #1a1a1a !important; }
    [data-testid="stDataFrame"] td { background: #ffffff !important; color: #1a1a1a !important; }

    /* 刷新进度条 */
    .refresh-bar-wrap {
        position: fixed; bottom: 0; left: 0; width: 100%; height: 2px;
        background: rgba(0,0,0,0.05); z-index: 999;
    }
    .refresh-bar {
        height: 100%; width: 0%;
        background: linear-gradient(90deg, #0D7A3F, #4CAF50);
        animation: refresh-fill 300s linear infinite;
    }
    @keyframes refresh-fill { 0% { width: 0%; } 100% { width: 100%; } }

    /* 页面加载动画 */
    @keyframes fade-in-up {
        from { opacity: 0; transform: translateY(12px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .mod-card { animation: fade-in-up 0.25s cubic-bezier(0.25,0.1,0.25,1) backwards; }
    .kpi-card { animation: fade-in-up 0.25s cubic-bezier(0.25,0.1,0.25,1) backwards; }
    .dash-header {
        margin-top: 6px; animation: fade-in-up 0.15s cubic-bezier(0.25,0.1,0.25,1) backwards; }
    .kpi-card:nth-child(1) { animation-delay: 0.05s; }
    .kpi-card:nth-child(2) { animation-delay: 0.08s; }
    .kpi-card:nth-child(3) { animation-delay: 0.11s; }
    .kpi-card:nth-child(4) { animation-delay: 0.14s; }
    .kpi-card:nth-child(5) { animation-delay: 0.17s; }

    /* 滚动条美化 */
    ::-webkit-scrollbar { width: 5px; }
    ::-webkit-scrollbar-track { background: rgba(0,0,0,0.02); border-radius: 3px; }
    ::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.12); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(0,0,0,0.2); }

    /* 日期选择器+按钮对齐 */
    [data-testid="stSelectbox"] { margin-bottom: 0 !important; }
    [data-testid="stButton"] { margin-top: 0 !important; padding-top: 0 !important; }
    [data-testid="stButton"] > button { margin-top: 0 !important; }

    /* 按钮组件 */
    .stButton > button {
        background: #FAFAFA !important;
        color: #1D1D1F !important;
        border: 1px solid #E5E5EA !important;
        border-radius: 8px !important;
        padding: 6px 16px !important;
        font-size: 13px !important;
        font-weight: 500 !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03) !important;
        transition: all 0.15s cubic-bezier(0.25,0.1,0.25,1) !important;
    }
    .stButton > button:hover {
        background: #F0F0F0 !important;
        border-color: #D0D0D0 !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08) !important;
    }
    .stButton > button:active {
        background: #E8E8E8 !important;
        transform: scale(0.98) !important;
    }

    /* 数据更新指示器 */
    .data-live::before {
        content: '';
        display: inline-block;
        width: 6px; height: 6px;
        background: #0D7A3F;
        border-radius: 50%;
        margin-right: 4px;
        animation: live-blink 1.5s ease-in-out infinite;
        vertical-align: middle;
    }
    @keyframes live-blink {
        0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(13,122,63,0.4); }
        50% { opacity: 0.4; box-shadow: 0 0 0 3px rgba(13,122,63,0); }
    }

    /* 标题栏光泽扫过 */
    .dash-header::after {
        content: '';
        position: absolute;
        top: 0; left: -100%; width: 60%; height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
        animation: header-shine 6s ease-in-out infinite;
        pointer-events: none;
    }
    @keyframes header-shine {
        0%, 70% { left: -60%; }
        100% { left: 160%; }
    }

    /* 图表卡片悬停微光 */
    .mod-card:hover::after {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        border-radius: 14px;
        box-shadow: inset 0 0 20px rgba(13,122,63,0.03);
        pointer-events: none;
    }

    /* 响应式 */
    @media (max-width: 640px) {
        .block-container { padding: 0.4rem 0.5rem !important; }
        .kpi-bar { flex-direction: column; gap: 0.3rem; }
        .kpi-card { width: 100%; }
        .kpi-sparkline { display: none; }
        .dash-header {
        margin-top: 6px; flex-direction: column; gap: 3px; padding: 0.4rem 0.6rem; }
        .dash-title { font-size: 0.85rem; }
        .dash-time { font-size: 0.5rem; position: static; text-align: center; }
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# Plotly 极简风格模板
import plotly.io as pio

NEUMORPHIC_TEMPLATE = go.layout.Template(
    layout=go.Layout(
        paper_bgcolor="#000000",
        plot_bgcolor="#000000",
        font=dict(family="Inter, SF Pro Display, PingFang SC, sans-serif", color="#000000", size=8),
        title=dict(font=dict(color="#000000", size=10, family="Inter, sans-serif"), x=0.01, xanchor="left"),
        xaxis=dict(
            gridcolor="rgba(0,0,0,0.06)", gridwidth=0.5, griddash="dot",
            zeroline=False,
            linecolor="rgba(0,0,0,0.15)", linewidth=1, showline=True,
            tickfont=dict(color="#888", size=7),
            title=dict(font=dict(color="#000000", size=7)),
        ),
        yaxis=dict(
            gridcolor="rgba(0,0,0,0.06)", gridwidth=0.5, griddash="dot",
            zeroline=False,
            linecolor="rgba(0,0,0,0.15)", linewidth=1, showline=True,
            tickfont=dict(color="#888", size=7),
            title=dict(font=dict(color="#000000", size=7)),
        ),
        hoverlabel=dict(
            bgcolor="#1a1a1a", bordercolor="rgba(0,0,0,0.2)",
            font=dict(color="#ffffff", size=9),
        ),
        legend=dict(
            bgcolor="rgba(255,255,255,0.9)", bordercolor="#e5e5e7",
            font=dict(color="#1a1a1a", size=7),
        ),
        colorway=[
            "#0D7A3F", "#dc3545", "#ffc107", "#007bff",
            "#ff6b35", "#6f42c1", "#20c997", "#e83e8c",
        ],
    ),
)
pio.templates["neumorphic"] = NEUMORPHIC_TEMPLATE
pio.templates.default = "neumorphic"  # 所有新 Figure 自动使用

# ============================================================
# 数据文件路径（优先本地实际路径，兜底项目目录）
# ============================================================
_ACTUAL_PRICE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "日前节点电价.xlsx")
if not os.path.exists(_ACTUAL_PRICE_PATH):
    _ACTUAL_PRICE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "日前节点电价.xlsx")

# ============================================================
# 常量 & 工具函数
# ============================================================
CN_WEEKDAYS = {0:"周一",1:"周二",2:"周三",3:"周四",4:"周五",5:"周六",6:"周日"}
def fmt_date(dt): return f"{dt.month}月{dt.day}日"
def fmt_date_short(dt): return f"{dt.month}月{dt.day}日"

CITY_ADCODE = {
    "广州":"440100","韶关":"440200","深圳":"440300","珠海":"440400",
    "汕头":"440500","佛山":"440600","江门":"440700","湛江":"440800",
    "茂名":"440900","肇庆":"441200","惠州":"441300","梅州":"441400",
    "汕尾":"441500","河源":"441600","阳江":"441700","清远":"441800",
    "东莞":"441900","中山":"442000","潮州":"445100","揭阳":"445200","云浮":"445300",
}

GEO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "guangdong_geo.json")
with open(GEO_PATH, "r", encoding="utf-8") as f:
    GD_GEOJSON = json.load(f)

# ============================================================
# 缓存
# ============================================================
@st.cache_data(ttl=900)
def cached_weather(city, days): return fetch_weather_single(city, days)

@st.cache_data(ttl=900)
def cached_all_cities_temp():
    """获取广东21地市当前实时观测温度（wttr.in气象站实测数据）"""
    return fetch_all_cities_current()

@st.cache_data(ttl=3600)
def cached_fuel(days):
    """获取燃料价格数据，带缓存和备用方案"""
    return build_fuel_display_data(days)
@st.cache_data(ttl=3600)
def cached_fuel_summary(): return get_fuel_latest_summary()
@st.cache_data(ttl=900)
def cached_price(): return fetch_electricity_data()


def parse_maintenance_from_disclosure(target_date: str) -> dict:
    """
    从信息披露xlsx解析检修数据
    返回: {"机组检修": DataFrame, "输变电检修": DataFrame, "检修容量": dict}
    """
    import pandas as _pd
    # 优先从用户本地目录查找，兜底从项目 disclosure/ 目录
    disclosure_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "disclosure")
    if not os.path.exists(disclosure_dir):
        disclosure_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "disclosure")
    fp = os.path.join(disclosure_dir, f"信息披露查询预测信息({target_date}).xlsx")

    result = {"机组检修": _pd.DataFrame(), "输变电检修": _pd.DataFrame(), "检修容量": {}}

    if not os.path.exists(fp):
        return result

    try:
        xl = _pd.ExcelFile(fp)

        # 机组检修预测信息
        sheets = [s for s in xl.sheet_names if "机组检修预测信息" in s]
        if sheets:
            df = _pd.read_excel(fp, sheet_name=sheets[0], header=None, skiprows=1)
            if len(df.columns) >= 7:
                df.columns = ["序号", "电厂名称", "机组名称", "状态类型", "设备改变原因", "开始时间", "结束时间"]
                result["机组检修"] = df[["电厂名称", "机组名称", "状态类型", "开始时间", "结束时间"]].copy()

        # 输变电检修预测信息
        sheets = [s for s in xl.sheet_names if "输变电检修预测信息" in s]
        if sheets:
            df = _pd.read_excel(fp, sheet_name=sheets[0], header=None, skiprows=1)
            if len(df.columns) >= 4:
                df.columns = ["序号", "日期", "元件名称", "电压等级"]
                result["输变电检修"] = df[["元件名称", "电压等级"]].copy()

        # 机组检修容量预测信息
        sheets = [s for s in xl.sheet_names if "机组检修容量" in s]
        if sheets:
            df = _pd.read_excel(fp, sheet_name=sheets[0], header=None, skiprows=1)
            if len(df.columns) >= 4:
                result["检修容量"] = {
                    "总容量": float(df.iloc[0, 2]) if len(df) > 0 else 0,
                    "市场机组容量": float(df.iloc[0, 3]) if len(df) > 0 else 0,
                }
    except Exception as e:
        print(f"[检修数据] 解析失败: {e}")

    return result


# ============================================================
# 侧边栏
# ============================================================
with st.sidebar:
    st.markdown("## ⚙️ 控制面板")
    selected_city = st.selectbox("📍 气象城市", list(GUANGDONG_CITIES.keys()), index=0)
    forecast_days = st.slider("📅 预报天数", 1, 16, 7)
    fuel_days = st.slider("📅 燃料天数", 7, 180, 60)

    st.markdown("---")
    st.markdown("## 📁 数据文件管理")

    # 电价数据文件上传
    st.markdown("### 📊 电价数据")
    price_actual_file = st.file_uploader("上传日前节点电价.xlsx", type=["xlsx"], key="price_actual")
    price_forecast_file = st.file_uploader("上传广东日前电价预测.xlsx", type=["xlsx"], key="price_forecast")

    # 检修数据文件上传
    st.markdown("### 🔧 检修数据")
    disclosure_file = st.file_uploader("上传信息披露文件", type=["xlsx"], key="disclosure")

    # 保存上传的文件
    if price_actual_file:
        with open(_ACTUAL_PRICE_PATH, "wb") as f:
            f.write(price_actual_file.getbuffer())
        st.success("✅ 日前节点电价.xlsx 已上传")

    if price_forecast_file:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "广东日前电价预测.xlsx"), "wb") as f:
            f.write(price_forecast_file.getbuffer())
        st.success("✅ 广东日前电价预测.xlsx 已上传")

    if disclosure_file:
        disclosure_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "disclosure")
        os.makedirs(disclosure_dir, exist_ok=True)
        with open(os.path.join(disclosure_dir, disclosure_file.name), "wb") as f:
            f.write(disclosure_file.getbuffer())
        st.success(f"✅ {disclosure_file.name} 已上传")

    st.markdown("---")
    maint_file = st.file_uploader("🔧 导入检修Excel", type=["xlsx","xls","csv"])
    
    # 燃料价格手动更新
    st.markdown("---")
    st.markdown("### ⛽ 燃料价格手动更新")
    fuel_date = st.date_input("日期", value=datetime.now())
    coal_price = st.number_input("煤价 (元/吨)", value=863, min_value=0, max_value=2000)
    lng_price = st.number_input("LNG出厂价 (元/吨)", value=6200, min_value=0, max_value=10000)
    
    if st.button("💾 更新燃料价格", use_container_width=True):
        from data_sources.fuel_manager import update_manual_coal_price, update_manual_lng_price
        date_str = fuel_date.strftime("%Y-%m-%d")
        
        coal_ok = update_manual_coal_price(date_str, coal_price)
        lng_ok = update_manual_lng_price(date_str, lng_price)
        
        if coal_ok and lng_ok:
            st.success(f"✅ 燃料价格已更新: 煤价{coal_price}元/吨, LNG{lng_price}元/吨")
            st.cache_data.clear()
            st.rerun()
        else:
            st.error("❌ 更新失败")
    
    if st.button("🔄 刷新全部", use_container_width=True):
        st.cache_data.clear(); st.rerun()
    st.caption(f"⏱ {_now().strftime('%H:%M:%S')}")

# ============================================================
# 加载数据
# ============================================================
with st.spinner("加载中..."):
    weather_df = cached_weather(selected_city, forecast_days)
    city_temps = cached_all_cities_temp()
    fuel_df = cached_fuel(fuel_days)
    fuel_summary = cached_fuel_summary()

    # 云存储加载电价数据（GitHub raw URL）
    def _load_from_cloud(url, local_path):
        """从云存储加载数据文件"""
        if os.path.exists(local_path):
            return True  # 本地已有文件
        try:
            import urllib.request
            urllib.request.urlretrieve(url, local_path)
            print(f"[云存储] 已从 {url} 下载到 {local_path}")
            return True
        except Exception as e:
            print(f"[云存储] 下载失败: {e}")
            return False

    # GitHub raw URL（需要替换为实际的仓库地址）
    _github_base = "https://raw.githubusercontent.com/K464k88dn5-sudo/power_market_dashboard/main"
    _actual_local = _ACTUAL_PRICE_PATH
    _forecast_local = os.path.join(os.path.dirname(os.path.abspath(__file__)), "广东日前电价预测.xlsx")

    # 尝试从云存储加载
    _load_from_cloud(f"{_github_base}/日前节点电价.xlsx", _actual_local)
    _load_from_cloud(f"{_github_base}/广东日前电价预测.xlsx", _forecast_local)

    try:
        price_data = cached_price()
    except Exception as e:
        st.warning(f"电价数据加载失败，使用参考模板: {e}")
        from data_sources.price_api import _load_price_cache
        cached = _load_price_cache()
        if cached:
            price_data = cached
        else:
            price_data = {
                "spot_price": generate_guangdong_price_template(),
                "news": pd.DataFrame(),
                "source": "参考模板（数据加载失败）",
            }
maint_df = load_maintenance_from_excel(maint_file) if maint_file else get_maintenance_template()
pdf = price_data.get("spot_price", pd.DataFrame()) if isinstance(price_data, dict) else pd.DataFrame()
mi = calculate_security_margin(maint_df)
margin_val = mi["安全裕度(%)"]
margin_lv = mi["预警等级"]
margin_color = {"充裕":"#2ecc71","偏紧":"#f39c12","紧张":"#e74c3c"}.get(margin_lv,"#888")

# ============================================================
# 标题栏
# ============================================================
sw = '✅' if not weather_df.empty else '❌'
sf = '✅' if not fuel_df.empty else '❌'
sp = '✅' if price_data.get('source') else '❌'

# 加载 logo base64
_logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.png")
if os.path.exists(_logo_path):
    import base64 as _b64
    with open(_logo_path, "rb") as _f:
        _logo_b64 = _b64.b64encode(_f.read()).decode()
    _logo_html = f'<img src="data:image/png;base64,{_logo_b64}" style="height:36px;position:absolute;left:0.8rem;top:50%;transform:translateY(-50%);">'
else:
    _logo_html = ''

# 注入共享样式
from styles import inject_styles
inject_styles()

# 标题栏和导航栏（使用共享模块）
from header_nav import render_header_nav
render_header_nav("电力大屏")

# ============================================================
# KPI 行（实时数据）
# ============================================================
import numpy as _np

def _make_sparkline_svg(values, color="#00d2d3", w=64, h=16, fill=True):
    """生成内联 SVG 迷你趋势图"""
    vals = [v for v in values if v is not None and not (isinstance(v, float) and _np.isnan(v))]
    if len(vals) < 2:
        return ""
    mn, mx = min(vals), max(vals)
    rng = mx - mn if mx != mn else 1
    pts = []
    for i, v in enumerate(vals):
        x = 2 + i * (w - 4) / (len(vals) - 1)
        y = h - 2 - (v - mn) / rng * (h - 4)
        pts.append(f"{x:.1f},{y:.1f}")
    polyline = f'<polyline points="{" ".join(pts)}" fill="none" stroke="{color}" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/>'
    # 填充区域
    fill_poly = ""
    if fill:
        fill_pts = [f"{2:.1f},{h-2:.1f}"] + pts + [f"{w-2:.1f},{h-2:.1f}"]
        grad_id = f'spark_{id(values)}'
    defs = f'<defs><linearGradient id="{grad_id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="{color}" stop-opacity="0.25"/><stop offset="100%" stop-color="{color}" stop-opacity="0.02"/></linearGradient></defs>'
    fill_poly = f'{defs}<polygon points="{" ".join(fill_pts)}" fill="url(#{grad_id})"/>'
    return f'<div class="kpi-sparkline"><svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">{fill_poly}{polyline}</svg></div>'

def _chart_annotation(fig, x, y, text, color="#1a1a1a", position="top center"):
    """Add a value annotation to a chart"""
    fig.add_annotation(
        x=x, y=y, text=text,
        showarrow=False,
        font=dict(size=7, color=color),
        bgcolor="rgba(255,255,255,0.7)",
        bordercolor=color,
        borderwidth=0.5,
        borderpad=2,
        opacity=0.9,
    )

def _kpi_arrow(val, prev, fmt="+.1f"):
    """生成箭头指标 HTML"""
    if prev is None or prev == 0:
        return ""
    diff = val - prev
    pct = diff / abs(prev) * 100
    if abs(pct) < 0.5:
        return f'<span class="kpi-arrow-flat">→ 0%</span>'
    elif pct > 0:
        return f'<span class="kpi-arrow-up">↑ {pct:{fmt}}%</span>'
    else:
        return f'<span class="kpi-arrow-dn">↓ {pct:{fmt}}%</span>'
from data_sources.weather_api import fetch_current_observation as _fco

# 当前城市实时温度
_real_obs = _fco(selected_city)
_real_temp = _real_obs.get("温度", None)
_real_weather = _real_obs.get("天气", "")

kpi = '<div class="kpi-bar">'

# --- 温度 KPI（sparkline来自逐时温度，脉冲>35℃）---
if _real_temp is not None:
    _temp_pulse = ' kpi-pulse' if _real_temp >= 35 else ''
    _temp_sp = ""
    if not weather_df.empty and "温度(℃)" in weather_df.columns:
        _recent_t = weather_df["温度(℃)"].tail(24).tolist()
        _temp_sp = _make_sparkline_svg(_recent_t, "#ff6b6b", 64, 14)
    kpi += f'<div class="kpi-card{_temp_pulse}"><div class="kpi-label">🌡️ {selected_city} 实况</div><div class="kpi-value" style="color:#ff6b6b">{_real_temp:.1f}℃</div><div class="kpi-delta" style="color:#888">{_real_weather}</div>{_temp_sp}</div>'

# --- 煤价 KPI（始终显示，无数据时显示N/A）---
if fuel_summary.get("煤价最新"):
    c = fuel_summary["煤价最新"]; ch = fuel_summary.get("煤价环比", 0) or 0
    _coal_arrow = _kpi_arrow(c, c / (1 + ch / 100) if ch != 0 else None)
    _coal_sp = ""
    if not fuel_df.empty and "动力煤价格(元/吨)" in fuel_df.columns:
        _coal_sp = _make_sparkline_svg(fuel_df["动力煤价格(元/吨)"].tail(7).tolist(), "#ff9f43", 64, 14)
    kpi += f'<div class="kpi-card"><div class="kpi-label">动力煤</div><div class="kpi-value" style="color:#ff9f43">{c:.0f}元/吨</div><div class="kpi-delta" style="color:{"#ff6b6b" if ch>0 else "#2ecc71"}">{ch:+.2f}% {_coal_arrow}</div>{_coal_sp}</div>'
else:
    kpi += '<div class="kpi-card"><div class="kpi-label">动力煤</div><div class="kpi-value" style="color:#C7C7CC">N/A</div><div class="kpi-delta" style="color:#C7C7CC">暂无数据</div></div>'

# --- LNG KPI（始终显示，无数据时显示N/A）---
if fuel_summary.get("LNG出厂价"):
    _lng_val = fuel_summary["LNG出厂价"]
    _lng_sp = ""
    if not fuel_df.empty and "LNG出厂价(元/吨)" in fuel_df.columns:
        _lng_sp = _make_sparkline_svg(fuel_df["LNG出厂价(元/吨)"].tail(7).tolist(), "#54a0ff", 64, 14)
    _lng_prev = None
    if not fuel_df.empty and "LNG出厂价(元/吨)" in fuel_df.columns and len(fuel_df) >= 2:
        _lng_prev = fuel_df["LNG出厂价(元/吨)"].iloc[-2]
    _lng_arrow = _kpi_arrow(_lng_val, _lng_prev)
    kpi += f'<div class="kpi-card"><div class="kpi-label">LNG</div><div class="kpi-value" style="color:#54a0ff">{_lng_val:.0f}元/吨</div><div class="kpi-delta" style="color:#888">参考{fuel_summary.get("LNG参考价",0):.2f}元/m³ {_lng_arrow}</div>{_lng_sp}</div>'
else:
    kpi += '<div class="kpi-card"><div class="kpi-label">LNG</div><div class="kpi-value" style="color:#C7C7CC">N/A</div><div class="kpi-delta" style="color:#C7C7CC">暂无数据</div></div>'

# --- 电价均价 KPI（sparkline来自日前节点电价最近7天均价，脉冲>500）---
# 优先使用实际电价数据的日期和均价，而非参考模板
_actual_path = _ACTUAL_PRICE_PATH
_elec_sp = ""; _elec_arrow = ""; ld = ""; da = 0
if os.path.exists(_actual_path):
    try:
        _adf = pd.read_excel(_actual_path)
        _hour_cols = [f"{i}时" for i in range(24)]
        _adf["_avg"] = _adf[_hour_cols].mean(axis=1)
        _adf["_date"] = pd.to_datetime(_adf["日期"], errors="coerce")
        _adf = _adf.dropna(subset=["_date"]).sort_values("_date")
        ld = _adf["_date"].max().strftime("%Y-%m-%d")
        da = _adf["_avg"].iloc[-1]
        _elec_sp = _make_sparkline_svg(_adf["_avg"].tail(7).tolist(), "#00d2d3", 64, 14)
        if len(_adf) >= 2:
            _elec_prev = _adf["_avg"].iloc[-2]
            _elec_arrow = _kpi_arrow(da, _elec_prev)
    except Exception:
        pass
# 兜底：用参考模板
if not ld and not pdf.empty and "参考电价(元/MWh)" in pdf.columns:
    ld = pdf["日期"].max(); da = pdf[pdf["日期"] == ld]["参考电价(元/MWh)"].mean()

_elec_pulse = ' kpi-pulse' if da > 500 else ''
kpi += f'<div class="kpi-card{_elec_pulse}"><div class="kpi-label">📊 电价均价</div><div class="kpi-value" style="color:#0D7A3F">{da:.0f}元/MWh</div><div class="kpi-delta" style="color:#888">{ld} {_elec_arrow}</div>{_elec_sp}</div>'

# --- 统调负荷最大值 KPI ---
_load_max_val = None
_load_peak_hour = None
if ld:
    _disclosure_dir_kpi = os.path.join(os.path.dirname(os.path.abspath(__file__)), "disclosure")
    _load_fp_kpi = os.path.join(_disclosure_dir_kpi, f"信息披露查询预测信息({ld}).xlsx")
    if os.path.exists(_load_fp_kpi):
        try:
            _load_sheets_kpi = [s for s in pd.ExcelFile(_load_fp_kpi).sheet_names if "负荷预测" in s]
            if _load_sheets_kpi:
                _load_df_kpi = pd.read_excel(_load_fp_kpi, sheet_name=_load_sheets_kpi[0], header=None, skiprows=1)
                if len(_load_df_kpi) > 0:
                    _load_row_kpi = _load_df_kpi.iloc[0]
                    _load_vals_kpi = _load_row_kpi[2:].tolist()
                    if len(_load_vals_kpi) == 96:
                        _load_hourly_kpi = [_load_vals_kpi[i*4] for i in range(24)]
                    elif len(_load_vals_kpi) == 24:
                        _load_hourly_kpi = _load_vals_kpi
                    else:
                        _load_hourly_kpi = _load_vals_kpi[:24]
                    _load_max_val = max(_load_hourly_kpi)
                    _load_peak_hour = _load_hourly_kpi.index(_load_max_val)
        except Exception:
            pass

if _load_max_val is not None:
    kpi += f'<div class="kpi-card"><div class="kpi-label">⚡ 统调负荷</div><div class="kpi-value" style="color:#dc3545">{_load_max_val:.0f}MW</div><div class="kpi-delta" style="color:#888">峰值{_load_peak_hour}时</div></div>'
else:
    kpi += '<div class="kpi-card"><div class="kpi-label">⚡ 统调负荷</div><div class="kpi-value" style="color:#C7C7CC">N/A</div><div class="kpi-delta" style="color:#C7C7CC">暂无数据</div></div>'

# --- 安全裕度 KPI（脉冲=紧张）---
_margin_pulse = ' kpi-pulse' if margin_lv == "紧张" else ''
kpi += f'<div class="kpi-card{_margin_pulse}"><div class="kpi-label">🛡️ 安全裕度</div><div class="kpi-value" style="color:{margin_color}">{margin_val:.1f}%</div><div class="kpi-delta" style="color:{margin_color}">{margin_lv}</div></div></div>'
st.markdown(kpi, unsafe_allow_html=True)

# ============================================================
# 三列布局：气象+燃料 | 地图+电价 | 检修（等宽）
# ============================================================
col1, col2, col3 = st.columns(3)

# ===== 第一列：气象监测 + 燃料价格 =====
with col1:
    # ----- 气象监测 -----
    with st.container(border=True):
        st.markdown('<div class="mod-head mod-head-w">🌤️ 气象监测<span class="mod-sub">实时数据 · 7天预报</span></div>', unsafe_allow_html=True)
        if weather_df.empty:
            st.warning("数据获取失败")
        else:
            today = _date.today()
            today_df = weather_df[weather_df["时间"].dt.date == today].copy()

            daily = weather_df.copy(); daily["日期"]=daily["时间"].dt.date
            agg = daily.groupby("日期").agg(
                最高=("温度(℃)","max"),最低=("温度(℃)","min"),均温=("温度(℃)","mean"),
                风速=("风速(m/s)","mean") if "风速(m/s)" in daily.columns else ("温度(℃)","mean"),
                湿度=("湿度(%)","mean") if "湿度(%)" in daily.columns else ("温度(℃)","mean"),
            ).reset_index()
            agg["标签"]=agg["日期"].apply(fmt_date)

            wc_left, wc_right = st.columns(2)

            with wc_left:
                fig1 = go.Figure()
                if not today_df.empty:
                    fig1.add_trace(go.Scatter(x=today_df["时间"],y=today_df["温度(℃)"],
                        mode="lines+markers",line=dict(color="#ff6b6b",width=1.5,shape="spline"),marker=dict(size=2),
                        name="气温",fill="tozeroy",fillcolor="rgba(255,107,107,0.1)"))
                    for idx,clr,sym in [(today_df["温度(℃)"].idxmax(),"#ff4444","triangle-up"),
                                         (today_df["温度(℃)"].idxmin(),"#4488ff","triangle-down")]:
                        r=today_df.loc[idx]
                        fig1.add_trace(go.Scatter(x=[r["时间"]],y=[r["温度(℃)"]],mode="markers+text",
                            marker=dict(size=6,color=clr,symbol=sym),text=[f"{r['温度(℃)']:.0f}℃"],
                            textposition="top center" if clr=="#ff4444" else "bottom center",
                            textfont=dict(size=8, color=clr),showlegend=False,cliponaxis=False))
                fig1.update_layout(transition=dict(duration=500, easing="cubic-in-out"), height=130,template="neumorphic",showlegend=False,
                    hovermode="x unified",
                    margin=dict(l=30,r=6,t=32,b=22),font=dict(size=7, color="#000000"),
                    title=dict(text=f"📅 {today.month}月{today.day}日 {CN_WEEKDAYS.get(today.weekday(),'')} 逐时温度(℃)",font=dict(size=9, color="#000000")))
                fig1.update_xaxes(dtick=3600000*3,tickformat="%H")
                # Y轴自适应
                if not today_df.empty:
                    _t_min = today_df["温度(℃)"].min()
                    _t_max = today_df["温度(℃)"].max()
                    _t_pad = max((_t_max - _t_min) * 0.15, 1)
                    fig1.update_yaxes(range=[_t_min - _t_pad, _t_max + _t_pad], dtick=2)
                st.plotly_chart(fig1,use_container_width=True)

                fig2 = go.Figure()
                fig2.add_trace(go.Scatter(x=agg["标签"],y=agg["最高"],name="最高",mode="lines+markers",
                    line=dict(color="#ff6b6b",width=1.5,shape="spline"),marker=dict(size=3)))
                fig2.add_trace(go.Scatter(x=agg["标签"],y=agg["均温"],name="均温",mode="lines+markers",
                    line=dict(color="#ffd93d",width=1.5,dash="dot",shape="spline"),marker=dict(size=2)))
                fig2.add_trace(go.Scatter(x=agg["标签"],y=agg["最低"],name="最低",mode="lines+markers",
                    line=dict(color="#54a0ff",width=1.5,shape="spline"),marker=dict(size=3)))
                fig2.add_trace(go.Scattergl(x=list(agg["标签"])+list(agg["标签"][::-1]),
                    y=list(agg["最高"])+list(agg["最低"][::-1]),fill="toself",fillcolor="rgba(255,107,107,0.08)",
                    line=dict(width=0),showlegend=False,hoverinfo="skip"))
                fig2.update_layout(transition=dict(duration=500, easing="cubic-in-out"), height=130,template="neumorphic",showlegend=False,
                    hovermode="x unified",
                    margin=dict(l=30,r=6,t=26,b=22),font=dict(size=7, color="#000000"),
                    title=dict(text="📊 预报温度趋势(℃)",font=dict(size=9, color="#000000")))
                fig2.update_xaxes(tickfont=dict(size=6, color="#000000"))
                st.plotly_chart(fig2,use_container_width=True)

            with wc_right:
                fig3 = go.Figure()
                if "风速(m/s)" in daily.columns:
                    fig3.add_trace(go.Scatter(x=agg["标签"],y=agg["风速"],name="风速",mode="lines+markers",
                        line=dict(color="#6bcb77",width=1.5,shape="spline"),marker=dict(size=4),
                        fill="tozeroy",fillcolor="rgba(107,203,119,0.1)"))
                fig3.update_layout(transition=dict(duration=500, easing="cubic-in-out"), height=130,template="neumorphic",showlegend=False,
                    hovermode="x unified",
                    margin=dict(l=30,r=6,t=26,b=22),font=dict(size=7, color="#000000"),
                    title=dict(text="🌬️ 预报风速(m/s)",font=dict(size=9, color="#000000")))
                fig3.update_xaxes(tickfont=dict(size=6, color="#000000"))
                st.plotly_chart(fig3,use_container_width=True)

                fig4 = go.Figure()
                if "湿度(%)" in daily.columns:
                    fig4.add_trace(go.Scatter(x=agg["标签"],y=agg["湿度"],name="湿度",mode="lines+markers",
                        line=dict(color="#a29bfe",width=1.5,shape="spline"),marker=dict(size=4),
                        fill="tozeroy",fillcolor="rgba(162,155,254,0.1)"))
                fig4.update_layout(transition=dict(duration=500, easing="cubic-in-out"), height=130,template="neumorphic",showlegend=False,
                    hovermode="x unified",
                    margin=dict(l=30,r=6,t=26,b=22),font=dict(size=7, color="#000000"),
                    title=dict(text="💧 预报湿度(%)",font=dict(size=9, color="#000000")))
                fig4.update_xaxes(tickfont=dict(size=6, color="#000000"))
                # Y轴自适应
                _hum_vals = agg["湿度"].dropna().tolist() if "湿度" in agg.columns else []
                if _hum_vals:
                    _h_min, _h_max = min(_hum_vals), max(_hum_vals)
                    _h_pad = max((_h_max - _h_min) * 0.15, 2)
                    fig4.update_yaxes(range=[max(0, _h_min - _h_pad), min(100, _h_max + _h_pad)])
                st.plotly_chart(fig4,use_container_width=True)

            _obs = _fco(selected_city)
            _cur_t = _obs.get("温度", 0)
            _cur_h = _obs.get("湿度", 0)
            _cur_w = _obs.get("风速", 0)
            _cur_wx = _obs.get("天气", "")
            _min_t = weather_df["温度(℃)"].min()
            _max_t = weather_df["温度(℃)"].max()
            _avg_t = weather_df["温度(℃)"].mean()

            _wx_html = '<div style="display:flex;gap:4px;flex-wrap:wrap;margin-top:2px">'
            for _label,_val,_sub in [("实况温度",f"{_cur_t:.1f}℃",f"{_cur_wx}"),
                                      ("预报均温",f"{_avg_t:.1f}℃",""),
                                      ("预报极值",f"{_min_t:.0f}~{_max_t:.0f}℃",""),
                                      ("实况湿度",f"{_cur_h:.0f}%",""),
                                      ("实况风速",f"{_cur_w:.1f}m/s","")]:
                _sub_s = f'<span style="font-size:0.5rem;color:#888;margin-left:2px">{_sub}</span>' if _sub else ''
                _wx_html += f'<div style="flex:1;text-align:center"><div style="font-size:0.6rem;color:#666">{_label}</div><div style="font-size:0.75rem;color:#1a1a1a">{_val}{_sub_s}</div></div>'
            _wx_html += '</div>'
            st.markdown(_wx_html, unsafe_allow_html=True)

    # ----- 燃料价格 -----
    with st.container(border=True):
        st.markdown('<div class="mod-head mod-head-f">⛽ 燃料价格<span class="mod-sub">CCTD煤价 · SHPGX气价</span></div>', unsafe_allow_html=True)
        if fuel_df.empty: st.warning("数据获取失败")
        else:
            from datetime import timedelta as _td
            fuel_df = fuel_df.copy()
            _cutoff = _now().replace(tzinfo=None) - _td(days=30)
            fuel_df = fuel_df[fuel_df["日期"] >= _cutoff].copy()
            fuel_df["日期标签"] = fuel_df["日期"].apply(fmt_date_short)

            # 煤价
            if "动力煤价格(元/吨)" in fuel_df.columns:
                fig_coal=go.Figure()
                fig_coal.add_trace(go.Scatter(x=fuel_df["日期标签"],y=fuel_df["动力煤价格(元/吨)"],
                    mode="lines+markers",marker=dict(size=3),
                    line=dict(color="#ff9f43",width=1.5,shape="spline"),fill="tozeroy",fillcolor="rgba(255,159,67,0.1)"))

                fig_coal.update_layout(transition=dict(duration=500, easing="cubic-in-out"), height=200,template="neumorphic",showlegend=False,
                    hovermode="x unified",
                    margin=dict(l=30,r=10,t=30,b=30),font=dict(size=8, color="#000000"),
                    title=dict(text="动力煤价格(元/吨)",font=dict(size=10, color="#000000")))
                fig_coal.update_xaxes(tickfont=dict(size=7, color="#000000"))
                # Y轴自适应
                _coal_vals = fuel_df["动力煤价格(元/吨)"].dropna().tolist()
                if _coal_vals:
                    _c_min, _c_max = min(_coal_vals), max(_coal_vals)
                    _c_pad = max((_c_max - _c_min) * 0.1, 5)
                    fig_coal.update_yaxes(range=[_c_min - _c_pad, _c_max + _c_pad])
                # 最新值标注
                _coal_last = fuel_df["动力煤价格(元/吨)"].iloc[-1]
                _coal_last_x = fuel_df["日期标签"].iloc[-1]
                fig_coal.add_annotation(x=_coal_last_x, y=_coal_last, text=f'{_coal_last:.0f}',
                    showarrow=False, font=dict(size=7, color="#ff9f43"),
                    bgcolor="rgba(255,255,255,0.7)", bordercolor="#ff9f43", borderwidth=0.5, borderpad=2,
                    xshift=15, yshift=8)
                st.plotly_chart(fig_coal,use_container_width=True)

            # LNG气价
            if "LNG出厂价(元/吨)" in fuel_df.columns:
                fig_lng=go.Figure()
                fig_lng.add_trace(go.Scatter(x=fuel_df["日期标签"],y=fuel_df["LNG出厂价(元/吨)"],
                    mode="lines+markers",marker=dict(size=3),
                    line=dict(color="#54a0ff",width=1.5,shape="spline"),fill="tozeroy",fillcolor="rgba(84,160,255,0.1)"))

                fig_lng.update_layout(transition=dict(duration=500, easing="cubic-in-out"), height=200,template="neumorphic",showlegend=False,
                    hovermode="x unified",
                    margin=dict(l=30,r=10,t=30,b=30),font=dict(size=8, color="#000000"),
                    title=dict(text="LNG出厂价(元/吨)",font=dict(size=10, color="#000000")))
                fig_lng.update_xaxes(tickfont=dict(size=7, color="#000000"))
                # Y轴自适应
                _lng_vals = fuel_df["LNG出厂价(元/吨)"].dropna().tolist()
                if _lng_vals:
                    _l_min, _l_max = min(_lng_vals), max(_lng_vals)
                    _l_pad = max((_l_max - _l_min) * 0.1, 50)
                    fig_lng.update_yaxes(range=[_l_min - _l_pad, _l_max + _l_pad])
                # 最新值标注
                _lng_last = fuel_df["LNG出厂价(元/吨)"].iloc[-1]
                _lng_last_x = fuel_df["日期标签"].iloc[-1]
                fig_lng.add_annotation(x=_lng_last_x, y=_lng_last, text=f'{_lng_last:.0f}',
                    showarrow=False, font=dict(size=7, color="#54a0ff"),
                    bgcolor="rgba(255,255,255,0.7)", bordercolor="#54a0ff", borderwidth=0.5, borderpad=2,
                    xshift=15, yshift=8)
                st.plotly_chart(fig_lng,use_container_width=True)

            # 数据源信息
            _coal_src = fuel_summary.get("煤价来源", "CCTD")
            _lng_src = fuel_summary.get("LNG来源", "SHPGX")
            _fuel_src_html = f'<span style="font-size:0.6rem;color:#666">煤价来源: **{_coal_src}** | LNG来源: **{_lng_src}**</span>'
            st.markdown(_fuel_src_html, unsafe_allow_html=True)


# ===== 第二列：广东地图 + 检修计划 =====
with col2:
    # ----- 广东地图 -----
    with st.container(border=True):
        st.markdown('<div class="mod-head mod-head-g">🗺️ 广东地市实时温度<span class="mod-sub">21地市 · Open-Meteo</span></div>', unsafe_allow_html=True)
        if city_temps.empty:
            st.warning("数据获取失败")
        else:
            import folium
            from folium.features import GeoJsonTooltip
            from streamlit_folium import st_folium
            from branca.colormap import LinearColormap

            temp_map = {int(r["adcode"]):r["温度"] for _,r in city_temps.iterrows()}
            gd_temp = copy.deepcopy(GD_GEOJSON)
            for f in gd_temp["features"]: f["properties"]["温度"] = temp_map.get(f["properties"]["adcode"],0)

            cmap = LinearColormap(colors=["#2196F3","#00BCD4","#FFC107","#FF9800","#F44336","#B71C1C","#9C27B0"],vmin=18,vmax=40)

            all_c = []
            def ext(c):
                if isinstance(c[0],(int,float)): all_c.append(c)
                else:
                    for x in c: ext(x)
            for feat in GD_GEOJSON["features"]: ext(feat["geometry"]["coordinates"])
            lons=[c[0] for c in all_c]; lats=[c[1] for c in all_c]

            m = folium.Map(tiles="CartoDB positron",control_scale=False,prefer_canvas=True,zoom_control=False,
                           attr=" ", max_zoom=10)

            # 注入浅色背景CSS到地图内部（作用于iframe内）
            dark_css = """
            <style>
                body, .leaflet-container { background: transparent !important; }
                /* 平滑缩放过渡 */
                .leaflet-zoom-anim .leaflet-zoom-animated {
                    transition: transform 0.3s ease-out;
                }
                .leaflet-tile { transition: opacity 0.3s ease; }
                /* 隐藏右下角控件 */
                .leaflet-control-attribution { display: none !important; visibility: hidden !important; height: 0 !important; width: 0 !important; overflow: hidden !important; }
                .leaflet-control-zoom { display: none !important; }
                /* 高温脉冲动画 */
                @keyframes map-pulse {
                    0%, 100% { transform: scale(1); opacity: 1; }
                    50%      { transform: scale(1.15); opacity: 0.8; }
                }
                        /* 标签淡入 */
                .leaflet-marker-icon {
                    animation: label-fade-in 0.5s ease-out;
                }
                @keyframes label-fade-in {
                    from { opacity: 0; transform: scale(0.8); }
                    to { opacity: 1; transform: scale(1); }
                }
            </style>
            <script>
                // 强制移除所有控件
                function removeControls() {
                    // 移除zoom控件
                    var zoomControls = document.querySelectorAll('.leaflet-control-zoom');
                    zoomControls.forEach(function(el) { el.remove(); });
                    // 移除attribution控件
                    var attributions = document.querySelectorAll('.leaflet-control-attribution');
                    attributions.forEach(function(el) { el.remove(); });
                    // 移除所有control容器
                    var controlContainers = document.querySelectorAll('.leaflet-control-container');
                    controlContainers.forEach(function(el) { el.remove(); });
                }
                // 立即执行
                removeControls();
                // 延迟执行（确保DOM完全加载）
                setTimeout(removeControls, 100);
                setTimeout(removeControls, 500);
                setTimeout(removeControls, 1000);
                // 监听DOM变化
                var observer = new MutationObserver(removeControls);
                observer.observe(document.body, { childList: true, subtree: true });
            </script>
            """
            m.get_root().html.add_child(folium.Element(dark_css))
            # 自适应窗口：计算边界 + padding
            _bounds = [[min(lats),min(lons)],[max(lats),max(lons)]]
            m.fit_bounds(_bounds, padding=(30, 20))

            # 移除zoom控件
            for key in list(m._children.keys()):
                if 'zoom' in str(type(m._children[key])).lower():
                    del m._children[key]

            folium.GeoJson(gd_temp,
                style_function=lambda f:{"fillColor":cmap(f["properties"].get("温度",0)),"color":"#e5e5e7","weight":1.5,"fillOpacity":0.5},
                tooltip=GeoJsonTooltip(fields=["name","温度"],aliases=["城市:","温度:"],
                    style="background:rgba(255,255,255,.9);color:#1a1a1a;padding:3px;border-radius:4px;font-size:11px;border:1px solid #e5e5e7;"),
                highlight_function=lambda x:{"weight":3,"fillOpacity":0.85}).add_to(m)

            for feat in GD_GEOJSON["features"]:
                ac=feat["properties"]["adcode"]; temp=temp_map.get(ac)
                if temp is None: continue
                ctr=feat["properties"].get("centroid") or feat["properties"].get("center",[0,0])
                nm=feat["properties"]["name"].replace("市","")

                # 高温脉冲动画（>32℃）
                if temp >= 35:
                    _pulse = 'animation:map-pulse 1.5s ease-in-out infinite;'
                    _temp_color = '#ff4444'
                    _glow = 'text-shadow:0 0 8px rgba(255,68,68,0.8),1px 1px 3px black,-1px -1px 3px black;'
                elif temp >= 32:
                    _pulse = 'animation:map-pulse 2s ease-in-out infinite;'
                    _temp_color = '#ff9f43'
                    _glow = 'text-shadow:0 0 6px rgba(255,159,67,0.6),1px 1px 3px black,-1px -1px 3px black;'
                else:
                    _pulse = ''
                    _temp_color = '#ffffff'
                    _glow = ''

                folium.Marker(location=[ctr[1],ctr[0]],icon=folium.DivIcon(
                    html=f'<div style="font-size:10px;font-weight:bold;color:#fff;text-align:center;text-shadow:1px 1px 3px black,-1px -1px 3px black,1px -1px 3px black,-1px 1px 3px black;{_glow}{_pulse}">{nm}<br><span style="font-size:12px;color:{_temp_color}">{temp:.0f}℃</span></div>',
                    icon_size=(55,28),icon_anchor=(27,14))).add_to(m)

            # 计算地图高度：窗口高度 - 标题栏 - KPI卡片 - 模块标题 - 图例统计
            _map_height = 318
            st_folium(m,width="100%",height=_map_height,returned_objects=[])
            # 色阶图例 + 修复公网白色背景JS
            _legend_html = '''<div style="display:flex;align-items:center;gap:4px;margin-top:2px;font-size:0.5rem;color:#000000">
                <span>18℃</span>
                <div style="flex:1;height:8px;border-radius:4px;background:linear-gradient(90deg,#2196F3,#00BCD4,#FFC107,#FF9800,#F44336,#B71C1C,#9C27B0)"></div>
                <span>40℃</span>
            </div>
            <script>
            (function() {
                function fixFoliumBg() {
                    var iframes = document.querySelectorAll('iframe[src*="streamlit_folium"]');
                    iframes.forEach(function(iframe) {
                        var el = iframe;
                        for (var i = 0; i < 10; i++) {
                            el = el.parentElement;
                            if (!el) break;
                            el.style.background = 'transparent';
                            el.style.backgroundColor = 'transparent';
                            var siblings = el.parentElement ? el.parentElement.children : [];
                            for (var j = 0; j < siblings.length; j++) {
                                if (siblings[j] !== el && siblings[j].tagName === 'DIV') {
                                    var cs = window.getComputedStyle(siblings[j]);
                                    if (cs.width === '0px' || cs.height === '0px' ||
                                        siblings[j].children.length === 0) {
                                        siblings[j].style.display = 'none';
                                    }
                                }
                            }
                        }
                    });
                }
                fixFoliumBg();
                setTimeout(fixFoliumBg, 500);
                setTimeout(fixFoliumBg, 1500);
            })();
            </script>'''
            st.markdown(_legend_html, unsafe_allow_html=True)
            avg_t=city_temps["温度"].mean(); mx=city_temps.loc[city_temps["温度"].idxmax()]; mn=city_temps.loc[city_temps["温度"].idxmin()]
            st.markdown(f'<span style="font-size:0.6rem;color:#666">均温**{avg_t:.1f}℃** | 最高{mx["城市"]}**{mx["温度"]:.1f}℃** | 最低{mn["城市"]}**{mn["温度"]:.1f}℃**</span>', unsafe_allow_html=True)


    # ----- 检修计划（来自披露文件，日期与电价模块联动）-----
    with st.container(border=True):
        st.markdown('<div class="mod-head mod-head-m">🔧 检修计划<span class="mod-sub">信息披露 · 机组+输变电</span></div>', unsafe_allow_html=True)
        _price_date = st.session_state.get("price_date_val", datetime.now().strftime("%Y-%m-%d"))
        _maint_data = parse_maintenance_from_disclosure(_price_date)

        # 如果当前日期无数据，回退到最近可用日期
        if not _maint_data["检修容量"] and _maint_data["机组检修"].empty and _maint_data["输变电检修"].empty:
            _disclosure_dir_fallback = os.path.join(os.path.dirname(os.path.abspath(__file__)), "disclosure")
            if os.path.exists(_disclosure_dir_fallback):
                _avail_files = sorted([f.replace("信息披露查询预测信息(","").replace(").xlsx","") 
                                       for f in os.listdir(_disclosure_dir_fallback) 
                                       if f.startswith("信息披露查询预测信息(") and f.endswith(").xlsx")])
                if _avail_files:
                    _price_date = _avail_files[-1]
                    _maint_data = parse_maintenance_from_disclosure(_price_date)

        # 数据来源日期（橙色）+ 检修容量（紧凑两行）
        st.markdown(f'<div style="font-size:0.6rem;color:#ff9f43;font-weight:bold;margin-bottom:2px">📅 数据日期：{_price_date}</div>', unsafe_allow_html=True)
        if _maint_data["检修容量"]:
            _cap = _maint_data["检修容量"]
            st.markdown(
                f'<div style="display:flex;gap:8px;margin:2px 0 3px 0;">'
                f'<span style="font-size:0.6rem;color:#666">总检修容量 <b style="color:#1a1a1a">{_cap["总容量"]:.0f}</b> MW</span>'
                f'<span style="font-size:0.6rem;color:#666">市场机组 <b style="color:#1a1a1a">{_cap["市场机组容量"]:.0f}</b> MW</span>'
                f'</div>', unsafe_allow_html=True)

        _mach = _maint_data.get("机组检修", pd.DataFrame())
        _line = _maint_data.get("输变电检修", pd.DataFrame())

        # 表格深色主题样式（HTML表格，循环滚动展示）
        def _df_to_dark_html(df, max_height=120, scroll=True, col_widths=None):
            """DataFrame → 深色主题 HTML 表格（表头固定，内容循环滚动）"""
            th_style = 'background:linear-gradient(180deg,#f0f2f5,#e8eaef);color:#1a1a1a;font-size:0.45rem;padding:3px 6px;border:1px solid #d0d0d0;font-weight:600;line-height:1.5;position:sticky;top:0;z-index:1;'
            td_style = 'background:#ffffff;color:#1a1a1a;font-size:0.45rem;padding:2px 6px;border:1px solid #e5e5e7;transition:background 0.2s;'

            row_count = len(df)
            anim_duration = max(row_count * 3, 10)

            # 计算列宽比例
            col_count = len(df.columns)
            if col_widths:
                widths = col_widths
            else:
                widths = [f'{100/col_count:.1f}%'] * col_count

            # 单表格：表头sticky + 表体滚动
            body_height = max_height - 20
            html = f'<div style="max-height:{body_height}px;overflow-y:auto;overflow-x:hidden;border-radius:8px;border:1px solid #d0d0d0;">'

            if scroll and row_count > 3:
                html += f'<div style="animation:table-scroll {anim_duration}s linear infinite;">'

            html += '<table style="width:100%;border-collapse:collapse;table-layout:fixed;"><thead><tr>'
            for i, col in enumerate(df.columns):
                w = widths[i] if i < len(widths) else widths[-1]
                html += f'<th style="{th_style}width:{w};">{col}</th>'
            html += '</tr></thead><tbody>'

            for _, row in df.iterrows():
                _row_bg = '' if _ % 2 == 0 else 'background:#f8f9fa;'
                html += f'<tr style="{_row_bg}">'
                for i, val in enumerate(row):
                    w = widths[i] if i < len(widths) else widths[-1]
                    html += f'<td style="{td_style}width:{w};{_row_bg}">{val}</td>'
                html += '</tr>'

            html += '</tbody></table>'

            if scroll and row_count > 3:
                html += '</div>'

            html += '</div>'
            return html

        if not _mach.empty:
            _mach_html = f'<span style="font-size:0.6rem;font-weight:bold;color:#ff9f43;display:block;margin-bottom:2px;">🔩 机组检修（{len(_mach)}台）</span>'
            _mach_html += _df_to_dark_html(_mach, 175, col_widths=["30%", "15%", "15%", "20%", "20%"])
            st.markdown(_mach_html, unsafe_allow_html=True)

        if not _line.empty:
            _line_html = f'<span style="font-size:0.6rem;font-weight:bold;color:#ff9f43;display:block;margin-bottom:2px;">⚡ 输变电检修（{len(_line)}条）</span>'
            _line_html += _df_to_dark_html(_line, 180)
            st.markdown(_line_html, unsafe_allow_html=True)
            st.markdown('<div style="height:1px"></div>', unsafe_allow_html=True)

        if _mach.empty and _line.empty and not _maint_data["检修容量"]:
            st.info(f"{_price_date} 无检修数据，请先上传披露文件")


# ============================================================


# ===== 第三列：电价数据 =====
with col3:
    # ----- 电价分析 -----
    with st.container(border=True):
        st.markdown('<div class="mod-head mod-head-p">📊 电价数据<span class="mod-sub">实际+预测 · 统调负荷</span></div>', unsafe_allow_html=True)

        # 信息披露文件上传
        _disclosure_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "disclosure")
        if not os.path.exists(_disclosure_dir):
            _disclosure_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "disclosure")
        os.makedirs(_disclosure_dir, exist_ok=True)

        # 同步逻辑变量初始化
        _sync_clicked = False

        # 加载实际电价和预测电价
        _actual_path = _ACTUAL_PRICE_PATH
        _forecast_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "广东日前电价预测.xlsx")
        _actual_df = pd.read_excel(_actual_path) if os.path.exists(_actual_path) else pd.DataFrame()
        _forecast_df = pd.read_excel(_forecast_path) if os.path.exists(_forecast_path) else pd.DataFrame()

        _hour_cols = [f"{i}时" for i in range(24)]
        if not _actual_df.empty:
            _actual_df["_日期"] = pd.to_datetime(_actual_df["日期"]).dt.strftime("%Y-%m-%d")
        if not _forecast_df.empty:
            _forecast_df["_日期"] = pd.to_datetime(_forecast_df["日期"]).dt.strftime("%Y-%m-%d")

        # 合并可用日期 + 模型预测日期
        _actual_dates = set()
        _all_dates = []
        if not _actual_df.empty:
            _actual_dates = set(_actual_df["_日期"].unique().tolist())
            _all_dates += list(_actual_dates)
        if not _forecast_df.empty:
            _all_dates += _forecast_df["_日期"].unique().tolist()
        # 添加今天和明天（模型可预测）
        _today = _now().strftime("%Y-%m-%d")
        _tomorrow = (_now() + timedelta(days=1)).strftime("%Y-%m-%d")
        for _d in [_today, _tomorrow]:
            if _d not in _all_dates:
                _all_dates.append(_d)
        _all_dates = sorted(set(_all_dates), reverse=True)

        # 日期中文标签映射
        def _fmt_cn(d_str):
            _dt = pd.to_datetime(d_str)
            _wd = CN_WEEKDAYS.get(_dt.weekday(), "")
            return f"{_dt.month}月{_dt.day}日 {_wd}"

        _date_labels = {d: _fmt_cn(d) for d in _all_dates}
        # 默认选中最近有实际数据的日期（而非今天）
        _default_idx = 0
        for _i, _d in enumerate(_all_dates):
            if _d in _actual_dates:
                _default_idx = _i
                break

        if _all_dates:
            # 回调：selectbox 变化时立即更新 session_state
            def _on_date_change():
                _label = st.session_state["price_date_sel"]
                _date_str = [d for d, lb in _date_labels.items() if lb == _label][0]
                st.session_state["price_date_val"] = _date_str

            # 日期选择器
            st.markdown('<div style="font-size:0.7rem;color:#86868B;margin-bottom:2px;">选择日期</div>', unsafe_allow_html=True)
            sel_label = st.selectbox("选择日期", [_date_labels[d] for d in _all_dates],
                                      index=_default_idx, key="price_date_sel",
                                      on_change=_on_date_change, label_visibility="collapsed")

            # 反查日期字符串
            sel_date = [d for d, lb in _date_labels.items() if lb == sel_label][0]
            st.session_state["price_date_val"] = sel_date

            fig = go.Figure()
            has_data = False

            # 实际电价
            if not _actual_df.empty:
                _act = _actual_df[_actual_df["_日期"] == sel_date]
                if not _act.empty:
                    _row = _act.iloc[0]
                    _vals = [_row[h] for h in _hour_cols]
                    fig.add_trace(go.Scattergl(
                        x=list(range(24)), y=_vals, name="实际电价",
                        line=dict(color="#007bff", width=2),
                        mode="lines+markers", marker=dict(size=5, color="#ffffff", line=dict(color="#007bff", width=1.5)),
                        fill="tozeroy", fillcolor="rgba(0,123,255,0.1)"))
                    has_data = True
                    # 峰谷标注
                    _pk_idx = _vals.index(max(_vals))
                    _vl_idx = _vals.index(min(_vals))
                    _chart_annotation(fig, _pk_idx, max(_vals), f'{max(_vals):.0f}', '#dc3545', 'top center')
                    _chart_annotation(fig, _vl_idx, min(_vals), f'{min(_vals):.0f}', '#0D7A3F', 'bottom center')

            # Excel预测电价（校准后）
            if not _forecast_df.empty:
                _fc = _forecast_df[(_forecast_df["_日期"] == sel_date) & (_forecast_df["模型"] == "校准后")]
                if not _fc.empty:
                    _row = _fc.iloc[0]
                    _vals = [_row[h] for h in _hour_cols]
                    fig.add_trace(go.Scattergl(
                        x=list(range(24)), y=_vals, name="预测(校准后)",
                        line=dict(color="#ff6b6b", width=2, dash="dot"),
                        mode="lines+markers", marker=dict(size=3)))
                    has_data = True

                _fc2 = _forecast_df[(_forecast_df["_日期"] == sel_date) & (_forecast_df["模型"] == "校准前")]
                if not _fc2.empty:
                    _row = _fc2.iloc[0]
                    _vals = [_row[h] for h in _hour_cols]
                    fig.add_trace(go.Scattergl(
                        x=list(range(24)), y=_vals, name="预测(校准前)",
                        line=dict(color="#ffd93d", width=1.5, dash="dash"),
                        mode="lines+markers", marker=dict(size=2)))

            # 模型实时预测（当选择的日期无实际/Excel预测数据时）
            # 从 session_state 获取已保存的预测结果
            _fc_key = f"forecast_{sel_date}"
            _saved_fc = st.session_state.get(_fc_key)

            # 缓存预加载：session_state 没有时尝试从文件加载
            if _saved_fc is None:
                _pred_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "predictions")
                _pred_file = os.path.join(_pred_dir, f"forecast_{sel_date}.csv")
                if os.path.exists(_pred_file):
                    try:
                        _cached_df = pd.read_csv(_pred_file)
                        _saved_fc = {"result": _cached_df, "log": "（从本地缓存加载）"}
                        st.session_state[_fc_key] = _saved_fc
                    except Exception:
                        pass

            if not has_data and _saved_fc is not None:
                # 已有预测结果，直接显示
                _fc_result = _saved_fc["result"]
                _fc_log = _saved_fc.get("log", "")
                fig.add_trace(go.Scattergl(
                    x=_fc_result["小时"], y=_fc_result["预测电价(元/MWh)"],
                    name="日前电价预测", line=dict(color="#ff6b6b", width=2),
                    mode="lines+markers", marker=dict(size=4),
                    fill="tozeroy", fillcolor="rgba(255,107,107,0.1)"))
                has_data = True

            # 显示预测详情（无论新预测还是已保存）
            if _saved_fc is not None:
                _fc_result = _saved_fc["result"]
                _fc_log = _saved_fc.get("log", "")
                st.markdown("**📋 预测结果详情**")
                _pc1, _pc2, _pc3, _pc4 = st.columns(4)
                _avg = _fc_result["预测电价(元/MWh)"].mean()
                _peak = _fc_result["预测电价(元/MWh)"].max()
                _valley = _fc_result["预测电价(元/MWh)"].min()
                _peak_h = int(_fc_result.loc[_fc_result["预测电价(元/MWh)"].idxmax(), "小时"])
                _valley_h = int(_fc_result.loc[_fc_result["预测电价(元/MWh)"].idxmin(), "小时"])
                with _pc1: st.metric("均价", f"{_avg:.0f} 元/MWh")
                with _pc2: st.metric("峰值", f"{_peak:.0f}", f"{_peak_h}时")
                with _pc3: st.metric("谷值", f"{_valley:.0f}", f"{_valley_h}时")
                with _pc4: st.metric("峰谷差", f"{_peak - _valley:.0f}")

                with st.expander("📊 逐时预测明细", expanded=False):
                    _display_df = _fc_result.copy()
                    _display_df.columns = ["小时", "预测电价(元/MWh)", "日期"]
                    st.dataframe(_display_df, use_container_width=True, hide_index=True, height=120)

                with st.expander("🔍 预测过程日志", expanded=False):
                    st.code(_fc_log if _fc_log else "无详细日志", language="text")

            if has_data:
                # 峰谷区间着色
                _shapes = []
                # 谷时 0-6: 蓝色
                _shapes.append(dict(type="rect", xref="x", yref="paper", x0=-0.5, x1=6.5, y0=0, y1=1, fillcolor="rgba(84,160,255,0.06)", line_width=0))
                # 平时 7: 无色
                # 峰时 8-12, 14-17: 浅红
                _shapes.append(dict(type="rect", xref="x", yref="paper", x0=7.5, x1=12.5, y0=0, y1=1, fillcolor="rgba(255,107,107,0.06)", line_width=0))
                _shapes.append(dict(type="rect", xref="x", yref="paper", x0=13.5, x1=17.5, y0=0, y1=1, fillcolor="rgba(255,107,107,0.06)", line_width=0))
                # 尖峰 10-12, 15-17: 深红
                _shapes.append(dict(type="rect", xref="x", yref="paper", x0=9.5, x1=12.5, y0=0, y1=1, fillcolor="rgba(255,71,87,0.08)", line_width=0))
                _shapes.append(dict(type="rect", xref="x", yref="paper", x0=14.5, x1=17.5, y0=0, y1=1, fillcolor="rgba(255,71,87,0.08)", line_width=0))
                # 晚间 18-23: 浅灰
                _shapes.append(dict(type="rect", xref="x", yref="paper", x0=17.5, x1=23.5, y0=0, y1=1, fillcolor="rgba(136,136,136,0.04)", line_width=0))

                fig.update_layout(transition=dict(duration=500, easing="cubic-in-out"), height=210, template="neumorphic",
                    showlegend=True,
                    title=dict(text=f"日前电价曲线 - {sel_date}", font=dict(size=10, color="#000000")),
                    hovermode="x unified",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=7, color="#000000")),
                    margin=dict(l=30, r=10, t=20, b=8), font=dict(size=8, color="#000000"),
                    shapes=_shapes,
                    xaxis=dict(dtick=3, tickvals=list(range(0,24,3)), ticktext=[f"{i}时" for i in range(0,24,3)]),
                    yaxis=dict(title="元/MWh", title_font=dict(size=7, color="#000000")))
                # Y轴自适应
                _all_y = []
                for _tr in fig.data:
                    if _tr.y is not None:
                        _all_y.extend([v for v in _tr.y if v is not None])
                if _all_y:
                    _y_min, _y_max = min(_all_y), max(_all_y)
                    _y_pad = max((_y_max - _y_min) * 0.1, 10)
                    fig.update_yaxes(range=[_y_min - _y_pad, _y_max + _y_pad])
                st.plotly_chart(fig, use_container_width=True)

                # 指标行
                if not _actual_df.empty:
                    _act = _actual_df[_actual_df["_日期"] == sel_date]
                    if not _act.empty:
                        _vals = [_act.iloc[0][h] for h in _hour_cols]
                        pk_h = _vals.index(max(_vals))
                        vl_h = _vals.index(min(_vals))
                        _avg_v = sum(_vals)/len(_vals)

                        # 前一天数据（用于对比）
                        _prev_day = _actual_df[_actual_df["_日期"] < sel_date].tail(1)
                        _pk_arrow = ""; _vl_arrow = ""; _pk_price_arrow = ""; _avg_arrow = ""
                        if not _prev_day.empty:
                            _prev_vals = [_prev_day.iloc[0][h] for h in _hour_cols]
                            _prev_pk_h = _prev_vals.index(max(_prev_vals))
                            _prev_vl_h = _prev_vals.index(min(_prev_vals))
                            _prev_avg = sum(_prev_vals)/len(_prev_vals)
                            # 峰时箭头：后移↑ 前移↓
                            if pk_h > _prev_pk_h:
                                _pk_arrow = '<span style="color:#ff4757;font-size:0.5rem;">↑</span>'
                            elif pk_h < _prev_pk_h:
                                _pk_arrow = '<span style="color:#2ecc71;font-size:0.5rem;">↓</span>'
                            # 谷时箭头：后移↑ 前移↓
                            if vl_h > _prev_vl_h:
                                _vl_arrow = '<span style="color:#ff4757;font-size:0.5rem;">↑</span>'
                            elif vl_h < _prev_vl_h:
                                _vl_arrow = '<span style="color:#2ecc71;font-size:0.5rem;">↓</span>'
                            # 峰值价格箭头
                            _pk_diff = max(_vals) - max(_prev_vals)
                            if _pk_diff > 5:
                                _pk_price_arrow = '<span style="color:#ff4757;font-size:0.5rem;">↑</span>'
                            elif _pk_diff < -5:
                                _pk_price_arrow = '<span style="color:#2ecc71;font-size:0.5rem;">↓</span>'
                            # 均价箭头
                            _avg_arrow = ""
                            _avg_diff = _avg_v - _prev_avg
                            if _avg_diff > 5:
                                _avg_arrow = '<span style="color:#ff4757;font-size:0.5rem;">↑</span>'
                            elif _avg_diff < -5:
                                _avg_arrow = '<span style="color:#2ecc71;font-size:0.5rem;">↓</span>'

                        _metrics_html = f'''<div style="display:flex;gap:16px;font-size:0.6rem;margin-top:2px;">
                            <span>均价 <b style="color:#0D7A3F;font-size:0.75rem;">{_avg_v:.0f}</b> {_avg_arrow}</span>
                            <span>峰 <b style="color:#dc3545;font-size:0.75rem;">{max(_vals):.0f}</b>{_pk_price_arrow} {pk_h}时{_pk_arrow}</span>
                            <span>谷 <b style="color:#007bff;font-size:0.75rem;">{min(_vals):.0f}</b> {vl_h}时{_vl_arrow}</span>
                        </div>'''
                        st.markdown(_metrics_html, unsafe_allow_html=True)

                # ===== 实时电价曲线图表 =====
                # 实时电价单独日期选择器
                _rt_date_options = [d for d in _all_dates]
                _rt_sel_date = st.selectbox("实时电价日期", _rt_date_options, index=0, key="rt_price_date_sel", label_visibility="collapsed")
                
                _rt_fig = go.Figure()
                _rt_has_data = False
                _rt_hour_cols = [f"{i}时" for i in range(24)]
                _rt_hourly = None
                _rt_fc_vals = None

                # 实际实时电价（从披露数据读取96点，转换为24点）
                _rt_actual_dir = os.path.expanduser("~/projects/能源电力资料/实时训练数据/日前和实时电价占比/2026")
                _rt_actual_month = _rt_sel_date[:7]  # 格式: 2026-06
                _rt_actual_path = os.path.join(_rt_actual_dir, str(int(_rt_actual_month.split("-")[1])))
                if os.path.exists(_rt_actual_path):
                    _rt_file = os.path.join(_rt_actual_path, f"实时节点电价查询({_rt_sel_date}).xlsx")
                    if os.path.exists(_rt_file):
                        try:
                            _rt_df = pd.read_excel(_rt_file)
                            _rt_time_cols = [c for c in _rt_df.columns if ':' in str(c)]
                            if len(_rt_time_cols) >= 96:
                                # 对所有节点求平均
                                _rt_avg = _rt_df[_rt_time_cols].mean()
                                # 96点转24点（每4点取平均）
                                _rt_hourly = []
                                for h in range(24):
                                    _quarter_cols = [f'{h:02d}:{m:02d}' for m in [0, 15, 30, 45]]
                                    _vals = [_rt_avg[c] for c in _quarter_cols if c in _rt_avg.index]
                                    _rt_hourly.append(float(np.mean(_vals)) if _vals else np.nan)
                                _rt_fig.add_trace(go.Scattergl(
                                    x=list(range(24)), y=_rt_hourly,
                                    name=f"实际电价 {sel_date}",
                                    line=dict(color="#007bff", width=2),
                                    mode="lines+markers",
                                    marker=dict(size=4, color="#ffffff", line=dict(color="#007bff", width=1.5)),
                                    fill="tozeroy", fillcolor="rgba(0,123,255,0.08)"
                                ))
                                _rt_has_data = True
                        except Exception as e:
                            pass

                # 预测实时电价
                _rt_forecast_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "广东实时电价预测.xlsx")
                if os.path.exists(_rt_forecast_path):
                    try:
                        _rt_fc_df = pd.read_excel(_rt_forecast_path)
                        _rt_fc_df["_date"] = pd.to_datetime(_rt_fc_df["日期"]).dt.strftime("%Y-%m-%d")
                        _rt_fc_sel = _rt_fc_df[(_rt_fc_df["_date"] == _rt_sel_date) & (_rt_fc_df["模型"] == "校准后")]
                        if not _rt_fc_sel.empty:
                            _rt_fc_vals = [_rt_fc_sel.iloc[0][h] for h in _rt_hour_cols]
                            _rt_fig.add_trace(go.Scattergl(
                                x=list(range(24)), y=_rt_fc_vals,
                                name=f"预测电价 {_rt_sel_date}",
                                line=dict(color="#ff6b6b", width=2, dash="dot"),
                                mode="lines+markers", marker=dict(size=3)
                            ))
                            _rt_has_data = True
                    except Exception as e:
                        pass

                # 始终显示图表（即使无数据）
                _rt_fig.update_layout(
                    height=200, template="neumorphic", showlegend=True,
                    title=dict(text=f"实时电价曲线 - {_rt_sel_date}", font=dict(size=10, color="#000000")),
                    hovermode="x unified",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=7, color="#000000")),
                    margin=dict(l=30, r=10, t=20, b=8), font=dict(size=8, color="#000000"),
                    xaxis=dict(dtick=3, tickvals=list(range(0, 24, 3)), ticktext=[f"{i}时" for i in range(0, 24, 3)]),
                    yaxis=dict(title="元/MWh", title_font=dict(size=7, color="#000000"))
                )
                # Y轴自适应
                _rt_all_y = []
                for _tr in _rt_fig.data:
                    if _tr.y is not None:
                        _rt_all_y.extend([v for v in _tr.y if v is not None])
                if _rt_all_y:
                    _rt_y_min, _rt_y_max = min(_rt_all_y), max(_rt_all_y)
                    _rt_pad = max((_rt_y_max - _rt_y_min) * 0.1, 10)
                    _rt_fig.update_yaxes(range=[_rt_y_min - _rt_pad, _rt_y_max + _rt_pad])
                st.plotly_chart(_rt_fig, use_container_width=True)
                # 实时电价KPI（始终显示）
                _rt_kpi_parts = []
                if _rt_hourly is not None:
                    _rt_actual_avg = np.nanmean(_rt_hourly)
                    _rt_kpi_parts.append(f'实际均价 <b>{_rt_actual_avg:.0f}</b> 元/MWh')
                else:
                    _rt_kpi_parts.append('实际均价 <b>--</b> 元/MWh')
                if _rt_fc_vals is not None:
                    _rt_fc_avg = np.nanmean(_rt_fc_vals)
                    _rt_kpi_parts.append(f'预测均价 <b>{_rt_fc_avg:.0f}</b> 元/MWh')
                else:
                    _rt_kpi_parts.append('预测均价 <b>--</b> 元/MWh')
                if _rt_hourly is not None and _rt_fc_vals is not None:
                    _rt_diff = _rt_actual_avg - _rt_fc_avg
                    _rt_diff_pct = _rt_diff / _rt_fc_avg * 100 if _rt_fc_avg != 0 else 0
                    _rt_arrow = "↑" if _rt_diff > 0 else "↓" if _rt_diff < 0 else "→"
                    _rt_color = "#dc3545" if _rt_diff > 0 else "#0D7A3F" if _rt_diff < 0 else "#666"
                    _rt_kpi_parts.append(f'偏差 <span style="color:{_rt_color};font-weight:bold">{_rt_arrow} {_rt_diff:+.0f} ({_rt_diff_pct:+.1f}%)</span>')
                else:
                    _rt_kpi_parts.append('偏差 <b>--</b>')
                st.markdown(f'<span style="font-size:0.6rem;color:#666">{" | ".join(_rt_kpi_parts)}</span>', unsafe_allow_html=True)

                # ===== 负荷曲线图表（省内B类电源）=====
                _load_fig = go.Figure()
                _load_has_data = False
                
                # 从披露数据读取省内B类电源
                _disclosure_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "disclosure")
                _load_fp = os.path.join(_disclosure_dir, f"信息披露查询预测信息({sel_date}).xlsx")
                
                if os.path.exists(_load_fp):
                    try:
                        _load_xl = pd.ExcelFile(_load_fp)
                        for s in _load_xl.sheet_names:
                            if "负荷预测" in s:
                                _load_df = pd.read_excel(_load_fp, sheet_name=s, header=None, skiprows=1)
                                for _, row in _load_df.iterrows():
                                    ch = str(row.iloc[1]) if len(row) > 1 else ""
                                    if "B类电源" in ch:
                                        _load_vals = []
                                        for col_idx in range(2, min(98, len(row))):
                                            try:
                                                _load_vals.append(float(row.iloc[col_idx]))
                                            except:
                                                pass
                                        if len(_load_vals) >= 96:
                                            _load_hourly = [np.mean(_load_vals[h*4:(h+1)*4]) for h in range(24)]
                                            _load_fig.add_trace(go.Scattergl(
                                                x=list(range(24)), y=_load_hourly,
                                                name=f"B类电源 {sel_date}",
                                                line=dict(color="#54a0ff", width=2),
                                                mode="lines+markers", marker=dict(size=4),
                                                fill="tozeroy", fillcolor="rgba(84,160,255,0.08)"
                                            ))
                                            _load_has_data = True
                                break
                    except Exception as e:
                        pass
                
                if _load_has_data:
                    _load_fig.update_layout(
                        height=200, template="neumorphic", showlegend=True,
                        title=dict(text=f"负荷曲线 - {sel_date}", font=dict(size=10, color="#000000")),
                        hovermode="x unified",
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=7, color="#000000")),
                        margin=dict(l=30, r=10, t=20, b=8), font=dict(size=8, color="#000000"),
                        xaxis=dict(dtick=3, tickvals=list(range(0, 24, 3)), ticktext=[f"{i}时" for i in range(0, 24, 3)]),
                        yaxis=dict(title="MW", title_font=dict(size=7, color="#000000"))
                    )
                    # Y轴自适应
                    _load_all_y = []
                    for _tr in _load_fig.data:
                        if _tr.y is not None:
                            _load_all_y.extend([v for v in _tr.y if v is not None])
                    if _load_all_y:
                        _load_y_min, _load_y_max = min(_load_all_y), max(_load_all_y)
                        _load_pad = max((_load_y_max - _load_y_min) * 0.1, 1000)
                        _load_fig.update_yaxes(range=[_load_y_min - _load_pad, _load_y_max + _load_pad])
                    st.plotly_chart(_load_fig, use_container_width=True)
                    
                    # 负荷KPI（始终显示）
                    _load_avg = np.nanmean(_load_hourly)
                    _load_max = max(_load_hourly)
                    _load_min = min(_load_hourly)
                    _load_peak_h = _load_hourly.index(_load_max)
                    _load_valley_h = _load_hourly.index(_load_min)
                    st.markdown(f'<span style="font-size:0.6rem;color:#666">日均 <b>{_load_avg:.0f}</b> MW | 峰值 <b>{_load_max:.0f}</b> MW {_load_peak_h}时 | 谷值 <b>{_load_min:.0f}</b> MW {_load_valley_h}时</span>', unsafe_allow_html=True)
                else:
                    st.markdown('<span style="font-size:0.6rem;color:#666">日均 <b>--</b> MW | 峰值 <b>--</b> MW | 谷值 <b>--</b> MW</span>', unsafe_allow_html=True)

            else:
                st.info(f"{sel_date} 无电价数据，请进行日前电价预测")
        else:
            st.warning("无电价数据文件")


# 页脚
# ============================================================
st.markdown("""
<div style="margin-top:4px;padding:16px 0 8px;border-top:1px solid #e5e5e7;text-align:center;">
    <div style="display:flex;justify-content:center;align-items:center;gap:24px;flex-wrap:wrap;">
        <span style="font-size:0.6rem;color:#888;">📊 数据来源: Open-Meteo · CCTD · SHPGX · 广东电力交易中心</span>
        <span style="font-size:0.6rem;color:#888;">🔄 更新周期: 气象10分钟 · 燃料1小时 · 电价实时</span>
    </div>
    <div style="margin-top:8px;font-size:0.55rem;color:#aaa;">
        © 2024-2026 电力市场多源数据监控大屏 v2.0 | Powered by Streamlit
    </div>
</div>
""", unsafe_allow_html=True)
