"""
历史数据页面 - 电力市场多源数据监控大屏
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(page_title="历史数据", page_icon="📈", layout="wide")

_CN_TZ = timezone(timedelta(hours=8))
def _now(): return datetime.now(_CN_TZ)

from header_nav import render_header_nav
render_header_nav("历史数据")

# 数据路径
PRICE_PATH = os.path.expanduser("~/projects/能源电力资料/日前训练数据/日前节点电价.xlsx")
FUEL_DATA_PATH = os.path.expanduser("~/Desktop/power_market_dashboard/data/fuel_cache.json")

hour_cols = [f"{i}时" for i in range(24)]

# 读取电价数据
@st.cache_data(ttl=600)
def load_price_data():
    if os.path.exists(PRICE_PATH):
        df = pd.read_excel(PRICE_PATH)
        df['日期'] = pd.to_datetime(df['日期'])
        return df
    return pd.DataFrame()

# 读取燃料数据
@st.cache_data(ttl=600)
def load_fuel_data():
    if os.path.exists(FUEL_DATA_PATH):
        import json
        with open(FUEL_DATA_PATH, 'r') as f:
            data = json.load(f)
        if 'data' in data and 'fuel_30d' in data['data']:
            df = pd.DataFrame(data['data']['fuel_30d'])
            if not df.empty and '日期' in df.columns:
                df['日期'] = pd.to_datetime(df['日期'])
            return df
    return pd.DataFrame()

price_df = load_price_data()
fuel_df = load_fuel_data()

# 顶部选择器
col_type, col_date, _ = st.columns([1, 1, 2])
with col_type:
    data_type = st.selectbox("数据类型", ["日前节点电价", "实时节点电价", "统调负荷预测", "省内B类电源预测", "统调负荷实际", "省内B类电源实际", "气象数据", "燃料价格"], key="hist_data_type")
with col_date:
    if data_type in ["日前节点电价", "实时节点电价"] and not price_df.empty:
        date_options = sorted(price_df['日期'].dt.strftime('%Y-%m-%d').unique(), reverse=True)
        selected_date = st.selectbox("选择日期", date_options, index=0, key="hist_date_sel")
    elif data_type in ["统调负荷预测", "省内B类电源预测"]:
        disclosure_dir = os.path.expanduser("~/projects/能源电力资料/日前训练数据/信息披露日前")
        import glob
        files = glob.glob(os.path.join(disclosure_dir, "信息披露查询预测信息(*.xlsx"))
        dates = sorted([f.split("(")[1].split(")")[0] for f in files], reverse=True)
        if dates:
            selected_date = st.selectbox("选择日期", dates, index=0, key="hist_date_sel")
        else:
            selected_date = _now().strftime('%Y-%m-%d')
    elif data_type in ["统调负荷实际", "省内B类电源实际"]:
        actual_dir = os.path.expanduser("~/projects/能源电力资料/实时训练数据/信息披露实际")
        import glob
        files = glob.glob(os.path.join(actual_dir, "信息披露查询实际信息(*.xlsx"))
        dates = sorted([f.split("(")[1].split(")")[0] for f in files], reverse=True)
        if dates:
            selected_date = st.selectbox("选择日期", dates, index=0, key="hist_date_sel")
        else:
            selected_date = _now().strftime('%Y-%m-%d')
    elif data_type == "气象数据":
        selected_date = st.selectbox("选择日期", [_now().strftime('%Y-%m-%d')], index=0, key="hist_date_sel")
    else:
        selected_date = _now().strftime('%Y-%m-%d')


# ============================================================
# 电价数据
# ============================================================
if data_type == "日前节点电价":
    with st.container(border=True):
        st.markdown('<div class="mod-head mod-head-p">📊 日前节点电价<span class="mod-sub">日前出清价</span></div>', unsafe_allow_html=True)
        
        if not price_df.empty:
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
                st.warning(f"{selected_date} 无电价数据")
        else:
            st.warning("无电价数据文件")

# ============================================================
# 实时节点电价
# ============================================================
elif data_type == "实时节点电价":
    with st.container(border=True):
        st.markdown('<div class="mod-head mod-head-b">📊 实时节点电价<span class="mod-sub">实时出清价</span></div>', unsafe_allow_html=True)
        
        RT_PRICE_DIR = os.path.expanduser("~/projects/能源电力资料/实时训练数据/日前和实时电价占比/2026")
        rt_month = str(int(selected_date[5:7]))  # 去掉前导零
        rt_path = os.path.join(RT_PRICE_DIR, rt_month)
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
                    
                    # 图表
                    data = {'小时': [f'{i}:00' for i in range(24)], '电价(元/MWh)': rt_hourly}
                    df_display = pd.DataFrame(data)
                    
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        fig = go.Figure()
                        fig.add_trace(go.Bar(x=list(range(24)), y=rt_hourly, marker_color='#ff6b6b'))
                        fig.update_layout(title=f'{selected_date} 实时逐时电价', xaxis_title='小时', yaxis_title='元/MWh', height=350)
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with col2:
                        st.dataframe(df_display, use_container_width=True, hide_index=True, height=350)
                    
                    # 统计汇总
                    vals = [v for v in rt_hourly if not np.isnan(v)]
                    col1, col2, col3, col4, col5 = st.columns(5)
                    col1.metric("均价", f"{np.mean(vals):.1f}")
                    col2.metric("峰值", f"{max(vals):.1f}")
                    col3.metric("谷值", f"{min(vals):.1f}")
                    col4.metric("峰谷差", f"{max(vals)-min(vals):.1f}")
                    col5.metric("标准差", f"{np.std(vals):.1f}")
            except:
                st.warning(f"{selected_date} 实时电价数据读取失败")
        else:
            st.warning(f"{selected_date} 无实时电价数据")

# ============================================================
# 统调负荷预测
# ============================================================
elif data_type == "统调负荷预测":
    with st.container(border=True):
        st.markdown('<div class="mod-head mod-head-r">📊 统调负荷预测<span class="mod-sub">日前预测</span></div>', unsafe_allow_html=True)
        
        disclosure_dir = os.path.expanduser("~/projects/能源电力资料/日前训练数据/信息披露日前")
        fp = os.path.join(disclosure_dir, f"信息披露查询预测信息({selected_date}).xlsx")
        
        if os.path.exists(fp):
            try:
                xl = pd.ExcelFile(fp)
                for s in xl.sheet_names:
                    if "负荷预测" in s:
                        df = pd.read_excel(fp, sheet_name=s, header=None, skiprows=1)
                        for _, row in df.iterrows():
                            ch = str(row.iloc[1]) if len(row) > 1 else ""
                            if "统调负荷" in ch:
                                vals = []
                                for col_idx in range(2, min(98, len(row))):
                                    try: vals.append(float(row.iloc[col_idx]))
                                    except: pass
                                if len(vals) >= 96:
                                    hourly = [np.mean(vals[h*4:(h+1)*4]) for h in range(24)]
                                    fig = go.Figure()
                                    fig.add_trace(go.Bar(x=list(range(24)), y=hourly, marker_color='#ff6b6b'))
                                    fig.update_layout(title=f'{selected_date} 统调负荷预测', xaxis_title='小时', yaxis_title='MW', height=350)
                                    st.plotly_chart(fig, use_container_width=True)
                                    c1, c2, c3, c4 = st.columns(4)
                                    c1.metric("日均", f"{np.nanmean(hourly):.0f}")
                                    c2.metric("峰值", f"{max(hourly):.0f}")
                                    c3.metric("谷值", f"{min(hourly):.0f}")
                                    c4.metric("峰谷差", f"{max(hourly)-min(hourly):.0f}")
                                break
                        break
            except:
                st.warning("数据读取失败")
        else:
            st.warning(f"{selected_date} 无数据")

# ============================================================
# 省内B类电源预测
# ============================================================
elif data_type == "省内B类电源预测":
    with st.container(border=True):
        st.markdown('<div class="mod-head mod-head-b">📊 省内B类电源预测<span class="mod-sub">日前预测</span></div>', unsafe_allow_html=True)
        
        disclosure_dir = os.path.expanduser("~/projects/能源电力资料/日前训练数据/信息披露日前")
        fp = os.path.join(disclosure_dir, f"信息披露查询预测信息({selected_date}).xlsx")
        
        if os.path.exists(fp):
            try:
                xl = pd.ExcelFile(fp)
                for s in xl.sheet_names:
                    if "负荷预测" in s:
                        df = pd.read_excel(fp, sheet_name=s, header=None, skiprows=1)
                        for _, row in df.iterrows():
                            ch = str(row.iloc[1]) if len(row) > 1 else ""
                            if "B类电源" in ch:
                                vals = []
                                for col_idx in range(2, min(98, len(row))):
                                    try: vals.append(float(row.iloc[col_idx]))
                                    except: pass
                                if len(vals) >= 96:
                                    hourly = [np.mean(vals[h*4:(h+1)*4]) for h in range(24)]
                                    fig = go.Figure()
                                    fig.add_trace(go.Bar(x=list(range(24)), y=hourly, marker_color='#54a0ff'))
                                    fig.update_layout(title=f'{selected_date} 省内B类电源预测', xaxis_title='小时', yaxis_title='MW', height=350)
                                    st.plotly_chart(fig, use_container_width=True)
                                    c1, c2, c3, c4 = st.columns(4)
                                    c1.metric("日均", f"{np.nanmean(hourly):.0f}")
                                    c2.metric("峰值", f"{max(hourly):.0f}")
                                    c3.metric("谷值", f"{min(hourly):.0f}")
                                    c4.metric("峰谷差", f"{max(hourly)-min(hourly):.0f}")
                                break
                        break
            except:
                st.warning("数据读取失败")
        else:
            st.warning(f"{selected_date} 无数据")

# ============================================================
# 统调负荷实际
# ============================================================
elif data_type == "统调负荷实际":
    with st.container(border=True):
        st.markdown('<div class="mod-head mod-head-r">📊 统调负荷实际<span class="mod-sub">实际出清</span></div>', unsafe_allow_html=True)
        
        actual_dir = os.path.expanduser("~/projects/能源电力资料/实时训练数据/信息披露实际")
        fp = os.path.join(actual_dir, f"信息披露查询实际信息({selected_date}).xlsx")
        
        if os.path.exists(fp):
            try:
                df = pd.read_excel(fp, sheet_name=0, header=None, skiprows=1)
                if len(df) > 0:
                    vals = []
                    for col_idx in range(2, min(98, len(df.columns))):
                        try: vals.append(float(df.iloc[0, col_idx]))
                        except: pass
                    if len(vals) >= 96:
                        hourly = [np.mean(vals[h*4:(h+1)*4]) for h in range(24)]
                        fig = go.Figure()
                        fig.add_trace(go.Bar(x=list(range(24)), y=hourly, marker_color='#ff6b6b'))
                        fig.update_layout(title=f'{selected_date} 统调负荷实际', xaxis_title='小时', yaxis_title='MW', height=350)
                        st.plotly_chart(fig, use_container_width=True)
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("日均", f"{np.nanmean(hourly):.0f}")
                        c2.metric("峰值", f"{max(hourly):.0f}")
                        c3.metric("谷值", f"{min(hourly):.0f}")
                        c4.metric("峰谷差", f"{max(hourly)-min(hourly):.0f}")
            except:
                st.warning("数据读取失败")
        else:
            st.warning(f"{selected_date} 无数据")

# ============================================================
# 省内B类电源实际
# ============================================================
elif data_type == "省内B类电源实际":
    with st.container(border=True):
        st.markdown('<div class="mod-head mod-head-b">📊 省内B类电源实际<span class="mod-sub">实际出清</span></div>', unsafe_allow_html=True)
        
        actual_dir = os.path.expanduser("~/projects/能源电力资料/实时训练数据/信息披露实际")
        fp = os.path.join(actual_dir, f"信息披露查询实际信息({selected_date}).xlsx")
        
        if os.path.exists(fp):
            try:
                xl = pd.ExcelFile(fp)
                for s in xl.sheet_names:
                    if "负荷" in s or "出力" in s:
                        df = pd.read_excel(fp, sheet_name=s, header=None, skiprows=1)
                        for _, row in df.iterrows():
                            ch = str(row.iloc[1]) if len(row) > 1 else ""
                            if "B类电源" in ch:
                                vals = []
                                for col_idx in range(2, min(98, len(row))):
                                    try: vals.append(float(row.iloc[col_idx]))
                                    except: pass
                                if len(vals) >= 96:
                                    hourly = [np.mean(vals[h*4:(h+1)*4]) for h in range(24)]
                                    fig = go.Figure()
                                    fig.add_trace(go.Bar(x=list(range(24)), y=hourly, marker_color='#54a0ff'))
                                    fig.update_layout(title=f'{selected_date} 省内B类电源实际', xaxis_title='小时', yaxis_title='MW', height=350)
                                    st.plotly_chart(fig, use_container_width=True)
                                    c1, c2, c3, c4 = st.columns(4)
                                    c1.metric("日均", f"{np.nanmean(hourly):.0f}")
                                    c2.metric("峰值", f"{max(hourly):.0f}")
                                    c3.metric("谷值", f"{min(hourly):.0f}")
                                    c4.metric("峰谷差", f"{max(hourly)-min(hourly):.0f}")
                                break
                        break
            except:
                st.warning("数据读取失败")
        else:
            st.warning(f"{selected_date} 无数据")

# ============================================================
# 气象数据
# ============================================================
elif data_type == "气象数据":
    with st.container(border=True):
        st.markdown('<div class="mod-head mod-head-w">🌤️ 气象数据<span class="mod-sub">广州</span></div>', unsafe_allow_html=True)
        
        from data.data_manager import get_weather_data
        
        weather_df = get_weather_data("广州", forecast_days=14)
        
        if not weather_df.empty:
            weather_df["时间"] = pd.to_datetime(weather_df["时间"]).dt.tz_localize(None)
            
            # 图表
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=weather_df["时间"], y=weather_df["温度(℃)"],
                mode='lines+markers', name='温度',
                line=dict(color='#ff6b6b', width=2), marker=dict(size=3),
                fill='tozeroy', fillcolor='rgba(255,107,107,0.1)'
            ))
            fig.update_layout(title='近14天温度趋势', xaxis_title='时间', yaxis_title='℃', height=300)
            st.plotly_chart(fig, use_container_width=True)
            
            # 数据表
            table_data = []
            for _, row in weather_df.iterrows():
                table_data.append({
                    "时间": row["时间"].strftime("%m-%d %H:%M"),
                    "温度℃": f'{row.get("温度(℃)", 0):.1f}',
                    "湿度%": f'{row.get("湿度(%)", 0):.0f}',
                    "风速m/s": f'{row.get("风速(m/s)", 0):.1f}'
                })
            df = pd.DataFrame(table_data).iloc[::-1].reset_index(drop=True)
            st.dataframe(df, use_container_width=True, hide_index=True, height=300)
        else:
            st.warning("气象数据获取失败")

# ============================================================
# 燃料价格
# ============================================================
elif data_type == "燃料价格":
    with st.container(border=True):
        st.markdown('<div class="mod-head mod-head-f">⛽ 燃料价格<span class="mod-sub">CCTD煤价 · SHPGX气价</span></div>', unsafe_allow_html=True)
        
        if not fuel_df.empty:
            # 煤价图表
            if '动力煤价格(元/吨)' in fuel_df.columns:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=fuel_df['日期'], y=fuel_df['动力煤价格(元/吨)'],
                    mode='lines+markers', name='煤价',
                    line=dict(color='#ff9f43', width=2), marker=dict(size=4),
                    fill='tozeroy', fillcolor='rgba(255,159,67,0.1)'
                ))
                fig.update_layout(title='动力煤价格趋势', xaxis_title='日期', yaxis_title='元/吨', height=250)
                st.plotly_chart(fig, use_container_width=True)
            
            # LNG图表
            if 'LNG出厂价(元/吨)' in fuel_df.columns:
                fig2 = go.Figure()
                fig2.add_trace(go.Scatter(
                    x=fuel_df['日期'], y=fuel_df['LNG出厂价(元/吨)'],
                    mode='lines+markers', name='LNG',
                    line=dict(color='#54a0ff', width=2), marker=dict(size=4),
                    fill='tozeroy', fillcolor='rgba(84,160,255,0.1)'
                ))
                fig2.update_layout(title='LNG出厂价趋势', xaxis_title='日期', yaxis_title='元/吨', height=250)
                st.plotly_chart(fig2, use_container_width=True)
            
            # 数据表
            display_cols = ['日期']
            if '动力煤价格(元/吨)' in fuel_df.columns:
                display_cols.append('动力煤价格(元/吨)')
            if 'LNG出厂价(元/吨)' in fuel_df.columns:
                display_cols.append('LNG出厂价(元/吨)')
            
            table_df = fuel_df[display_cols].copy()
            table_df['日期'] = table_df['日期'].dt.strftime('%m-%d')
            table_df = table_df.iloc[::-1].reset_index(drop=True)
            st.dataframe(table_df, use_container_width=True, hide_index=True, height=200)
        else:
            st.warning("燃料数据获取失败")

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
