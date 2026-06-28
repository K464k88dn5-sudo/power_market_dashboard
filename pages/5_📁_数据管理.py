"""
数据管理页面 - 电力市场多源数据监控大屏
"""
import streamlit as st
import pandas as pd
import os
import sys
import json
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(page_title="数据管理", page_icon="📁", layout="wide")

from header_nav import render_header_nav
render_header_nav("数据管理", margin_top="-12px")



_CN_TZ = timezone(timedelta(hours=8))
def _now(): return datetime.now(_CN_TZ)

# 配置文件路径
CONFIG_PATH = os.path.expanduser("~/Desktop/power_market_dashboard/data/data_sources.json")

def load_config():
    """加载配置"""
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"数据源": [], "缓存配置": {}}

def save_config(config):
    """保存配置"""
    config["最后更新"] = _now().isoformat()
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

# ============================================================
# 数据源管理（最上方）
# ============================================================
with st.container(border=True):
    st.markdown('<div class="mod-head mod-head-o">🔗 数据源管理<span class="mod-sub">查看/修改数据来源</span></div>', unsafe_allow_html=True)
    
    config = load_config()
    sources = config.get("数据源", [])
    
    # 显示数据源表格
    if sources:
        df = pd.DataFrame(sources)
        st.dataframe(df[["名称", "类型", "来源", "路径", "状态", "更新频率"]], 
                     use_container_width=True, hide_index=True, height=280)
    
    # 操作按钮
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("➕ 添加数据源", use_container_width=True):
            st.session_state["show_add_form"] = True
    with col2:
        if st.button("🔄 刷新状态", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    with col3:
        if st.button("📁 查看配置文件", use_container_width=True):
            st.session_state["show_config"] = True

# 显示配置文件内容
if st.session_state.get("show_config", False):
    with st.container(border=True):
        st.markdown('<div class="mod-head mod-head-w">📄 配置文件内容</div>', unsafe_allow_html=True)
        st.markdown(f'<span style="font-size:0.6rem;color:#666">路径: {CONFIG_PATH}</span>', unsafe_allow_html=True)
        
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                config_content = f.read()
            st.code(config_content, language='json')
            
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    "⬇️ 下载配置文件",
                    data=config_content,
                    file_name="data_sources.json",
                    mime="application/json",
                    use_container_width=True
                )
            with col2:
                if st.button("❌ 关闭", use_container_width=True):
                    st.session_state["show_config"] = False
                    st.rerun()
        else:
            st.warning("配置文件不存在")


# 数据文件路径
DATA_PATHS = {
    "电价数据": os.path.expanduser("~/projects/能源电力资料/日前训练数据/日前节点电价.xlsx"),
    "燃料缓存": os.path.expanduser("~/Desktop/power_market_dashboard/data/fuel_cache.json"),
    "气象缓存": os.path.expanduser("~/Desktop/power_market_dashboard/data/weather_cache.json"),
    "检修数据": os.path.expanduser("~/Desktop/power_market_dashboard/disclosure"),
}

# ============================================================
# 三列布局：修改路径 | 数据状态 | 缓存状态
# ============================================================
col_edit, col_status, col_cache = st.columns(3)

with col_edit:
    with st.container(border=True):
        st.markdown('<div class="mod-head mod-head-b">✏️ 修改数据源路径<span class="mod-sub">更新文件路径</span></div>', unsafe_allow_html=True)
        
        if sources:
            selected = st.selectbox("选择数据源", [s["名称"] for s in sources], key="edit_source_sel")
            
            for s in sources:
                if s["名称"] == selected:
                    st.markdown(f'<span style="font-size:0.7rem;color:#666">当前: <b>{s["路径"][:30]}...</b></span>', unsafe_allow_html=True)
                    
                    new_path = st.text_input("新路径", value=s["路径"], key="edit_path_input")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ 保存", key="save_path_btn", use_container_width=True):
                            if new_path and new_path != s["路径"]:
                                s["路径"] = new_path
                                save_config(config)
                                st.success(f"✅ 已更新")
                                st.rerun()
                    with col2:
                        if st.button("❌ 取消", key="cancel_edit_btn", use_container_width=True):
                            st.rerun()
                    break

with col_status:
    with st.container(border=True):
        st.markdown('<div class="mod-head mod-head-b">📊 数据文件状态</div>', unsafe_allow_html=True)
        
        for name, path in DATA_PATHS.items():
            if os.path.exists(path):
                if os.path.isfile(path):
                    size = os.path.getsize(path)
                    mtime = datetime.fromtimestamp(os.path.getmtime(path)).strftime('%m-%d %H:%M')
                    st.markdown(f'<span style="font-size:0.7rem;color:#666">✅ <b>{name}</b>: {size//1024}KB | {mtime}</span>', unsafe_allow_html=True)
                elif os.path.isdir(path):
                    count = len([f for f in os.listdir(path) if f.endswith('.xlsx')])
                    st.markdown(f'<span style="font-size:0.7rem;color:#666">✅ <b>{name}</b>: {count}个文件</span>', unsafe_allow_html=True)
            else:
                st.markdown(f'<span style="font-size:0.7rem;color:#dc3545">❌ <b>{name}</b></span>', unsafe_allow_html=True)

with col_cache:
    with st.container(border=True):
        st.markdown('<div class="mod-head mod-head-w">🕐 缓存状态</div>', unsafe_allow_html=True)
        
        now = _now()
        for name in ["燃料缓存", "气象缓存"]:
            path = DATA_PATHS[name]
            if os.path.exists(path):
                try:
                    with open(path, 'r') as f:
                        data = json.load(f)
                    ts = data.get('timestamp', '')
                    if ts:
                        cache_time = datetime.fromisoformat(ts)
                        age_hours = (now - cache_time).total_seconds() / 3600
                        status = "🟢" if age_hours < 6 else "🟡"
                        st.markdown(f'<span style="font-size:0.7rem;color:#666">{status} <b>{name}</b>: {age_hours:.1f}h</span>', unsafe_allow_html=True)
                except:
                    st.markdown(f'<span style="font-size:0.7rem;color:#888">⚪ <b>{name}</b></span>', unsafe_allow_html=True)

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
