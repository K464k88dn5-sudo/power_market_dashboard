"""
实时数据页面 - 电力市场多源数据监控大屏
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(page_title="实时数据", page_icon="📡", layout="wide")
from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=5 * 60 * 1000, key="rt_auto_refresh")

_CN_TZ = timezone(timedelta(hours=8))
def _now(): return datetime.now(_CN_TZ)

from header_nav import render_header_nav
render_header_nav("实时数据")

from data_sources.weather_api import GUANGDONG_CITIES
from data.data_manager import get_weather_data, get_all_cities_weather

hour_cols = [f"{i}时" for i in range(24)]
selected_date = _now().strftime('%Y-%m-%d')
now_naive = _now().replace(tzinfo=None)

# 三列布局
col1, col2, col3 = st.columns(3)

# ============================================================
# 第一列：气象数据
# ============================================================
with col1:
    with st.container(border=True):
        st.markdown('<div class="mod-head mod-head-w">🌤️ 气象数据<span class="mod-sub">广州 · 近24h</span></div>', unsafe_allow_html=True)
        weather_df = get_weather_data("广州", forecast_days=2)
        if not weather_df.empty:
            weather_df["时间"] = pd.to_datetime(weather_df["时间"]).dt.tz_localize(None)
            last_24h = weather_df[weather_df["时间"] >= now_naive - timedelta(days=7)].copy()
            if not last_24h.empty:
                table_data = []
                for _, row in last_24h.iterrows():
                    table_data.append({"时间": row["时间"].strftime("%m-%d %H:%M"), "温度℃": f'{row.get("温度(℃)", 0):.1f}', "湿度%": f'{row.get("湿度(%)", 0):.0f}', "风速m/s": f'{row.get("风速(m/s)", 0):.1f}'})
                df = pd.DataFrame(table_data).iloc[::-1].reset_index(drop=True)
                st.dataframe(df, use_container_width=True, hide_index=True, height=500)
                avg_t = last_24h["温度(℃)"].mean()
                st.markdown(f'<span style="font-size:0.6rem;color:#666">均温 <b>{avg_t:.1f}℃</b> | 最高 <b>{last_24h["温度(℃)"].max():.1f}℃</b> | 最低 <b>{last_24h["温度(℃)"].min():.1f}℃</span>', unsafe_allow_html=True)
            else:
                st.warning("近24小时无数据")
        else:
            st.warning("气象数据获取失败")

# ============================================================
# 第二列：地市温度
# ============================================================
with col2:
    with st.container(border=True):
        st.markdown('<div class="mod-head mod-head-g">🌡️ 地市温度<span class="mod-sub">近7天</span></div>', unsafe_allow_html=True)
        # 使用并行获取所有城市数据
        all_cities_df = get_all_cities_weather(forecast_days=2)
        city_data = []
        if not all_cities_df.empty:
            all_cities_df["时间"] = pd.to_datetime(all_cities_df["时间"]).dt.tz_localize(None)
            for city_name in GUANGDONG_CITIES.keys():
                city_df = all_cities_df[all_cities_df["城市"] == city_name]
                if not city_df.empty:
                    last_7d = city_df[city_df["时间"] >= now_naive - timedelta(days=7)]
                    for _, row in last_7d.iterrows():
                        city_data.append({"地市": city_name, "时间": row["时间"].strftime("%m-%d %H:%M"), "温度℃": f'{row.get("温度(℃)", 0):.1f}'})
        if city_data:
            df = pd.DataFrame(city_data).iloc[::-1].reset_index(drop=True)
            st.dataframe(df, use_container_width=True, hide_index=True, height=500)
            temps = [float(d["温度℃"]) for d in city_data]
            st.markdown(f'<span style="font-size:0.6rem;color:#666">均温 <b>{np.mean(temps):.1f}℃</b> | 最高 <b>{max(temps):.1f}℃</b> | 最低 <b>{min(temps):.1f}℃</span>', unsafe_allow_html=True)
        else:
            st.warning("地市温度数据获取失败")

# ============================================================
# 第三列：数据类型选择器 + 图表
# ============================================================
with col3:
    with st.container(border=True):
        data_type = st.selectbox("数据类型", ["实时电价", "实时负荷", "电价对比"], key="rt_data_type", label_visibility="visible")

        if data_type == "实时电价":
            st.markdown(f'<div class="mod-head mod-head-p">📡 实时电价<span class="mod-sub">{selected_date}</span></div>', unsafe_allow_html=True)
            RT_PRICE_DIR = os.path.expanduser("~/projects/能源电力资料/实时训练数据/日前和实时电价占比/2026")
            rt_month = selected_date[:7].replace("-", "/")
            rt_path = os.path.join(RT_PRICE_DIR, rt_month.split("/")[1])
            rt_file = os.path.join(rt_path, f"实时节点电价查询({selected_date}).xlsx")
            if os.path.exists(rt_file):
                try:
                    rt_df = pd.read_excel(rt_file)
                    rt_time_cols = [c for c in rt_df.columns if ':' in str(c)]
                    if len(rt_time_cols) >= 96:
                        rt_avg = rt_df[rt_time_cols].mean()
                        rt_hourly = []
                        for h in range(24):
                            quarter_cols = [f'{h:02d}:{m:02d}' for m in [0, 15, 30, 45]]
                            vals = [rt_avg[c] for c in quarter_cols if c in rt_avg.index]
                            rt_hourly.append(float(np.mean(vals)) if vals else np.nan)
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(x=list(range(24)), y=rt_hourly, mode='lines+markers', name='实时电价', line=dict(color='#007bff', width=2), marker=dict(size=6), fill='tozeroy', fillcolor='rgba(0,123,255,0.1)'))
                        pk_idx = rt_hourly.index(max(rt_hourly))
                        vl_idx = rt_hourly.index(min(rt_hourly))
                        fig.add_annotation(x=pk_idx, y=max(rt_hourly), text=f'{max(rt_hourly):.0f}', showarrow=True, arrowhead=2, font=dict(color='red'))
                        fig.add_annotation(x=vl_idx, y=min(rt_hourly), text=f'{min(rt_hourly):.0f}', showarrow=True, arrowhead=2, font=dict(color='green'))
                        fig.update_layout(title='实时电价曲线', xaxis_title='小时', yaxis_title='元/MWh', height=300, margin=dict(l=30, r=10, t=30, b=30))
                        st.plotly_chart(fig, use_container_width=True)
                        c1, c2 = st.columns(2)
                        c1.metric("均价", f"{np.nanmean(rt_hourly):.0f}")
                        c2.metric("峰谷差", f"{max(rt_hourly)-min(rt_hourly):.0f}")
                except:
                    st.warning("实时电价数据读取失败")
            else:
                st.warning(f"{selected_date} 无实时电价数据")

        elif data_type == "实时负荷":
            st.markdown(f'<div class="mod-head mod-head-r">⚡ 实时负荷<span class="mod-sub">{selected_date}</span></div>', unsafe_allow_html=True)
            DISCLOSURE_DIR = os.path.expanduser("~/projects/能源电力资料/实时训练数据/信息披露实际")
            actual_file = os.path.join(DISCLOSURE_DIR, f"信息披露查询实际信息({selected_date}).xlsx")
            if os.path.exists(actual_file):
                try:
                    actual_df = pd.read_excel(actual_file, sheet_name=0, header=None, skiprows=1)
                    if len(actual_df) > 0:
                        load_vals = []
                        for col_idx in range(2, min(98, len(actual_df.columns))):
                            try: load_vals.append(float(actual_df.iloc[0, col_idx]))
                            except: pass
                        if len(load_vals) >= 96:
                            load_hourly = [np.mean(load_vals[h*4:(h+1)*4]) for h in range(24)]
                            fig = go.Figure()
                            fig.add_trace(go.Scatter(x=list(range(24)), y=load_hourly, mode='lines+markers', name='统调负荷', line=dict(color='#ff6b6b', width=2), marker=dict(size=6), fill='tozeroy', fillcolor='rgba(255,107,107,0.1)'))
                            pk_idx = load_hourly.index(max(load_hourly))
                            vl_idx = load_hourly.index(min(load_hourly))
                            fig.add_annotation(x=pk_idx, y=max(load_hourly), text=f'{max(load_hourly):.0f}', showarrow=True, arrowhead=2, font=dict(color='red'))
                            fig.add_annotation(x=vl_idx, y=min(load_hourly), text=f'{min(load_hourly):.0f}', showarrow=True, arrowhead=2, font=dict(color='green'))
                            fig.update_layout(title='实时统调负荷曲线', xaxis_title='小时', yaxis_title='MW', height=300, margin=dict(l=30, r=10, t=30, b=30))
                            st.plotly_chart(fig, use_container_width=True)
                            c1, c2 = st.columns(2)
                            c1.metric("日均负荷", f"{np.nanmean(load_hourly):.0f}")
                            c2.metric("峰谷差", f"{max(load_hourly)-min(load_hourly):.0f}")
                except:
                    st.warning("负荷数据读取失败")
            else:
                st.warning(f"{selected_date} 无实际负荷数据")

        elif data_type == "电价对比":
            st.markdown(f'<div class="mod-head mod-head-b">📊 电价对比<span class="mod-sub">日前 vs 实时</span></div>', unsafe_allow_html=True)
            PRICE_PATH = os.path.expanduser("~/projects/能源电力资料/日前训练数据/日前节点电价.xlsx")
            RT_PRICE_DIR = os.path.expanduser("~/projects/能源电力资料/实时训练数据/日前和实时电价占比/2026")
            if os.path.exists(PRICE_PATH):
                price_df = pd.read_excel(PRICE_PATH)
                price_df['日期'] = pd.to_datetime(price_df['日期'])
                sel_dt = pd.to_datetime(selected_date)
                price_row = price_df[price_df['日期'] == sel_dt]
                if not price_row.empty:
                    da_hourly = [price_row.iloc[0][h] for h in hour_cols]
                    rt_month = selected_date[:7].replace("-", "/")
                    rt_path = os.path.join(RT_PRICE_DIR, rt_month.split("/")[1])
                    rt_file = os.path.join(rt_path, f"实时节点电价查询({selected_date}).xlsx")
                    rt_hourly = None
                    if os.path.exists(rt_file):
                        try:
                            rt_df = pd.read_excel(rt_file)
                            rt_time_cols = [c for c in rt_df.columns if ':' in str(c)]
                            if len(rt_time_cols) >= 96:
                                rt_avg = rt_df[rt_time_cols].mean()
                                rt_hourly = []
                                for h in range(24):
                                    quarter_cols = [f'{h:02d}:{m:02d}' for m in [0, 15, 30, 45]]
                                    vals = [rt_avg[c] for c in quarter_cols if c in rt_avg.index]
                                    rt_hourly.append(float(np.mean(vals)) if vals else np.nan)
                        except: pass
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=list(range(24)), y=da_hourly, mode='lines+markers', name='日前电价', line=dict(color='#007bff', width=2), marker=dict(size=6)))
                    if rt_hourly:
                        fig.add_trace(go.Scatter(x=list(range(24)), y=rt_hourly, mode='lines+markers', name='实时电价', line=dict(color='#ff6b6b', width=2), marker=dict(size=6)))
                    fig.update_layout(title='日前vs实时电价对比', xaxis_title='小时', yaxis_title='元/MWh', height=300, margin=dict(l=30, r=10, t=30, b=30))
                    st.plotly_chart(fig, use_container_width=True)
                    c1, c2 = st.columns(2)
                    c1.metric("日前均价", f"{np.nanmean(da_hourly):.0f}")
                    if rt_hourly:
                        c2.metric("实时均价", f"{np.nanmean(rt_hourly):.0f}")

st.markdown('''<div style="margin-top:4px;padding:16px 0 8px;border-top:1px solid #e5e5e7;text-align:center;">
    <div style="display:flex;justify-content:center;align-items:center;gap:24px;flex-wrap:wrap;">
        <span style="font-size:0.6rem;color:#888;">📊 数据来源: Open-Meteo · CCTD · SHPGX · 广东电力交易中心</span>
        <span style="font-size:0.6rem;color:#888;">🔄 更新周期: 气象10分钟 · 燃料1小时 · 电价实时</span>
    </div>
    <div style="margin-top:8px;font-size:0.55rem;color:#aaa;">
        © 2024-2026 电力市场多源数据监控大屏 v2.0 | Powered by Streamlit
    </div>
</div>''', unsafe_allow_html=True)
