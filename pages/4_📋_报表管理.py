"""
历史数据页面 - 电力市场多源数据监控大屏
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta, timezone
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(page_title="报表管理", page_icon="📋", layout="wide")

_CN_TZ = timezone(timedelta(hours=8))
def _now(): return datetime.now(_CN_TZ)

# 标题栏和导航栏
from header_nav import render_header_nav
render_header_nav("报表管理", margin_top="-12px")




# 数据路径
PRICE_PATH = os.path.expanduser("~/projects/能源电力资料/日前训练数据/日前节点电价.xlsx")

# 读取电价数据
@st.cache_data(ttl=600)
def load_price_data():
    if os.path.exists(PRICE_PATH):
        df = pd.read_excel(PRICE_PATH)
        df['日期'] = pd.to_datetime(df['日期'])
        return df
    return pd.DataFrame()

price_df = load_price_data()

if price_df.empty:
    st.warning("无电价数据")
else:
    # 侧边栏控制
    with st.sidebar:
        st.markdown("## ⚙️ 查询选项")
        
        # 数据类型
        data_type = st.selectbox("数据类型", ["日电价明细", "月度统计", "年度对比", "热力图"])
        
        # 日期范围
        min_date = price_df['日期'].min().date()
        max_date = price_df['日期'].max().date()
        
        if data_type == "日电价明细":
            selected_date = st.date_input("选择日期", value=max_date, min_value=min_date, max_value=max_date)
        elif data_type == "月度统计":
            months = sorted(price_df['日期'].dt.to_period('M').unique(), reverse=True)
            selected_month = st.selectbox("选择月份", [str(m) for m in months])
        elif data_type == "年度对比":
            years = sorted(price_df['日期'].dt.year.unique(), reverse=True)
            selected_years = st.multiselect("选择年份", years, default=[years[0]])
        else:
            date_range = st.date_input("日期范围", value=(max_date - timedelta(days=90), max_date), min_value=min_date, max_value=max_date)
    
    hour_cols = [f"{i}时" for i in range(24)]
    
    if data_type == "日电价明细":
        st.markdown(f"## 📋 {selected_date} 电价明细")
        
        sel_dt = pd.to_datetime(selected_date)
        sel_row = price_df[price_df['日期'] == sel_dt]
        
        if not sel_row.empty:
            # 24小时数据表
            data = {'小时': [f'{i}:00' for i in range(24)], '电价(元/MWh)': [sel_row.iloc[0][h] for h in hour_cols]}
            df_display = pd.DataFrame(data)
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                fig = go.Figure()
                fig.add_trace(go.Bar(x=list(range(24)), y=df_display['电价(元/MWh)'], marker_color='#007bff'))
                fig.update_layout(title=f'{selected_date} 逐时电价', xaxis_title='小时', yaxis_title='元/MWh', height=350)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.dataframe(df_display, use_container_width=True, hide_index=True, height=350)
            
            # 统计汇总
            vals = df_display['电价(元/MWh)'].tolist()
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("均价", f"{np.mean(vals):.1f}")
            col2.metric("峰值", f"{max(vals):.1f}")
            col3.metric("谷值", f"{min(vals):.1f}")
            col4.metric("峰谷差", f"{max(vals)-min(vals):.1f}")
            col5.metric("标准差", f"{np.std(vals):.1f}")
        else:
            st.warning(f"{selected_date} 无数据")
    
    elif data_type == "月度统计":
        st.markdown(f"## 📅 {selected_month} 月度统计")
        
        month_df = price_df[price_df['日期'].dt.to_period('M') == selected_month].copy()
        
        if not month_df.empty:
            month_df['均价'] = month_df[hour_cols].mean(axis=1)
            month_df['峰值'] = month_df[hour_cols].max(axis=1)
            month_df['谷值'] = month_df[hour_cols].min(axis=1)
            month_df['峰谷差'] = month_df['峰值'] - month_df['谷值']
            
            # 月度趋势图
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=month_df['日期'], y=month_df['均价'], name='均价', line=dict(color='#007bff', width=2)))
            fig.add_trace(go.Scatter(x=month_df['日期'], y=month_df['峰值'], name='峰值', line=dict(color='#dc3545', width=1, dash='dot')))
            fig.add_trace(go.Scatter(x=month_df['日期'], y=month_df['谷值'], name='谷值', line=dict(color='#28a745', width=1, dash='dot')))
            fig.update_layout(title=f'{selected_month} 电价趋势', xaxis_title='日期', yaxis_title='元/MWh', height=400)
            st.plotly_chart(fig, use_container_width=True)
            
            # 月度统计
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("月均价", f"{month_df['均价'].mean():.1f}")
            col2.metric("最高价", f"{month_df['峰值'].max():.1f}")
            col3.metric("最低价", f"{month_df['谷值'].min():.1f}")
            col4.metric("平均峰谷差", f"{month_df['峰谷差'].mean():.1f}")
            
            # 每日明细表
            st.markdown("### 每日明细")
            display_df = month_df[['日期', '均价', '峰值', '谷值', '峰谷差']].copy()
            display_df['日期'] = display_df['日期'].dt.strftime('%m/%d')
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.warning(f"{selected_month} 无数据")
    
    elif data_type == "年度对比":
        st.markdown(f"## 📊 年度电价对比")
        
        fig = go.Figure()
        
        for year in selected_years:
            year_df = price_df[price_df['日期'].dt.year == year].copy()
            year_df['月'] = year_df['日期'].dt.month
            monthly = year_df.groupby('月')[hour_cols].mean()
            monthly['均价'] = monthly.mean(axis=1)
            
            fig.add_trace(go.Scatter(x=monthly.index, y=monthly['均价'], name=f'{year}年', mode='lines+markers'))
        
        fig.update_layout(title='月度均价对比', xaxis_title='月份', yaxis_title='元/MWh', height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    elif data_type == "热力图":
        st.markdown("## 🔥 电价热力图")
        
        # 过滤日期范围
        if len(date_range) == 2:
            start_date, end_date = date_range
            heat_df = price_df[(price_df['日期'].dt.date >= start_date) & (price_df['日期'].dt.date <= end_date)].copy()
        else:
            heat_df = price_df.tail(30).copy()
        
        heat_df['标签'] = heat_df['日期'].dt.strftime('%m/%d')
        
        # 构建矩阵
        z = heat_df[hour_cols].values.T.tolist()
        x = heat_df['标签'].tolist()
        y = [f'{i}时' for i in range(24)]
        
        colorscale = [[0, '#0D7A3F'], [0.2, '#4CAF50'], [0.4, '#8BC34A'], [0.6, '#FFC107'], [0.8, '#FF5722'], [1, '#dc3545']]
        
        fig = go.Figure(data=go.Heatmap(z=z, x=x, y=y, colorscale=colorscale,
                                        colorbar=dict(title='元/MWh', tickfont=dict(size=8))))
        fig.update_layout(title='电价热力图', height=500)
        st.plotly_chart(fig, use_container_width=True)

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
