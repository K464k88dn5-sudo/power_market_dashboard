"""
系统配置页面 - 电力市场多源数据监控大屏
"""
import streamlit as st
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(page_title="系统配置", page_icon="⚙️", layout="wide")

from header_nav import render_header_nav
render_header_nav("系统配置", margin_top="-12px")



st.markdown("## ⚙️ 系统配置")
st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    with st.container(border=True):
        st.markdown('<div class="mod-head mod-head-b">⏰ 缓存配置</div>', unsafe_allow_html=True)
        
        st.markdown('<span style="font-size:0.65rem;color:#666">气象数据缓存: 6小时</span>', unsafe_allow_html=True)
        st.markdown('<span style="font-size:0.65rem;color:#666">燃料数据缓存: 2小时</span>', unsafe_allow_html=True)
        st.markdown('<span style="font-size:0.65rem;color:#666">电价数据缓存: 30分钟</span>', unsafe_allow_html=True)
        st.markdown('<span style="font-size:0.65rem;color:#666">自动刷新: 5分钟</span>', unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown('<div class="mod-head mod-head-w">🌤️ 气象配置</div>', unsafe_allow_html=True)
        
        st.markdown('<span style="font-size:0.65rem;color:#666">数据源: Open-Meteo API</span>', unsafe_allow_html=True)
        st.markdown('<span style="font-size:0.65rem;color:#666">更新频率: 每10分钟</span>', unsafe_allow_html=True)
        st.markdown('<span style="font-size:0.65rem;color:#666">覆盖范围: 广东21地市</span>', unsafe_allow_html=True)

with col2:
    with st.container(border=True):
        st.markdown('<div class="mod-head mod-head-f">⛽ 燃料配置</div>', unsafe_allow_html=True)
        
        st.markdown('<span style="font-size:0.65rem;color:#666">煤价数据源: CCTD环渤海港口</span>', unsafe_allow_html=True)
        st.markdown('<span style="font-size:0.65rem;color:#666">LNG数据源: SHPGX上海石油天然气</span>', unsafe_allow_html=True)
        st.markdown('<span style="font-size:0.65rem;color:#666">更新频率: 每1小时</span>', unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown('<div class="mod-head mod-head-p">📊 电价配置</div>', unsafe_allow_html=True)
        
        st.markdown('<span style="font-size:0.65rem;color:#666">数据源: 广东电力交易中心</span>', unsafe_allow_html=True)
        st.markdown('<span style="font-size:0.65rem;color:#666">更新频率: 实时</span>', unsafe_allow_html=True)
        st.markdown('<span style="font-size:0.65rem;color:#666">覆盖范围: 全省节点</span>', unsafe_allow_html=True)

# 页脚
st.markdown('''<div style="margin-top:4px;padding:16px 0 8px;border-top:1px solid #e5e5e7;text-align:center;">
    <div style="display:flex;justify-content:center;align-items:center;gap:24px;flex-wrap:wrap;">
        <span style="font-size:0.6rem;color:#888;">📊 数据来源: Open-Meteo · CCTD · SHPGX · 广东电力交易中心</span>
        <span style="font-size:0.6rem;color:#888;">🔄 更新周期: 气象10分钟 · 燃料1小时 · 电价实时</span>
    </div>
    <div style="margin-top:8px;font-size:0.55rem;color:#aaa;">
        © 2024-2026 电力市场多源数据监控大屏 v2.0 | Powered by Streamlit
    </div>
</div>''', unsafe_allow_html=True)
