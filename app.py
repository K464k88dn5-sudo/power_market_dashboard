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
from data_sources.fuel_api import build_fuel_display_data, get_fuel_latest_summary

# ============================================================
# 页面配置 & 自动刷新
# ============================================================
st.set_page_config(page_title="电力市场监控大屏", page_icon="⚡", layout="wide",
                   initial_sidebar_state="collapsed")

from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=5 * 60 * 1000, key="auto_refresh")

# 刷新倒计时进度条
st.markdown('<div class="refresh-bar-wrap"><div class="refresh-bar"></div></div>', unsafe_allow_html=True)

# 刷新脉冲光晕（页面加载时播放一次）
st.markdown('<div class="refresh-pulse-overlay"></div>', unsafe_allow_html=True)

# JavaScript：强制删除顶部空白
st.markdown("""
<script>
const removeTopGap = () => {
    // 删除 Streamlit 顶部工具栏/装饰元素
    const selectors = [
        '[data-testid="stHeader"]',
        '[data-testid="stToolbar"]', 
        '[data-testid="stDecoration"]',
        '[data-testid="stSidebarCollapsedControl"]'
    ];
    selectors.forEach(s => {
        document.querySelectorAll(s).forEach(el => {
            el.style.display = 'none';
            el.style.height = '0';
            el.style.minHeight = '0';
            el.style.padding = '0';
            el.style.margin = '0';
        });
    });
    // 压缩 block-container 上方所有兄弟元素
    const bc = document.querySelector('.block-container');
    if (bc) {
        bc.style.paddingTop = '0';
        bc.style.marginTop = '0';
        let prev = bc.previousElementSibling;
        while (prev) {
            prev.style.height = '0';
            prev.style.minHeight = '0';
            prev.style.padding = '0';
            prev.style.margin = '0';
            prev.style.overflow = 'hidden';
            prev = prev.previousElementSibling;
        }
    }
};
// 页面加载后执行
setTimeout(removeTopGap, 500);
setTimeout(removeTopGap, 2000);
</script>
""", unsafe_allow_html=True)

