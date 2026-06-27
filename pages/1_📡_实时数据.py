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

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(page_title="实时数据", page_icon="📡", layout="wide")

_CN_TZ = timezone(timedelta(hours=8))
def _now(): return datetime.now(_CN_TZ)

# 标题栏和导航栏
from header_nav import render_header_nav
render_header_nav("实时数据")

st.markdown("## 📡 实时数据")
st.markdown("---")

# 数据路径
PRICE_PATH = os.path.expanduser("~/projects/能源电力资料/日前训练数据/日前节点电价.xlsx")
RT_PRICE_DIR = os.path.expanduser("~/projects/能源电力资料/实时训练数据/日前和实时电价占比/2026")
DISCLOSURE_DIR = os.path.expanduser("~/projects/能源电力资料/实时训练数据/信息披露实际")

# 读取电价数据
@st.cache_data(ttl=600)
def load_price_data():
    if os.path.exists(PRICE_PATH):
        df = pd.read_excel(PRICE_PATH)
        df['日期'] = pd.to_datetime(df['日期'])
        return df
    return pd.DataFrame()

price_df = load_price_data()

# 侧边栏控制
with st.sidebar:
    st.markdown("## ⚙️ 查询选项")
    
    # 数据类型
    data_type = st.selectbox("数据类型", ["实时电价", "实时负荷", "电价对比", "气象数据", "地市温度"])
    
    # 日期选择
    if not price_df.empty:
        date_options = sorted(price_df['日期'].dt.strftime('%Y-%m-%d').unique(), reverse=True)
        selected_date = st.selectbox("选择日期", date_options, index=0)
    else:
        selected_date = _now().strftime('%Y-%m-%d')

hour_cols = [f"{i}时" for i in range(24)]

