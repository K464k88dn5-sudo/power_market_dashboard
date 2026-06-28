"""
共享的CSS样式模块 - 与电力大屏设计规范一致
"""

SHARED_CSS = """
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

    /* 隐藏侧边栏导航 */
    [data-testid="stSidebarNav"] {
        display: none !important;
    }
    section[data-testid="stSidebar"] {
        display: none !important;
    }

    /* 标题栏 */
    .dash-header {
        margin-top: 6px;
        background: linear-gradient(135deg, rgba(255,255,255,0.9) 0%, rgba(240,242,245,0.95) 100%);
        border: 1px solid #ffffff;
        border-radius: 14px;
        padding: 8px 16px;
        margin-bottom: 12px;
        display: flex; align-items: center; justify-content: center; gap: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.06);
        position: relative;
    }

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

    /* st.container(border=True) 样式 */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: linear-gradient(180deg, #ffffff 0%, #f8f9fa 100%) !important;
        border: 1px solid #ffffff !important;
        border-radius: 12px !important;
        padding: 12px 12px 20px 12px !important;
        margin-bottom: 12px !important;
        box-shadow: 
            0 1px 2px rgba(0,0,0,0.04),
            0 2px 4px rgba(0,0,0,0.06),
            0 4px 8px rgba(0,0,0,0.08),
            0 8px 16px rgba(0,0,0,0.06) !important;
    }

    /* 模块标题 */
    .mod-head {
        font-size: 0.8rem; font-weight: 600;
        padding: 0.35rem 0.5rem; margin-bottom: 0.3rem;
        border-bottom: 2px solid #e5e5e7;
        color: #1D1D1F;
        display: flex; align-items: baseline; gap: 8px;
        background: linear-gradient(180deg, #ffffff 0%, #f8f9fa 100%);
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.06);
    }
    .mod-sub {
        font-size: 0.6rem; font-weight: 400; color: #86868B;
    }

    /* 图表容器 */
    .stPlotlyChart {
        margin: 0 !important; padding: 0.3rem !important;
        background: transparent !important;
        border-radius: 10px !important;
        border: 1px solid #ffffff !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.06);
        overflow: hidden !important;
    }

    /* Metric样式 */
    [data-testid="stMetricValue"] { font-size: 0.8rem !important; color: #1a1a1a !important; }
    [data-testid="stMetricLabel"] { font-size: 0.55rem !important; color: #666 !important; }
    [data-testid="stMetricDelta"] { font-size: 0.55rem !important; }
    [data-testid="stMetric"] { padding: 0.05rem 0 !important; }

    /* DataFrame样式 */
    [data-testid="stDataFrame"] th { background: #F5F5F7 !important; color: #1a1a1a !important; font-size: 12px !important; text-align: center !important; }
    [data-testid="stDataFrame"] td { background: #ffffff !important; color: #1a1a1a !important; font-size: 12px !important; text-align: center !important; }

    /* 按钮样式 */
    .stButton > button {
        border-radius: 8px !important;
        font-size: 0.75rem !important;
        border: 1px solid #ffffff !important;
        background: rgba(255,255,255,0.8) !important;
        color: #1D1D1F !important;
        transition: all 0.2s !important;
        margin: 0 !important;
    }

    .stButton > button:active {
        background: #0D7A3F !important;
        border-color: #0D7A3F !important;
    }

    /* Selectbox样式 */
    div[data-baseweb="select"] {
        border-radius: 8px !important;
        border: 1px solid #ffffff !important;
    }

    /* 隐藏不需要的元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* 强制所有容器边框为白色 */
    div[data-testid="stVerticalBlockBorderWrapper"],
    div[data-testid="stVerticalBlockBorderWrapper"] > div,
    div[data-testid="stVerticalBlockBorderWrapper"] > div > div {
        border-color: #ffffff !important;
        border: 1px solid #ffffff !important;
    }
    
    /* 强制所有卡片边框为白色 */
    .stMarkdown,
    .stMarkdown > div,
    .stMarkdown > div > div {
        border-color: #ffffff !important;
    }

    /* 确保图表背景透明 */
    .stPlotlyChart > div {
        background: transparent !important;
        overflow: hidden !important;
    }
    .stPlotlyChart .plotly .main-svg {
        background: transparent !important;
    }
    .stPlotlyChart .plotly .svg-container {
        background: transparent !important;
    }

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




    /* 导航按钮悬停效果（不覆盖选中状态） */
    .stButton > button:hover:not([style*="background: #007AFF"]) {
        background: #87CEEB !important;
        color: #ffffff !important;
        border-color: #87CEEB !important;
    }


    /* 减少标题栏和导航栏之间的间距 */
    .stMarkdown {
        margin-bottom: 0 !important;
    }

    /* 减少标题栏和导航栏之间的间距 */
    [data-testid="stVerticalBlock"] > div {
        gap: 0 !important;
    }
</style>
"""

def inject_styles():
    """注入共享样式"""
    import streamlit as st
    st.markdown(SHARED_CSS, unsafe_allow_html=True)