# ============================================================
# 全局样式 — 极致紧凑，无滚动
# ============================================================
st.markdown("""
<style>
    /* ===== 驾驶舱深空科技风 ===== */

    /* 全局背景：深蓝黑渐变 + 微网格纹理 */
    .stApp {
        background: linear-gradient(180deg, #0a0e1a 0%, #0d1117 50%, #0a0e1a 100%) !important;
    }
    .block-container {
        padding: 0rem 0.5rem 0.25rem 0.5rem !important;
        max-width: 100% !important;
        background-image:
            linear-gradient(rgba(0,210,211,0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0,210,211,0.03) 1px, transparent 1px);
        background-size: 40px 40px;
    }
    /* 整体上移 */
    .stApp {
        transform: translateY(-4rem);
    }
    /* 压缩顶部空白（Streamlit 1.50 适配） */
    .stApp > header { height: 0 !important; min-height: 0 !important; display: none !important; }
    section[data-testid="stMain"] { padding-top: 0 !important; margin-top: 0 !important; }
    section[data-testid="stMain"] > div { padding-top: 0 !important; margin-top: 0 !important; }
    .block-container > div:first-child { margin-top: 0 !important; padding-top: 0 !important; }
    [data-testid="stHeader"] { display: none !important; height: 0 !important; }
    .stApp > div:first-child { margin-top: 0 !important; padding-top: 0 !important; }
    [data-testid="stToolbar"] { display: none !important; }
    [data-testid="stDecoration"] { display: none !important; }
    /* 通杀：所有顶层 div 的 margin/padding */
    .stApp, .stApp > div, .stApp > div > div {
        margin-top: 0 !important;
        padding-top: 0 !important;
    }
    /* 隐藏 sidebar 按钮 */
    [data-testid="stSidebarCollapsedControl"] { display: none !important; }
    /* 强制隐藏 sidebar */
    [data-testid="stSidebar"] { display: none !important; }
    section[data-testid="stSidebar"] { display: none !important; }
    /* 隐藏所有 Streamlit 顶部装饰 */
    header, [role="banner"] { display: none !important; height: 0 !important; }
    /* 压缩 main 区域 */
    .main { padding-top: 0 !important; margin-top: 0 !important; }
    .main .block-container { padding-top: 0 !important; margin-top: 0 !important; }

    /* 标题栏：渐变光带 */
    .dash-header {
        background: linear-gradient(90deg,
            rgba(0,210,211,0.08) 0%,
            rgba(0,210,211,0.2) 50%,
            rgba(0,210,211,0.08) 100%);
        border: 1px solid rgba(0,210,211,0.3);
        border-radius: 6px;
        padding: 0.25rem 0.8rem;
        margin-bottom: 0.2rem;
        display: flex; align-items: center; justify-content: center;
        box-shadow: 0 0 20px rgba(0,210,211,0.1);
        position: relative;
    }
    .dash-title {
        font-size: 1.3rem; font-weight: bold;
        background: linear-gradient(90deg, #00d2d3, #54a0ff, #a29bfe, #ff6b6b, #ffd93d, #00d2d3);
        background-size: 200% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        animation: title-shimmer 3s linear infinite;
    }
    @keyframes title-shimmer { 0%{background-position:0% center} 100%{background-position:200% center} }
    .dash-time  { font-size: 0.8rem; color: #8cc; position: absolute; right: 0.8rem; }
    .status-ok { color: #2ecc71; text-shadow: 0 0 5px rgba(46,204,113,0.5); }
    .status-fail { color: #e74c3c; text-shadow: 0 0 5px rgba(231,76,60,0.5); }

    /* KPI 行：玻璃拟态 */
    .kpi-bar { display: flex; gap: 0.25rem; margin-bottom: 0.2rem; }
    .kpi-card {
        flex: 1;
        background: rgba(13, 17, 23, 0.85);
        backdrop-filter: blur(8px);
        border: 1px solid rgba(0, 210, 211, 0.15);
        border-radius: 6px;
        padding: 0.2rem 0.4rem;
        text-align: center;
        box-shadow: 0 0 10px rgba(0,210,211,0.05), inset 0 0 10px rgba(0,210,211,0.02);
        transition: border-color 0.3s, box-shadow 0.3s;
    }
    .kpi-card:hover {
        border-color: rgba(0,210,211,0.5);
        box-shadow: 0 0 15px rgba(0,210,211,0.3), 0 0 30px rgba(0,210,211,0.1), inset 0 0 15px rgba(0,210,211,0.05);
        transform: translateY(-2px);
        transition: all 0.3s ease;
    }
    .kpi-label { font-size: 0.55rem; color: #7aa; }
    .kpi-value { font-size: 0.9rem; font-weight: bold; }
    .kpi-delta { font-size: 0.55rem; }

    /* 模块卡片：玻璃拟态 */
    .mod-card {
        background: rgba(13, 17, 23, 0.85);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(0, 210, 211, 0.12);
        border-radius: 6px;
        padding: 0.3rem;
        margin-bottom: 0.2rem;
        box-shadow: 0 0 15px rgba(0,210,211,0.04);
        transition: border-color 0.3s, box-shadow 0.3s;
    }
    .mod-card:hover {
        border-color: rgba(0,210,211,0.3);
        box-shadow: 0 0 20px rgba(0,210,211,0.1);
    }

    /* 模块标题 */
    .mod-head {
        font-size: 0.7rem; font-weight: bold;
        padding-bottom: 0.15rem; margin-bottom: 0.2rem;
        border-bottom: 2px solid;
        text-shadow: 0 0 8px currentColor;
    }
    .mod-head-w { color: #ffd93d; border-color: rgba(255,217,61,0.5); }
    .mod-head-f { color: #ff9f43; border-color: rgba(255,159,67,0.5); }
    .mod-head-p { color: #00d2d3; border-color: rgba(0,210,211,0.5); }
    .mod-head-m { color: #ff6b6b; border-color: rgba(255,107,107,0.5); }
    .mod-head-g { color: #2ecc71; border-color: rgba(46,204,113,0.5); }

    /* 紧凑图表 */
    .stPlotlyChart { margin: 0 !important; padding: 0 !important; background: transparent !important;
        animation: chart-fade-in 0.8s ease-out;
    }
    .stPlotlyChart > div { background: transparent !important; }
    .stPlotlyChart .plotly .main-svg { background: transparent !important; }
    [data-testid="stChart"] { background: transparent !important; }

    /* 图表渐现动画 */
    @keyframes chart-fade-in {
        0%   { opacity: 0; transform: translateX(-10px); }
        100% { opacity: 1; transform: translateX(0); }
    }

    /* folium 地图渐现 */
    .stFolium { animation: chart-fade-in 1s ease-out; }
    [data-testid="stMetricValue"] { font-size: 0.8rem !important; color: #e0e0e0 !important; }
    [data-testid="stMetricLabel"] { font-size: 0.55rem !important; color: #7aa !important; }
    [data-testid="stMetricDelta"] { font-size: 0.55rem !important; }
    [data-testid="stMetric"] { padding: 0.05rem 0 !important; }
    .stProgress > div > div { height: 0.35rem !important; }

    /* folium 地图容器深色背景 */
    .stFolium > iframe,
    .stFolium > div,
    .stFolium {
        background: #0a0e1a !important;
    }
    /* 地图 attribution 栏深色 */
    .leaflet-control-attribution { background: rgba(10,14,26,0.85) !important; color: #555 !important; }
    .leaflet-control-attribution a { color: #666 !important; }
    .leaflet-control-zoom a { background: #1a1e2a !important; color: #aaa !important; border-color: #333 !important; }

    /* Streamlit dataframe 表格深色主题 */
    [data-testid="stDataFrame"] th,
    [data-testid="stDataFrame"] td,
    [data-testid="stDataFrame"] .col_heading,
    [data-testid="stDataFrame"] .data,
    [data-testid="stDataFrame"] table {
        background-color: #0d1117 !important;
        color: #e0e0e0 !important;
        font-size: 0.45rem !important;
        border-color: rgba(255,255,255,0.06) !important;
    }
    [data-testid="stDataFrame"] th,
    [data-testid="stDataFrame"] .col_heading {
        background-color: rgba(0,210,211,0.08) !important;
        color: #00d2d3 !important;
        font-size: 0.45rem !important;
        border-color: rgba(0,210,211,0.15) !important;
    }

    /* 隐藏 Streamlit 默认元素（保留侧边栏切换按钮） */
    #MainMenu, footer { visibility: hidden; }
    /* 隐藏加载进度条和刷新动画 */
    .stSpinner, [data-testid="stStatusWidget"] { display: none !important; }
    header[data-testid="stHeader"] { display: none !important; }
    /* 隐藏滚动条相关 */
    .st-emotion-cache-1wrcr25 { padding-top: 0 !important; }

    /* KPI sparkline 迷你趋势线 */
    .kpi-sparkline { margin-top: 1px; line-height: 0; }
    .kpi-sparkline svg { display: block; }

    /* 异常值脉冲动画 */
    @keyframes kpi-pulse {
        0%, 100% { box-shadow: 0 0 10px rgba(255,71,87,0.2); border-color: rgba(255,71,87,0.3); }
        50%      { box-shadow: 0 0 20px rgba(255,71,87,0.5); border-color: rgba(255,71,87,0.7); }
    }
    .kpi-pulse { animation: kpi-pulse 2s ease-in-out infinite; }

    /* KPI 箭头指示 */
    .kpi-arrow-up { color: #ff4757; font-size: 0.5rem; }
    .kpi-arrow-dn { color: #2ecc71; font-size: 0.5rem; }
    .kpi-arrow-flat { color: #888; font-size: 0.5rem; }

    /* ===== 标题栏扫描线动画 ===== */
    .dash-header { position: relative; overflow: hidden; }
    .dash-header::after {
        content: '';
        position: absolute; top: 0; left: -100%;
        width: 50%; height: 100%;
        background: linear-gradient(90deg, transparent, rgba(0,210,211,0.15), transparent);
        animation: scan-line 4s ease-in-out infinite;
    }
    @keyframes scan-line {
        0%   { left: -50%; }
        100% { left: 150%; }
    }

    /* ===== 模块卡片呼吸灯 ===== */
    @keyframes card-breathe {
        0%, 100% { box-shadow: 0 0 15px rgba(0,210,211,0.04); }
        50%      { box-shadow: 0 0 25px rgba(0,210,211,0.12); }
    }
    .mod-card { animation: card-breathe 3s ease-in-out infinite; }

    /* ===== 地图高温城市脉冲 ===== */
    @keyframes map-pulse {
        0%, 100% { transform: scale(1); opacity: 1; }
        50%      { transform: scale(1.15); opacity: 0.8; }
    }

    /* ===== 表格循环滚动 ===== */
    @keyframes table-scroll {
        0%   { transform: translateY(0); }
        100% { transform: translateY(-50%); }
    }
    .table-scroll-wrap:hover .table-scroll-inner {
        animation-play-state: paused !important;
    }

    /* ===== 背景微粒子增强（20+光点 + 星芒）===== */
    .stApp::before {
        content: '';
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background-image:
            /* 20个光点 */
            radial-gradient(1.5px 1.5px at 5% 15%, rgba(0,210,211,0.4) 0%, transparent 100%),
            radial-gradient(1px 1px at 12% 45%, rgba(0,210,211,0.3) 0%, transparent 100%),
            radial-gradient(2px 2px at 18% 72%, rgba(0,210,211,0.25) 0%, transparent 100%),
            radial-gradient(1px 1px at 25% 28%, rgba(84,160,255,0.3) 0%, transparent 100%),
            radial-gradient(1.5px 1.5px at 32% 85%, rgba(0,210,211,0.35) 0%, transparent 100%),
            radial-gradient(1px 1px at 38% 12%, rgba(162,155,254,0.3) 0%, transparent 100%),
            radial-gradient(2px 2px at 45% 55%, rgba(0,210,211,0.2) 0%, transparent 100%),
            radial-gradient(1px 1px at 52% 38%, rgba(84,160,255,0.25) 0%, transparent 100%),
            radial-gradient(1.5px 1.5px at 58% 78%, rgba(0,210,211,0.3) 0%, transparent 100%),
            radial-gradient(1px 1px at 65% 22%, rgba(162,155,254,0.2) 0%, transparent 100%),
            radial-gradient(2px 2px at 72% 62%, rgba(0,210,211,0.35) 0%, transparent 100%),
            radial-gradient(1px 1px at 78% 8%, rgba(84,160,255,0.3) 0%, transparent 100%),
            radial-gradient(1.5px 1.5px at 85% 48%, rgba(0,210,211,0.25) 0%, transparent 100%),
            radial-gradient(1px 1px at 92% 82%, rgba(162,155,254,0.3) 0%, transparent 100%),
            radial-gradient(2px 2px at 8% 92%, rgba(0,210,211,0.2) 0%, transparent 100%),
            radial-gradient(1px 1px at 42% 2%, rgba(84,160,255,0.25) 0%, transparent 100%),
            radial-gradient(1.5px 1.5px at 62% 92%, rgba(0,210,211,0.3) 0%, transparent 100%),
            radial-gradient(1px 1px at 88% 28%, rgba(162,155,254,0.2) 0%, transparent 100%),
            radial-gradient(2px 2px at 22% 52%, rgba(0,210,211,0.35) 0%, transparent 100%),
            radial-gradient(1px 1px at 95% 68%, rgba(84,160,255,0.3) 0%, transparent 100%),
            /* 星芒效果 */
            radial-gradient(3px 1px at 15% 35%, rgba(255,255,255,0.15) 0%, transparent 100%),
            radial-gradient(1px 3px at 55% 65%, rgba(255,255,255,0.12) 0%, transparent 100%),
            radial-gradient(2px 1px at 75% 25%, rgba(255,255,255,0.1) 0%, transparent 100%),
            radial-gradient(1px 2px at 35% 85%, rgba(255,255,255,0.08) 0%, transparent 100%);
        animation: particle-drift 25s linear infinite;
        pointer-events: none; z-index: 0;
    }
    @keyframes particle-drift {
        0%   { transform: translateY(0) translateX(0); }
        25%  { transform: translateY(-15px) translateX(5px); }
        50%  { transform: translateY(-30px) translateX(-3px); }
        75%  { transform: translateY(-15px) translateX(8px); }
        100% { transform: translateY(0) translateX(0); }
    }

    /* ===== 数据刷新脉冲光晕 ===== */
    @keyframes refresh-pulse {
        0%   { opacity: 0; transform: scale(0.95); }
        50%  { opacity: 0.3; transform: scale(1); }
        100% { opacity: 0; transform: scale(1.05); }
    }
    .refresh-pulse-overlay {
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: radial-gradient(ellipse at center, rgba(0,210,211,0.15) 0%, transparent 70%);
        animation: refresh-pulse 1.5s ease-out;
        pointer-events: none; z-index: 9998;
    }

    /* ===== 刷新倒计时进度条 ===== */
    .refresh-bar-wrap {
        position: fixed; bottom: 0; left: 0; width: 100%; height: 3px;
        background: rgba(0,210,211,0.08); z-index: 999;
    }
    .refresh-bar {
        height: 100%; width: 0%;
        background: linear-gradient(90deg, #00d2d3, #54a0ff);
        animation: refresh-fill 300s linear infinite; /* 5min = 300s */
        box-shadow: 0 0 6px rgba(0,210,211,0.4);
    }
    @keyframes refresh-fill {
        0%   { width: 0%; }
        100% { width: 100%; }
    }

    /* ===== 单页自适应 ===== */

    /* 桌面：允许滚动 */
    @media (min-width: 1025px) {
        .block-container {
            padding: 0rem 0.5rem 0.25rem 0.5rem !important;
        }
    }

    /* 平板：两列布局 */
    @media (min-width: 641px) and (max-width: 1024px) {
        .block-container { padding: 0.2rem 0.3rem !important; }
        .kpi-bar { flex-wrap: wrap; gap: 0.15rem; }
        .kpi-card { min-width: 28%; padding: 0.15rem 0.3rem; }
        .kpi-value { font-size: 0.8rem !important; }
        .kpi-label { font-size: 0.5rem; }
        .dash-title { font-size: 0.9rem; }
        .mod-card { padding: 0.2rem; margin-bottom: 0.15rem; }
        .mod-head { font-size: 0.65rem; }
        [data-testid="stMetricValue"] { font-size: 0.75rem !important; }
        [data-testid="stMetricLabel"] { font-size: 0.5rem !important; }
    }

    /* 手机：单列堆叠 */
    @media (max-width: 640px) {
        .block-container { padding: 0.15rem 0.2rem !important; }
        .kpi-bar { flex-direction: column; gap: 0.1rem; }
        .kpi-card { width: 100%; padding: 0.12rem 0.3rem; }
        .kpi-value { font-size: 0.75rem !important; }
        .kpi-label { font-size: 0.45rem; }
        .kpi-sparkline { display: none; }
        .dash-header { flex-direction: column; gap: 2px; }
        .dash-title { font-size: 0.8rem; }
        .dash-time  { font-size: 0.5rem; }
        .mod-card { padding: 0.15rem; margin-bottom: 0.1rem; }
        .mod-head { font-size: 0.6rem; }
        [data-testid="stMetricValue"] { font-size: 0.7rem !important; }
        [data-testid="stMetricLabel"] { font-size: 0.45rem !important; }
        /* 手机隐藏粒子效果，节省性能 */
        .stApp::before { display: none; }
    }

    @media (max-width: 768px) {
        .block-container { padding: 0.15rem 0.2rem !important; }
        .kpi-card { min-width: 45%; padding: 0.1rem 0.2rem; }
        .kpi-value { font-size: 0.7rem !important; }
        .kpi-label { font-size: 0.45rem; }
        .dash-header { padding: 0.1rem 0.4rem; }
        .dash-title { font-size: 0.75rem; }
        .dash-time { font-size: 0.5rem; }
        .mod-card { padding: 0.15rem; }
        .mod-head { font-size: 0.6rem; }
        [data-testid="stMetricValue"] { font-size: 0.65rem !important; }
        [data-testid="stMetricLabel"] { font-size: 0.45rem !important; }
        [data-testid="stMetric"] { padding: 0.02rem 0 !important; }
    }

    @media (max-width: 480px) {
        .kpi-card { min-width: 100%; }
        .kpi-value { font-size: 0.65rem !important; }
        .dash-title { font-size: 0.65rem; }
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# Plotly 深空科技风自定义模板
# ============================================================
import plotly.io as pio

DEEP_SPACE_TEMPLATE = go.layout.Template(
    layout=go.Layout(
        paper_bgcolor="#0a0e1a",             # 深空底色
        plot_bgcolor="#0d1117",              # 绘图区微亮
        font=dict(family="sans-serif", color="#ffffff", size=8),
        title=dict(font=dict(color="#ffffff", size=10)),
        # X 轴
        xaxis=dict(
            gridcolor="rgba(255,255,255,0.06)",
            gridwidth=0.3,
            griddash="dot",
            zerolinecolor="rgba(0,210,211,0.15)",
            linecolor="rgba(255,255,255,0.5)",
            linewidth=1,
            showline=True,
            tickfont=dict(color="#ffffff", size=7),
            title=dict(font=dict(color="#ffffff", size=7)),
        ),
        # Y 轴
        yaxis=dict(
            gridcolor="rgba(255,255,255,0.06)",
            gridwidth=0.3,
            griddash="dot",
            zerolinecolor="rgba(0,210,211,0.15)",
            linecolor="rgba(255,255,255,0.5)",
            linewidth=1,
            showline=True,
            tickfont=dict(color="#ffffff", size=7),
            title=dict(font=dict(color="#ffffff", size=7)),
        ),
        # Hover 统一风格
        hoverlabel=dict(
            bgcolor="rgba(10,14,26,0.92)",
            bordercolor="rgba(0,210,211,0.4)",
            font=dict(color="#e0e0e0", size=9, family="sans-serif"),
        ),
        # 图例
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(255,255,255,0.15)",
            font=dict(color="#ffffff", size=7),
        ),
        # 色板
        colorway=[
            "#00d2d3", "#ff6b6b", "#ffd93d", "#54a0ff",
            "#ff9f43", "#2ecc71", "#a29bfe", "#6bcb77",
        ],
    ),
)
pio.templates["deep_space"] = DEEP_SPACE_TEMPLATE
pio.templates.default = "deep_space"  # 所有新 Figure 自动使用

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
@st.cache_data(ttl=300)
def cached_weather(city, days): return fetch_weather_single(city, days)

@st.cache_data(ttl=300)
def cached_all_cities_temp():
    """获取广东21地市当前实时观测温度（wttr.in气象站实测数据）"""
    return fetch_all_cities_current()

@st.cache_data(ttl=3600)
def cached_fuel(days): return build_fuel_display_data(days)
@st.cache_data(ttl=3600)
def cached_fuel_summary(): return get_fuel_latest_summary()
@st.cache_data(ttl=300)
def cached_price(): return fetch_electricity_data()


def parse_maintenance_from_disclosure(target_date: str) -> dict:
    """
    从信息披露xlsx解析检修数据
    返回: {"机组检修": DataFrame, "输变电检修": DataFrame, "检修容量": dict}
    """
    import pandas as _pd
    disclosure_dir = os.path.expanduser("~/Desktop/能源电力资料/日前训练数据/信息披露日前")
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
    maint_file = st.file_uploader("🔧 导入检修Excel", type=["xlsx","xls","csv"])
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
    _logo_html = f'<img src="data:image/png;base64,{_logo_b64}" style="height:32px;position:absolute;left:0.8rem;">'
else:
    _logo_html = ''

st.markdown(f'<div class="dash-header">{_logo_html}<span class="dash-title">⚡ 电力市场多源数据监控大屏</span><span class="dash-time">气象:{sw} 燃料:{sf} 电价:{sp} | {_now().strftime("%Y-%m-%d %H:%M")}</span></div>', unsafe_allow_html=True)

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
        fill_poly = f'<polygon points="{" ".join(fill_pts)}" fill="{color}" opacity="0.12"/>'
    return f'<div class="kpi-sparkline"><svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">{fill_poly}{polyline}</svg></div>'

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

# --- 煤价 KPI（sparkline来自燃料日度数据，箭头=环比）---
if fuel_summary.get("煤价最新"):
    c = fuel_summary["煤价最新"]; ch = fuel_summary.get("煤价环比", 0) or 0
    _coal_arrow = _kpi_arrow(c, c / (1 + ch / 100) if ch != 0 else None)
    _coal_sp = ""
    if not fuel_df.empty and "动力煤价格(元/吨)" in fuel_df.columns:
        _coal_sp = _make_sparkline_svg(fuel_df["动力煤价格(元/吨)"].tail(7).tolist(), "#ff9f43", 64, 14)
    kpi += f'<div class="kpi-card"><div class="kpi-label">🪨 动力煤</div><div class="kpi-value" style="color:#ff9f43">{c:.0f}元/吨</div><div class="kpi-delta" style="color:{"#ff6b6b" if ch>0 else "#2ecc71"}">{ch:+.2f}% {_coal_arrow}</div>{_coal_sp}</div>'

# --- LNG KPI（sparkline来自燃料日度数据）---
if fuel_summary.get("LNG出厂价"):
    _lng_val = fuel_summary["LNG出厂价"]
    _lng_sp = ""
    if not fuel_df.empty and "LNG出厂价(元/吨)" in fuel_df.columns:
        _lng_sp = _make_sparkline_svg(fuel_df["LNG出厂价(元/吨)"].tail(7).tolist(), "#54a0ff", 64, 14)
    # 箭头：对比前一天
    _lng_prev = None
    if not fuel_df.empty and "LNG出厂价(元/吨)" in fuel_df.columns and len(fuel_df) >= 2:
        _lng_prev = fuel_df["LNG出厂价(元/吨)"].iloc[-2]
    _lng_arrow = _kpi_arrow(_lng_val, _lng_prev)
    kpi += f'<div class="kpi-card"><div class="kpi-label">⛽ LNG</div><div class="kpi-value" style="color:#54a0ff">{_lng_val:.0f}元/吨</div><div class="kpi-delta" style="color:#888">参考{fuel_summary.get("LNG参考价",0):.2f}元/m³ {_lng_arrow}</div>{_lng_sp}</div>'

# --- 电价均价 KPI（sparkline来自日前节点电价最近7天均价，脉冲>500）---
# 优先使用实际电价数据的日期和均价，而非参考模板
_actual_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "日前节点电价.xlsx")
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
kpi += f'<div class="kpi-card{_elec_pulse}"><div class="kpi-label">📊 电价均价</div><div class="kpi-value" style="color:#00d2d3">{da:.0f}元/MWh</div><div class="kpi-delta" style="color:#888">{ld} {_elec_arrow}</div>{_elec_sp}</div>'

# --- 安全裕度 KPI（脉冲=紧张）---
_margin_pulse = ' kpi-pulse' if margin_lv == "紧张" else ''
kpi += f'<div class="kpi-card{_margin_pulse}"><div class="kpi-label">🛡️ 安全裕度</div><div class="kpi-value" style="color:{margin_color}">{margin_val:.1f}%</div><div class="kpi-delta" style="color:{margin_color}">{margin_lv}</div></div></div>'
st.markdown(kpi, unsafe_allow_html=True)

# ============================================================
# 三列布局：气象+燃料 | 地图+电价 | 检修（等宽）
# ============================================================
col1, col2, col3 = st.columns(3)

# ===== 第一列：气象监测 + 检修计划 =====
with col1:
    # ----- 气象监测 -----
    st.markdown('<div class="mod-card"><div class="mod-head mod-head-w">🌤️ 气象监测</div>', unsafe_allow_html=True)
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
                    mode="lines+markers",line=dict(color="#ff6b6b",width=1.5),marker=dict(size=2),
                    name="气温",fill="tozeroy",fillcolor="rgba(255,107,107,0.1)"))
                for idx,clr,sym in [(today_df["温度(℃)"].idxmax(),"#ff4444","triangle-up"),
                                     (today_df["温度(℃)"].idxmin(),"#4488ff","triangle-down")]:
                    r=today_df.loc[idx]
                    fig1.add_trace(go.Scatter(x=[r["时间"]],y=[r["温度(℃)"]],mode="markers+text",
                        marker=dict(size=6,color=clr,symbol=sym),text=[f"{r['温度(℃)']:.0f}℃"],
                        textposition="top center" if clr=="#ff4444" else "bottom center",
                        textfont=dict(size=8, color=clr),showlegend=False))
            fig1.update_layout(transition=dict(duration=500, easing="cubic-in-out"), height=90,template="deep_space",showlegend=False,
                hovermode="x unified",
                margin=dict(l=30,r=6,t=26,b=22),font=dict(size=7, color="#ffffff"),
                title=dict(text=f"📅 {today.month}月{today.day}日 {CN_WEEKDAYS.get(today.weekday(),'')} 逐时温度(℃)",font=dict(size=9, color="#ffffff")))
            fig1.update_xaxes(dtick=3600000*3,tickformat="%H")
            st.plotly_chart(fig1,use_container_width=True)

            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=agg["标签"],y=agg["最高"],name="最高",mode="lines+markers",
                line=dict(color="#ff6b6b",width=1.5),marker=dict(size=3)))
            fig2.add_trace(go.Scatter(x=agg["标签"],y=agg["均温"],name="均温",mode="lines+markers",
                line=dict(color="#ffd93d",width=1.5,dash="dot"),marker=dict(size=2)))
            fig2.add_trace(go.Scatter(x=agg["标签"],y=agg["最低"],name="最低",mode="lines+markers",
                line=dict(color="#54a0ff",width=1.5),marker=dict(size=3)))
            fig2.add_trace(go.Scattergl(x=list(agg["标签"])+list(agg["标签"][::-1]),
                y=list(agg["最高"])+list(agg["最低"][::-1]),fill="toself",fillcolor="rgba(255,107,107,0.08)",
                line=dict(width=0),showlegend=False,hoverinfo="skip"))
            fig2.update_layout(transition=dict(duration=500, easing="cubic-in-out"), height=90,template="deep_space",showlegend=False,
                hovermode="x unified",
                margin=dict(l=30,r=6,t=26,b=22),font=dict(size=7, color="#ffffff"),
                title=dict(text="📊 预报温度趋势(℃)",font=dict(size=9, color="#ffffff")))
            fig2.update_xaxes(tickangle=-30,tickfont=dict(size=6, color="#ffffff"))
            st.plotly_chart(fig2,use_container_width=True)

        with wc_right:
            fig3 = go.Figure()
            if "风速(m/s)" in daily.columns:
                fig3.add_trace(go.Scatter(x=agg["标签"],y=agg["风速"],name="风速",mode="lines+markers",
                    line=dict(color="#6bcb77",width=1.5),marker=dict(size=4),
                    fill="tozeroy",fillcolor="rgba(107,203,119,0.1)"))
            fig3.update_layout(transition=dict(duration=500, easing="cubic-in-out"), height=90,template="deep_space",showlegend=False,
                hovermode="x unified",
                margin=dict(l=30,r=6,t=26,b=22),font=dict(size=7, color="#ffffff"),
                title=dict(text="🌬️ 预报风速(m/s)",font=dict(size=9, color="#ffffff")))
            fig3.update_xaxes(tickangle=-30,tickfont=dict(size=6, color="#ffffff"))
            st.plotly_chart(fig3,use_container_width=True)

            fig4 = go.Figure()
            if "湿度(%)" in daily.columns:
                fig4.add_trace(go.Scatter(x=agg["标签"],y=agg["湿度"],name="湿度",mode="lines+markers",
                    line=dict(color="#a29bfe",width=1.5),marker=dict(size=4),
                    fill="tozeroy",fillcolor="rgba(162,155,254,0.1)"))
            fig4.update_layout(transition=dict(duration=500, easing="cubic-in-out"), height=90,template="deep_space",showlegend=False,
                hovermode="x unified",
                margin=dict(l=30,r=6,t=26,b=22),font=dict(size=7, color="#ffffff"),
                title=dict(text="💧 预报湿度(%)",font=dict(size=9, color="#ffffff")))
            fig4.update_xaxes(tickangle=-30,tickfont=dict(size=6, color="#ffffff"))
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
            _sub_s = f'<span style="font-size:0.45rem;color:#888;margin-left:2px">{_sub}</span>' if _sub else ''
            _wx_html += f'<div style="flex:1;text-align:center"><div style="font-size:0.5rem;color:#7aa">{_label}</div><div style="font-size:0.7rem;color:#e0e0e0">{_val}{_sub_s}</div></div>'
        _wx_html += '</div>'
        st.markdown(_wx_html, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # ----- 检修计划（来自披露文件，日期与电价模块联动）-----
    st.markdown('<div class="mod-card"><div class="mod-head mod-head-m">🔧 检修计划</div>', unsafe_allow_html=True)
    _price_date = st.session_state.get("price_date_val", datetime.now().strftime("%Y-%m-%d"))
    _maint_data = parse_maintenance_from_disclosure(_price_date)

    # 数据来源日期（橙色）
    st.markdown(f'<span style="font-size:0.6rem;color:#ff9f43;font-weight:bold">📅 数据日期：{_price_date}</span>', unsafe_allow_html=True)

    if _maint_data["检修容量"]:
        _cap = _maint_data["检修容量"]
        st.markdown(
            f'<div style="display:flex;gap:8px;margin:4px 0">'
            f'<span style="font-size:0.8rem;color:#aaa">总检修容量 <b style="color:#e0e0e0">{_cap["总容量"]:.0f}</b> MW</span>'
            f'<span style="font-size:0.8rem;color:#aaa">市场机组 <b style="color:#e0e0e0">{_cap["市场机组容量"]:.0f}</b> MW</span>'
            f'</div>', unsafe_allow_html=True)

    _mach = _maint_data.get("机组检修", pd.DataFrame())
    _line = _maint_data.get("输变电检修", pd.DataFrame())

    # 表格深色主题样式（HTML表格，循环滚动展示）
    def _df_to_dark_html(df, max_height=120, scroll=True, col_widths=None):
        """DataFrame → 深色主题 HTML 表格（表头固定，内容循环滚动）"""
        th_style = 'background:#14202e;color:#00d2d3;font-size:0.5rem;padding:3px 6px;border:1px solid rgba(0,210,211,0.15);font-weight:bold;line-height:1.5;'
        td_style = 'background:#0d1117;color:#e0e0e0;font-size:0.5rem;padding:2px 6px;border:1px solid rgba(255,255,255,0.06);'

        row_count = len(df)
        anim_duration = max(row_count * 3, 10)

        # 计算列宽比例
        col_count = len(df.columns)
        if col_widths:
            widths = col_widths
        else:
            widths = [f'{100/col_count:.1f}%'] * col_count

        # 表头（固定不滚动）
        html = f'<table style="width:100%;border-collapse:collapse;table-layout:fixed;">'
        html += '<thead><tr>'
        for i, col in enumerate(df.columns):
            w = widths[i] if i < len(widths) else widths[-1]
            html += f'<th style="{th_style}width:{w};">{col}</th>'
        html += '</tr></thead></table>'

        # 表体（循环滚动）
        body_height = max_height - 40
        html += f'<div class="table-scroll-wrap" style="max-height:{body_height}px;overflow:hidden;">'

        if scroll and row_count > 3:
            html += f'<div class="table-scroll-inner" style="animation:table-scroll {anim_duration}s linear infinite;">'

        html += f'<table style="width:100%;border-collapse:collapse;table-layout:fixed;"><tbody>'

        rows_html = ''
        for _, row in df.iterrows():
            rows_html += '<tr>'
            for i, val in enumerate(row):
                w = widths[i] if i < len(widths) else widths[-1]
                rows_html += f'<td style="{td_style}width:{w};">{val}</td>'
            rows_html += '</tr>'

        html += rows_html
        if scroll and row_count > 3:
            html += rows_html

        html += '</tbody></table>'

        if scroll and row_count > 3:
            html += '</div>'

        html += '</div>'
        return html

    if not _mach.empty:
        st.markdown(f'<span style="font-size:0.6rem;font-weight:bold;color:#ff9f43">🔩 机组检修（{len(_mach)}台）</span>', unsafe_allow_html=True)
        st.markdown(_df_to_dark_html(_mach, 80, col_widths=["30%", "15%", "15%", "20%", "20%"]), unsafe_allow_html=True)

    if not _line.empty:
        st.markdown(f'<span style="font-size:0.6rem;font-weight:bold;color:#ff9f43">⚡ 输变电检修（{len(_line)}条）</span>', unsafe_allow_html=True)
        st.markdown(_df_to_dark_html(_line, 140), unsafe_allow_html=True)

    if _mach.empty and _line.empty and not _maint_data["检修容量"]:
        st.info(f"{_price_date} 无检修数据，请先上传披露文件")

    st.markdown('</div>', unsafe_allow_html=True)

# ===== 第二列：广东地图 + 燃料价格 =====
with col2:
    # ----- 广东地图 -----
    st.markdown('<div class="mod-card"><div class="mod-head mod-head-g">🗺️ 广东地市实时温度</div>', unsafe_allow_html=True)
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

        m = folium.Map(tiles="CartoDB dark_matter",control_scale=False,prefer_canvas=True,
                       attr=" ")

        # 注入深色背景CSS到地图内部（作用于iframe内）
        dark_css = """
        <style>
            body, .leaflet-container { background: #0a0e1a !important; }
            .leaflet-control-zoom a { background: #1a1e2a !important; color: #aaa !important; border-color: #333 !important; }
            /* 平滑缩放过渡 */
            .leaflet-zoom-anim .leaflet-zoom-animated {
                transition: transform 0.3s ease-out;
            }
            .leaflet-tile { transition: opacity 0.3s ease; }
            /* 高温脉冲动画 */
            @keyframes map-pulse {
                0%, 100% { transform: scale(1); opacity: 1; }
                50%      { transform: scale(1.15); opacity: 0.8; }
            }
        </style>
        """
        m.get_root().html.add_child(folium.Element(dark_css))
        m.fit_bounds([[min(lats),min(lons)],[max(lats),max(lons)]], padding=0)

        folium.GeoJson(gd_temp,
            style_function=lambda f:{"fillColor":cmap(f["properties"].get("温度",0)),"color":"white","weight":1.5,"fillOpacity":0.7},
            tooltip=GeoJsonTooltip(fields=["name","温度"],aliases=["城市:","温度:"],
                style="background:rgba(0,0,0,.8);color:white;padding:3px;border-radius:4px;font-size:11px;"),
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
                _temp_color = '#fff'
                _glow = 'text-shadow:1px 1px 3px black,-1px -1px 3px black,1px -1px 3px black,-1px 1px 3px black;'

            folium.Marker(location=[ctr[1],ctr[0]],icon=folium.DivIcon(
                html=f'<div style="font-size:10px;font-weight:bold;color:#fff;text-align:center;{_glow}{_pulse}">{nm}<br><span style="font-size:12px;color:{_temp_color}">{temp:.0f}℃</span></div>',
                icon_size=(55,28),icon_anchor=(27,14))).add_to(m)

        st_folium(m,width="100%",height=320,returned_objects=[])
        # 色阶图例
        _legend_html = '''<div style="display:flex;align-items:center;gap:4px;margin-top:2px;font-size:0.5rem;color:#fff">
            <span>18℃</span>
            <div style="flex:1;height:8px;border-radius:4px;background:linear-gradient(90deg,#2196F3,#00BCD4,#FFC107,#FF9800,#F44336,#B71C1C,#9C27B0)"></div>
            <span>40℃</span>
        </div>'''
        st.markdown(_legend_html, unsafe_allow_html=True)
        avg_t=city_temps["温度"].mean(); mx=city_temps.loc[city_temps["温度"].idxmax()]; mn=city_temps.loc[city_temps["温度"].idxmin()]
        st.markdown(f'<span style="font-size:0.55rem;color:#aaa">均温**{avg_t:.1f}℃** | 最高{mx["城市"]}**{mx["温度"]:.1f}℃** | 最低{mn["城市"]}**{mn["温度"]:.1f}℃**</span>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # ----- 燃料价格 -----
    st.markdown('<div class="mod-card"><div class="mod-head mod-head-f">⛽ 燃料价格</div>', unsafe_allow_html=True)
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
                line=dict(color="#ff9f43",width=1.5),fill="tozeroy",fillcolor="rgba(255,159,67,0.1)"))
            fig_coal.update_layout(transition=dict(duration=500, easing="cubic-in-out"), height=110,template="deep_space",showlegend=False,
                hovermode="x unified",
                margin=dict(l=30,r=10,t=30,b=30),font=dict(size=8, color="#ffffff"),
                title=dict(text="🪨 动力煤价格(元/吨)",font=dict(size=10, color="#ffffff")))
            fig_coal.update_xaxes(tickangle=-30,tickfont=dict(size=7, color="#ffffff"))
            st.plotly_chart(fig_coal,use_container_width=True)

        # LNG气价
        if "LNG出厂价(元/吨)" in fuel_df.columns:
            fig_lng=go.Figure()
            fig_lng.add_trace(go.Scatter(x=fuel_df["日期标签"],y=fuel_df["LNG出厂价(元/吨)"],
                mode="lines+markers",marker=dict(size=3),
                line=dict(color="#54a0ff",width=1.5),fill="tozeroy",fillcolor="rgba(84,160,255,0.1)"))
            fig_lng.update_layout(transition=dict(duration=500, easing="cubic-in-out"), height=110,template="deep_space",showlegend=False,
                hovermode="x unified",
                margin=dict(l=30,r=10,t=30,b=30),font=dict(size=8, color="#ffffff"),
                title=dict(text="⛽ LNG出厂价(元/吨)",font=dict(size=10, color="#ffffff")))
            fig_lng.update_xaxes(tickangle=-30,tickfont=dict(size=7, color="#ffffff"))
            st.plotly_chart(fig_lng,use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ===== 第三列：电价分析 =====
with col3:
    # ----- 电价分析 -----
    st.markdown('<div class="mod-card"><div class="mod-head mod-head-p">📊 电价分析</div>', unsafe_allow_html=True)

    # 信息披露文件上传
    _disclosure_dir = os.path.expanduser("~/Desktop/能源电力资料/日前训练数据/信息披露日前")
    os.makedirs(_disclosure_dir, exist_ok=True)

    with st.expander("📤 上传信息披露文件", expanded=False):
        _upload_file = st.file_uploader(
            "选择信息披露查询预测信息文件",
            type=["xlsx", "xls"],
            key="disclosure_upload",
            help="文件名格式：信息披露查询预测信息(YYYY-MM-DD).xlsx"
        )
        if _upload_file is not None:
            _save_path = os.path.join(_disclosure_dir, _upload_file.name)
            with open(_save_path, "wb") as f:
                f.write(_upload_file.getbuffer())
            st.success(f"✅ 已保存: {_upload_file.name}")

    # 加载实际电价和预测电价
    _actual_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "日前节点电价.xlsx")
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

        sel_label = st.selectbox("选择日期", [_date_labels[d] for d in _all_dates],
                                  index=_default_idx, key="price_date_sel",
                                  on_change=_on_date_change)
        # 反查日期字符串
        sel_date = [d for d, lb in _date_labels.items() if lb == sel_label][0]
        st.session_state["price_date_val"] = sel_date  # 存储实际日期字符串

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
                    line=dict(color="#00d2d3", width=2),
                    mode="lines+markers", marker=dict(size=3),
                    fill="tozeroy", fillcolor="rgba(0,210,211,0.1)"))
                has_data = True

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
                name="模型预测", line=dict(color="#ff6b6b", width=2),
                mode="lines+markers", marker=dict(size=4),
                fill="tozeroy", fillcolor="rgba(255,107,107,0.1)"))
            has_data = True

        if not has_data:
            if st.button(f"🔮 预测 {sel_date} 电价", key="btn_forecast"):
                with st.spinner("模型推理中（约1-2分钟）..."):
                    from forecast.predictor import forecast_price
                    import io, contextlib
                    f = io.StringIO()
                    with contextlib.redirect_stdout(f):
                        fc_result = forecast_price(sel_date)
                    log_output = f.getvalue()

                if not fc_result.empty:
                    # 保存到 session_state
                    st.session_state[_fc_key] = {
                        "result": fc_result,
                        "log": log_output,
                    }

                    fig.add_trace(go.Scattergl(
                        x=fc_result["小时"], y=fc_result["预测电价(元/MWh)"],
                        name="模型预测", line=dict(color="#ff6b6b", width=2),
                        mode="lines+markers", marker=dict(size=4),
                        fill="tozeroy", fillcolor="rgba(255,107,107,0.1)"))
                    has_data = True

                    # 保存CSV
                    _pred_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "predictions")
                    os.makedirs(_pred_dir, exist_ok=True)
                    fc_result.to_csv(os.path.join(_pred_dir, f"forecast_{sel_date}.csv"), index=False)

                    # 追加到广东日前电价预测.xlsx
                    _xlsx_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "广东日前电价预测.xlsx")
                    _hour_cols_fc = [f"{i}时" for i in range(24)]
                    _new_row = {"日期": sel_date, "模型": "校准后"}
                    for _h in range(24):
                        _new_row[f"{_h}时"] = fc_result.iloc[_h]["预测电价(元/MWh)"]

                    if os.path.exists(_xlsx_path):
                        _exist_df = pd.read_excel(_xlsx_path)
                        # 检查是否已有该日期+模型的数据
                        _mask = (_exist_df["日期"].astype(str) == sel_date) & (_exist_df["模型"] == "校准后")
                        if _mask.any():
                            # 更新已有行
                            for _h in range(24):
                                _exist_df.loc[_mask, f"{_h}时"] = _new_row[f"{_h}时"]
                        else:
                            # 追加新行
                            _new_df = pd.DataFrame([_new_row])
                            _exist_df = pd.concat([_exist_df, _new_df], ignore_index=True)
                        _exist_df = _exist_df.sort_values(["日期", "模型"]).reset_index(drop=True)
                        _exist_df.to_excel(_xlsx_path, index=False, engine="openpyxl")
                    else:
                        pd.DataFrame([_new_row]).to_excel(_xlsx_path, index=False, engine="openpyxl")
                else:
                    st.error("预测失败，请检查披露文件是否已上传")

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

            fig.update_layout(transition=dict(duration=500, easing="cubic-in-out"), height=140, template="deep_space",
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=7, color="#ffffff")),
                margin=dict(l=30, r=10, t=20, b=8), font=dict(size=8, color="#ffffff"),
                shapes=_shapes,
                xaxis=dict(dtick=3, tickvals=list(range(0,24,3)), ticktext=[f"{i}时" for i in range(0,24,3)]),
                yaxis=dict(title="元/MWh", title_font=dict(size=7, color="#ffffff")))
            st.plotly_chart(fig, use_container_width=True)

            # 指标行
            if not _actual_df.empty:
                _act = _actual_df[_actual_df["_日期"] == sel_date]
                if not _act.empty:
                    _vals = [_act.iloc[0][h] for h in _hour_cols]
                    pk_h = _vals.index(max(_vals))
                    vl_h = _vals.index(min(_vals))
                    pc1, pc2, pc3 = st.columns(3)
                    with pc1: st.metric("均价", f"{sum(_vals)/len(_vals):.0f}")
                    with pc2: st.metric("峰", f"{max(_vals):.0f}", f"{pk_h}时")
                    with pc3: st.metric("谷", f"{min(_vals):.0f}", f"{vl_h}时")
        else:
            st.info(f"{sel_date} 无电价数据，点击上方按钮进行模型预测")
    else:
        st.warning("无电价数据文件")

    st.markdown('</div>', unsafe_allow_html=True)

    # ============================================================
    # 历史电价热力图（24h × 30d）
    # ============================================================
    st.markdown('<div class="mod-card"><div class="mod-head mod-head-p">🔥 历史电价热力图</div>', unsafe_allow_html=True)
    _actual_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "日前节点电价.xlsx")
    if os.path.exists(_actual_path):
        try:
            _heat_df = pd.read_excel(_actual_path)
            _hour_cols = [f"{i}时" for i in range(24)]
            # 日期列标准化
            _heat_df["_date"] = pd.to_datetime(_heat_df["日期"], errors="coerce")
            _heat_df = _heat_df.dropna(subset=["_date"]).sort_values("_date")
            # 取最近30天
            _heat_df = _heat_df.tail(30).copy()
            _heat_df["_label"] = _heat_df["_date"].apply(lambda d: f"{d.month}月{d.day}日")
            # 构建矩阵 (行=小时, 列=日期)
            _z = _heat_df[_hour_cols].values.T.tolist()  # 24 × N
            _x = _heat_df["_label"].tolist()
            _y = [f"{i}时" for i in range(24)]
            # 自定义色阶：绿(低)→黄→红(高)
            _colorscale = [
                [0.0, "#1a9641"],
                [0.2, "#a6d96a"],
                [0.4, "#ffffbf"],
                [0.6, "#fdae61"],
                [0.8, "#f46d43"],
                [1.0, "#d73027"],
            ]
            _heat_fig = go.Figure(data=go.Heatmap(
                z=_z, x=_x, y=_y,
                colorscale=_colorscale,
                colorbar=dict(title=dict(text="元/MWh", font=dict(size=8, color="#ffffff")), tickfont=dict(size=7, color="#ffffff"), len=0.8, thickness=8),
                hovertemplate="日期: %{x}<br时段: %{y}<br电价: %{z:.0f} 元/MWh<extra></extra>",
            ))

            # 当前时刻标记线
            _now_hour = _now().hour
            _now_label = f"{_now_hour}时"
            if _now_label in _y:
                _hour_idx = _y.index(_now_label)
                _heat_fig.add_hline(y=_hour_idx, line_dash="dash", line_color="rgba(0,210,211,0.6)", line_width=1,
                    annotation_text="当前", annotation_position="right",
                    annotation_font=dict(color="#00d2d3", size=8))

            # 今日标记线
            _today_str = _now().strftime("%-m月%-d日")
            for _xi, _xl in enumerate(_x):
                if _today_str in _xl:
                    _heat_fig.add_vline(x=_xi, line_dash="dash", line_color="rgba(0,210,211,0.4)", line_width=1)
                    break

            _heat_fig.update_layout(
                height=200, template="deep_space",
                margin=dict(l=35, r=10, t=5, b=30),
                font=dict(size=7, color="#ffffff"),
                xaxis=dict(tickangle=-45, tickfont=dict(size=6, color="#ffffff"), side="bottom"),
                yaxis=dict(tickfont=dict(size=6, color="#ffffff"), autorange="reversed"),
            )
            st.plotly_chart(_heat_fig, use_container_width=True)
            # 底部统计
            _all_vals = _np.array(_heat_df[_hour_cols].values, dtype=float).flatten()
            _all_vals = _all_vals[~_np.isnan(_all_vals)]
            if len(_all_vals) > 0:
                st.markdown(f'<span style="font-size:0.55rem;color:#aaa">近30天：均价**{_all_vals.mean():.0f}** | 峰值**{_all_vals.max():.0f}** | 谷值**{_all_vals.min():.0f}** | 峰谷差**{_all_vals.max()-_all_vals.min():.0f}** 元/MWh</span>', unsafe_allow_html=True)
        except Exception as e:
            st.warning(f"热力图数据加载失败: {e}")
    else:
        st.info("未找到日前节点电价.xlsx，无法生成热力图")
    st.markdown('</div>', unsafe_allow_html=True)