if data_type == "实时电价":
    st.markdown(f"## 📡 {selected_date} 实时电价")
    
    # 读取实时电价数据
    rt_month = selected_date[:7].replace("-", "/")
    rt_path = os.path.join(RT_PRICE_DIR, rt_month.split("/")[1])
    rt_file = os.path.join(rt_path, f"实时节点电价查询({selected_date}).xlsx")
    
    if os.path.exists(rt_file):
        try:
            rt_df = pd.read_excel(rt_file)
            rt_time_cols = [c for c in rt_df.columns if ':' in str(c)]
            
            if len(rt_time_cols) >= 96:
                # 对所有节点求平均
                rt_avg = rt_df[rt_time_cols].mean()
                
                # 96点转24点
                rt_hourly = []
                for h in range(24):
                    quarter_cols = [f'{h:02d}:{m:02d}' for m in [0, 15, 30, 45]]
                    vals = [rt_avg[c] for c in quarter_cols if c in rt_avg.index]
                    rt_hourly.append(float(np.mean(vals)) if vals else np.nan)
                
                # 绘制图表
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=list(range(24)), y=rt_hourly,
                    mode='lines+markers',
                    name='实时电价',
                    line=dict(color='#007bff', width=2),
                    marker=dict(size=6),
                    fill='tozeroy',
                    fillcolor='rgba(0,123,255,0.1)'
                ))
                
                # 峰谷标注
                pk_idx = rt_hourly.index(max(rt_hourly))
                vl_idx = rt_hourly.index(min(rt_hourly))
                fig.add_annotation(x=pk_idx, y=max(rt_hourly), text=f'{max(rt_hourly):.0f}', showarrow=True, arrowhead=2, font=dict(color='red'))
                fig.add_annotation(x=vl_idx, y=min(rt_hourly), text=f'{min(rt_hourly):.0f}', showarrow=True, arrowhead=2, font=dict(color='green'))
                
                fig.update_layout(
                    title=f'{selected_date} 实时电价曲线',
                    xaxis_title='小时', yaxis_title='元/MWh',
                    height=400
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # 统计指标
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("均价", f"{np.nanmean(rt_hourly):.0f} 元/MWh")
                col2.metric("峰值", f"{max(rt_hourly):.0f} 元/MWh", f"{pk_idx}时")
                col3.metric("谷值", f"{min(rt_hourly):.0f} 元/MWh", f"{vl_idx}时")
                col4.metric("峰谷差", f"{max(rt_hourly)-min(rt_hourly):.0f} 元/MWh")
            else:
                st.warning("实时电价数据格式不正确")
        except Exception as e:
            st.error(f"读取实时电价数据失败: {e}")
    else:
        st.warning(f"{selected_date} 无实时电价数据")

elif data_type == "实时负荷":
    st.markdown(f"## ⚡ {selected_date} 实时负荷")
    
    # 读取实际负荷数据
    actual_file = os.path.join(DISCLOSURE_DIR, f"信息披露查询实际信息({selected_date}).xlsx")
    
    if os.path.exists(actual_file):
        try:
            actual_df = pd.read_excel(actual_file, sheet_name=0, header=None, skiprows=1)
            
            if len(actual_df) > 0:
                # 提取统调负荷
                load_vals = []
                for col_idx in range(2, min(98, len(actual_df.columns))):
                    try:
                        load_vals.append(float(actual_df.iloc[0, col_idx]))
                    except:
                        pass
                
                if len(load_vals) >= 96:
                    # 96点转24点
                    load_hourly = [np.mean(load_vals[h*4:(h+1)*4]) for h in range(24)]
                    
                    # 绘制图表
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=list(range(24)), y=load_hourly,
                        mode='lines+markers',
                        name='统调负荷',
                        line=dict(color='#ff6b6b', width=2),
                        marker=dict(size=6),
                        fill='tozeroy',
                        fillcolor='rgba(255,107,107,0.1)'
                    ))
                    
                    # 峰谷标注
                    pk_idx = load_hourly.index(max(load_hourly))
                    vl_idx = load_hourly.index(min(load_hourly))
                    fig.add_annotation(x=pk_idx, y=max(load_hourly), text=f'{max(load_hourly):.0f}', showarrow=True, arrowhead=2, font=dict(color='red'))
                    fig.add_annotation(x=vl_idx, y=min(load_hourly), text=f'{min(load_hourly):.0f}', showarrow=True, arrowhead=2, font=dict(color='green'))
                    
                    fig.update_layout(
                        title=f'{selected_date} 实时统调负荷曲线',
                        xaxis_title='小时', yaxis_title='MW',
                        height=400
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # 统计指标
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("日均负荷", f"{np.nanmean(load_hourly):.0f} MW")
                    col2.metric("峰值", f"{max(load_hourly):.0f} MW", f"{pk_idx}时")
                    col3.metric("谷值", f"{min(load_hourly):.0f} MW", f"{vl_idx}时")
                    col4.metric("峰谷差", f"{max(load_hourly)-min(load_hourly):.0f} MW")
                else:
                    st.warning("负荷数据格式不正确")
            else:
                st.warning("无负荷数据")
        except Exception as e:
            st.error(f"读取负荷数据失败: {e}")
    else:
        st.warning(f"{selected_date} 无实际负荷数据")

elif data_type == "电价对比":
    st.markdown(f"## 📊 {selected_date} 电价对比")
    
    # 读取日前电价
    if not price_df.empty:
        sel_dt = pd.to_datetime(selected_date)
        price_row = price_df[price_df['日期'] == sel_dt]
        
        if not price_row.empty:
            da_hourly = [price_row.iloc[0][h] for h in hour_cols]
            
            # 读取实时电价
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
                except:
                    pass
            
            # 绘制对比图
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=list(range(24)), y=da_hourly,
                mode='lines+markers',
                name='日前电价',
                line=dict(color='#007bff', width=2),
                marker=dict(size=6)
            ))
            
            if rt_hourly:
                fig.add_trace(go.Scatter(
                    x=list(range(24)), y=rt_hourly,
                    mode='lines+markers',
                    name='实时电价',
                    line=dict(color='#ff6b6b', width=2),
                    marker=dict(size=6)
                ))
            
            fig.update_layout(
                title=f'{selected_date} 日前vs实时电价对比',
                xaxis_title='小时', yaxis_title='元/MWh',
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # 统计指标
            col1, col2 = st.columns(2)
            col1.metric("日前均价", f"{np.nanmean(da_hourly):.0f} 元/MWh")
            if rt_hourly:
                col2.metric("实时均价", f"{np.nanmean(rt_hourly):.0f} 元/MWh")
                diff = np.nanmean(rt_hourly) - np.nanmean(da_hourly)
                diff_pct = diff / np.nanmean(da_hourly) * 100
                st.markdown(f'<span style="font-size:0.6rem;color:#666">价差 <b>{diff:+.0f}</b> 元/MWh ({diff_pct:+.1f}%)</span>', unsafe_allow_html=True)
        else:
            st.warning(f"{selected_date} 无日前电价数据")
    else:
        st.warning("无电价数据")

elif data_type == "气象数据":
    st.markdown("## 🌤️ 气象数据")
    
    # 读取气象数据
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from data_sources.weather_api import fetch_weather_single, GUANGDONG_CITIES
    
    # 获取广州近24小时数据
    weather_df = fetch_weather_single("广州", forecast_days=2)
    
    if not weather_df.empty:
        # 取最近24小时数据
        now = _now()
        # 确保时间列是datetime类型且无时区
        weather_df["时间"] = pd.to_datetime(weather_df["时间"]).dt.tz_localize(None)
        now_naive = now.replace(tzinfo=None)
        last_24h = weather_df[weather_df["时间"] >= now_naive - timedelta(hours=24)].copy()
        
        if not last_24h.empty:
            # 构建表格数据
            table_data = []
            for _, row in last_24h.iterrows():
                table_data.append({
                    "名称": "广州",
                    "类型": "温度",
                    "数值": f'{row.get("温度(℃)", 0):.1f}',
                    "单位": "℃",
                    "获取时间": row["时间"].strftime("%Y-%m-%d %H:%M")
                })
                if "湿度(%)" in row:
                    table_data.append({
                        "名称": "广州",
                        "类型": "湿度",
                        "数值": f'{row.get("湿度(%)", 0):.0f}',
                        "单位": "%",
                        "获取时间": row["时间"].strftime("%Y-%m-%d %H:%M")
                    })
                if "风速(m/s)" in row:
                    table_data.append({
                        "名称": "广州",
                        "类型": "风速",
                        "数值": f'{row.get("风速(m/s)", 0):.1f}',
                        "单位": "m/s",
                        "获取时间": row["时间"].strftime("%Y-%m-%d %H:%M")
                    })
            
            df = pd.DataFrame(table_data)
            st.dataframe(df, use_container_width=True, hide_index=True, height=400)
            
            # 统计信息
            avg_temp = last_24h["温度(℃)"].mean()
            max_temp = last_24h["温度(℃)"].max()
            min_temp = last_24h["温度(℃)"].min()
            st.markdown(f'<span style="font-size:0.6rem;color:#666">近24h均温 <b>{avg_temp:.1f}℃</b> | 最高 <b>{max_temp:.1f}℃</b> | 最低 <b>{min_temp:.1f}℃</b></span>', unsafe_allow_html=True)
        else:
            st.warning("近24小时无数据")
    else:
        st.warning("气象数据获取失败")

elif data_type == "地市温度":
    st.markdown("## 🌡️ 地市实时温度")
    
    # 读取地市温度数据
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from data_sources.weather_api import fetch_weather_single, GUANGDONG_CITIES
    
    # 获取各城市近24小时数据
    now = _now()
    now_naive = now.replace(tzinfo=None)
    table_data = []
    
    for city_name in GUANGDONG_CITIES.keys():
        try:
            city_df = fetch_weather_single(city_name, forecast_days=2)
            if not city_df.empty:
                # 确保时间列是datetime类型且无时区
                city_df["时间"] = pd.to_datetime(city_df["时间"]).dt.tz_localize(None)
                last_24h = city_df[city_df["时间"] >= now_naive - timedelta(hours=24)]
                for _, row in last_24h.iterrows():
                    table_data.append({
                        "地名": city_name,
                        "类型": "实时温度",
                        "数值": f'{row.get("温度(℃)", 0):.1f}',
                        "单位": "℃",
                        "获取时间": row["时间"].strftime("%Y-%m-%d %H:%M")
                    })
        except:
            pass
    
    if table_data:
        df = pd.DataFrame(table_data)
        st.dataframe(df, use_container_width=True, hide_index=True, height=600)
        
        # 统计信息
        temps = [float(d["数值"]) for d in table_data]
        st.markdown(f'<span style="font-size:0.6rem;color:#666">近24h均温 <b>{np.mean(temps):.1f}℃</b> | 最高 <b>{max(temps):.1f}℃</b> | 最低 <b>{min(temps):.1f}℃</b></span>', unsafe_allow_html=True)
    else:
        st.warning("地市温度数据获取失败")

# 页脚
st.markdown("---")
st.markdown("📡 数据来源: 广东电力交易中心 | Powered by Streamlit")
