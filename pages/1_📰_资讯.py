"""
电力市场资讯 — 独立页面
"""

import streamlit as st
import pandas as pd
import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_sources import fetch_price_news

st.set_page_config(page_title="电力市场资讯", page_icon="📰", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 1rem !important; }
    #MainMenu, footer, header { visibility: hidden; }
    .news-card {
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        border: 1px solid #2a2a4a; border-radius: 8px;
        padding: 0.8rem 1rem; margin-bottom: 0.5rem;
    }
    .news-title { font-size: 0.95rem; color: #e0e0e0; }
    .news-title a { color: #54a0ff; text-decoration: none; }
    .news-title a:hover { text-decoration: underline; }
    .news-meta { font-size: 0.75rem; color: #888; margin-top: 0.3rem; }
</style>
""", unsafe_allow_html=True)

st.markdown("## 📰 电力市场资讯")

@st.cache_data(ttl=3600)
def cached_news():
    return fetch_price_news()

news = cached_news()

if news.empty:
    st.info("资讯获取中，请稍后刷新...")
else:
    # 筛选
    col1, col2 = st.columns([3, 1])
    with col2:
        sources = ["全部"] + sorted(news["来源"].unique().tolist()) if "来源" in news.columns else ["全部"]
        sel_source = st.selectbox("筛选来源", sources)

    filtered = news if sel_source == "全部" else news[news["来源"] == sel_source]

    st.caption(f"共 {len(filtered)} 条资讯")

    for _, r in filtered.iterrows():
        st.markdown(f"""
        <div class="news-card">
            <div class="news-title"><a href="{r.get('链接', '#')}" target="_blank">{r['标题']}</a></div>
            <div class="news-meta">{r.get('来源', '')} | {r.get('时间', '')}</div>
        </div>
        """, unsafe_allow_html=True)
