"""
数据分析页面 - 电力市场多源数据监控大屏
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone
import os
from data.data_paths import get_price_path, get_disclosure_pred_dir, get_disclosure_actual_dir, get_realtime_price_dir
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(page_title="数据分析", page_icon="📊", layout="wide")

_CN_TZ = timezone(timedelta(hours=8))
def _now(): return datetime.now(_CN_TZ)

# 标题栏和导航栏
from header_nav import render_header_nav
render_header_nav("数据分析", margin_top="-12px")



# 定义neumorphic模板
import plotly.io as pio
NEUMORPHIC_TEMPLATE = go.layout.Template(
    layout=go.Layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
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
pio.templates.default = "neumorphic"

# 数据路径
PRICE_PATH = get_price_path()
DISCLOSURE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "disclosure")

# 读取电价数据
@st.cache_data(ttl=600)
def load_price_data():
    if os.path.exists(PRICE_PATH):
        df = pd.read_excel(PRICE_PATH)
        df['日期'] = pd.to_datetime(df['日期'])
        return df
    return pd.DataFrame()

price_df = load_price_data()
hour_cols = [f"{i}时" for i in range(24)]

# 两列布局
col_left, col_right = st.columns(2)

# ============================================================
# 左列：电价分析 + 负荷分析
# ============================================================
with col_left:
    with st.container(border=True):
        st.markdown('<div class="mod-head mod-head-p">📊 电价分析<span class="mod-sub">电价 · 环比对比</span></div>', unsafe_allow_html=True)
        
        # 日期选择
        if not price_df.empty:
            _date_options = sorted(price_df['日期'].dt.strftime('%Y-%m-%d').unique(), reverse=True)
            _sel_date = st.selectbox("选择日期", _date_options, index=0, key="stat_date_sel", label_visibility="collapsed")
            
            _sel_dt = pd.to_datetime(_sel_date)
            _prev_dt = _sel_dt - timedelta(days=1)
            _prev_date = _prev_dt.strftime("%Y-%m-%d")
            
            _fig = go.Figure()
            _has_data = False
            
            # 电价环比
            _sel_row = price_df[price_df['日期'] == _sel_dt]
            _prev_row = price_df[price_df['日期'] == _prev_dt]
            
            if not _sel_row.empty:
                _cur_vals = [_sel_row.iloc[0][h] for h in hour_cols]
                _fig.add_trace(go.Scattergl(
                    x=list(range(24)), y=_cur_vals,
                    name=f"{_sel_dt.month}/{_sel_dt.day}",
                    line=dict(color="#007bff", width=2),
                    mode="lines+markers",
                    marker=dict(size=4, color="#ffffff", line=dict(color="#007bff", width=1.5)),
                    fill="tozeroy", fillcolor="rgba(0,123,255,0.08)"
                ))
                _has_data = True
            
            if not _prev_row.empty:
                _prev_vals = [_prev_row.iloc[0][h] for h in hour_cols]
                _fig.add_trace(go.Scattergl(
                    x=list(range(24)), y=_prev_vals,
                    name=f"{_prev_dt.month}/{_prev_dt.day}",
                    line=dict(color="#adb5bd", width=1.5, dash="dot"),
                    mode="lines+markers", marker=dict(size=3)
                ))
            
            if _has_data:
                _fig.update_layout(
                    height=200, template="neumorphic", showlegend=True,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=7, color="#000000")),
                    hovermode="x unified",
                    margin=dict(l=30, r=10, t=5, b=50),
                    font=dict(size=7, color="#000000"),
                    xaxis=dict(dtick=3, tickvals=list(range(0, 24, 3)), ticktext=[f"{i}时" for i in range(0, 24, 3)]),
                    yaxis=dict(title="元/MWh", title_font=dict(size=7, color="#000000"))
                )
                # Y轴自适应
                _all_y = []
                for _tr in _fig.data:
                    if _tr.y is not None:
                        _all_y.extend([v for v in _tr.y if v is not None])
                if _all_y:
                    _y_min, _y_max = min(_all_y), max(_all_y)
                    _y_pad = max((_y_max - _y_min) * 0.1, 10)
                    _fig.update_yaxes(range=[_y_min - _y_pad, _y_max + _y_pad])
                st.plotly_chart(_fig, use_container_width=True)
                
                # 电价KPI
                if not _sel_row.empty and not _prev_row.empty:
                    _cur_mean = np.mean(_cur_vals)
                    _prev_mean = np.mean(_prev_vals)
                    _chg_pct = (_cur_mean - _prev_mean) / _prev_mean * 100 if _prev_mean != 0 else 0
                    _arrow = "↑" if _chg_pct > 0 else "↓" if _chg_pct < 0 else "→"
                    _color = "#dc3545" if _chg_pct > 0 else "#0D7A3F" if _chg_pct < 0 else "#666"
                    st.markdown(f'<span style="font-size:0.6rem;color:#666">日均价 <b>{_cur_mean:.0f}</b> 元/MWh | 环比 <span style="color:{_color};font-weight:bold">{_arrow} {_chg_pct:+.1f}%</span>（前日 {_prev_mean:.0f}）</span>', unsafe_allow_html=True)
                else:
                    st.markdown('<span style="font-size:0.6rem;color:#666">日均价 <b>--</b> 元/MWh | 环比 <b>--</b></span>', unsafe_allow_html=True)
        else:
            st.markdown('<span style="font-size:0.6rem;color:#666">日均价 <b>--</b> 元/MWh | 环比 <b>--</b></span>', unsafe_allow_html=True)
    
    # 负荷分析模块
    with st.container(border=True):
        st.markdown('<div class="mod-head mod-head-g">⚡ 负荷分析<span class="mod-sub">统调负荷 · B类电源 · 环比</span></div>', unsafe_allow_html=True)
        
        _disclosure_dir_ld = get_disclosure_pred_dir()
        
        # 日期选择（从披露数据获取可用日期）
        _ld_date_options = []
        if os.path.exists(_disclosure_dir_ld):
            import glob
            _ld_files = glob.glob(os.path.join(_disclosure_dir_ld, "信息披露查询预测信息(*.xlsx"))
            for _f in _ld_files:
                import re
                _m = re.search(r'(\d{4}-\d{2}-\d{2})', os.path.basename(_f))
                if _m:
                    _ld_date_options.append(_m.group(1))
        _ld_date_options = sorted(set(_ld_date_options), reverse=True)
        
        if _ld_date_options:
            _ld_sel_date = st.selectbox("选择日期", _ld_date_options, index=0, key="load_date_sel", label_visibility="collapsed")
            
            _ld_sel_dt = pd.to_datetime(_ld_sel_date)
            _ld_prev_dt = _ld_sel_dt - timedelta(days=1)
            _ld_prev_date = _ld_prev_dt.strftime("%Y-%m-%d")
            
            def _get_load_data(date_str):
                fp = os.path.join(_disclosure_dir_ld, f"信息披露查询预测信息({date_str}).xlsx")
                if not os.path.exists(fp):
                    return None, None
                try:
                    xl = pd.ExcelFile(fp)
                    load_data = {}
                    for s in xl.sheet_names:
                        if "负荷预测" in s:
                            df = pd.read_excel(fp, sheet_name=s, header=None, skiprows=1)
                            for _, row in df.iterrows():
                                ch = str(row.iloc[1]) if len(row) > 1 else ""
                                vals = []
                                for col_idx in range(2, min(98, len(row))):
                                    try:
                                        vals.append(float(row.iloc[col_idx]))
                                    except:
                                        pass
                                hourly = []
                                for h in range(24):
                                    chunk = vals[h*4:(h+1)*4]
                                    hourly.append(np.mean(chunk) if chunk else np.nan)
                                if "统调负荷" in ch:
                                    load_data["统调负荷"] = hourly
                                elif "B类电源" in ch:
                                    load_data["B类电源"] = hourly
                            break
                except:
                    return None, None
                return load_data.get("统调负荷"), load_data.get("B类电源")
            
            _ld_sel_load, _ld_sel_b = _get_load_data(_ld_sel_date)
            _ld_prev_load, _ld_prev_b = _get_load_data(_ld_prev_date)
            
            _ld_fig = go.Figure()
            _ld_has = False
            
            if _ld_sel_load:
                _ld_fig.add_trace(go.Scattergl(
                    x=list(range(24)), y=_ld_sel_load,
                    name=f"统调负荷 {_ld_sel_dt.month}/{_ld_sel_dt.day}",
                    line=dict(color="#ff6b6b", width=2), mode="lines+markers", marker=dict(size=4),
                    fill="tozeroy", fillcolor="rgba(255,107,107,0.08)"
                ))
                _ld_has = True
            if _ld_prev_load:
                _ld_fig.add_trace(go.Scattergl(
                    x=list(range(24)), y=_ld_prev_load,
                    name=f"统调负荷 {_ld_prev_dt.month}/{_ld_prev_dt.day}",
                    line=dict(color="#ff6b6b", width=1.5, dash="dot"), mode="lines+markers", marker=dict(size=3)
                ))
            if _ld_sel_b:
                _ld_fig.add_trace(go.Scattergl(
                    x=list(range(24)), y=_ld_sel_b,
                    name=f"B类电源 {_ld_sel_dt.month}/{_ld_sel_dt.day}",
                    line=dict(color="#54a0ff", width=2), mode="lines+markers", marker=dict(size=4)
                ))
            if _ld_prev_b:
                _ld_fig.add_trace(go.Scattergl(
                    x=list(range(24)), y=_ld_prev_b,
                    name=f"B类电源 {_ld_prev_dt.month}/{_ld_prev_dt.day}",
                    line=dict(color="#54a0ff", width=1.5, dash="dot"), mode="lines+markers", marker=dict(size=3)
                ))
            
            if _ld_has:
                _ld_fig.update_layout(
                    height=210, template="neumorphic", showlegend=True,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=7, color="#000000")),
                    hovermode="x unified",
                    margin=dict(l=30, r=10, t=5, b=25),
                    font=dict(size=7, color="#000000"),
                    xaxis=dict(dtick=3, tickvals=list(range(0, 24, 3)), ticktext=[f"{i}时" for i in range(0, 24, 3)]),
                    yaxis=dict(title="MW", title_font=dict(size=7, color="#000000"))
                )
                # Y轴自适应
                _ld_all_y = []
                for _tr in _ld_fig.data:
                    if _tr.y is not None:
                        _ld_all_y.extend([v for v in _tr.y if v is not None])
                if _ld_all_y:
                    _ld_y_min, _ld_y_max = min(_ld_all_y), max(_ld_all_y)
                    _ld_pad = max((_ld_y_max - _ld_y_min) * 0.1, 1000)
                    _ld_fig.update_yaxes(range=[_ld_y_min - _ld_pad, _ld_y_max + _ld_pad])
                st.plotly_chart(_ld_fig, use_container_width=True)
                
                # 负荷KPI
                if _ld_sel_load and _ld_prev_load:
                    _ld_cur_avg = np.nanmean(_ld_sel_load)
                    _ld_prev_avg = np.nanmean(_ld_prev_load)
                    _ld_chg = (_ld_cur_avg - _ld_prev_avg) / _ld_prev_avg * 100 if _ld_prev_avg != 0 else 0
                    _ld_arrow = "↑" if _ld_chg > 0 else "↓" if _ld_chg < 0 else "→"
                    _ld_color = "#dc3545" if _ld_chg > 0 else "#0D7A3F" if _ld_chg < 0 else "#666"
                    st.markdown(f'<span style="font-size:0.6rem;color:#666">日均负荷 <b>{_ld_cur_avg:.0f}</b> MW | 环比 <span style="color:{_ld_color};font-weight:bold">{_ld_arrow} {_ld_chg:+.1f}%</span>（前日 {_ld_prev_avg:.0f}）</span>', unsafe_allow_html=True)
                else:
                    st.markdown('<span style="font-size:0.6rem;color:#666">日均负荷 <b>--</b> MW | 环比 <b>--</b></span>', unsafe_allow_html=True)
            else:
                st.markdown('<span style="font-size:0.6rem;color:#666">日均负荷 <b>--</b> MW | 环比 <b>--</b></span>', unsafe_allow_html=True)
        else:
            st.markdown('<span style="font-size:0.6rem;color:#666">日均负荷 <b>--</b> MW | 环比 <b>--</b></span>', unsafe_allow_html=True)

    # 周度趋势
    with st.container(border=True):
        st.markdown('<div class="mod-head mod-head-w">📈 周度电价趋势<span class="mod-sub">近30天</span></div>', unsafe_allow_html=True)
        
        daily_avg = price_df.copy()
        # 检查列名是否存在
        valid_hour_cols = [h for h in hour_cols if h in daily_avg.columns]
        if valid_hour_cols:
            daily_avg['均价'] = daily_avg[valid_hour_cols].mean(axis=1)
            daily_avg['峰值'] = daily_avg[valid_hour_cols].max(axis=1)
            daily_avg['谷值'] = daily_avg[valid_hour_cols].min(axis=1)
        else:
            daily_avg['均价'] = 0
            daily_avg['峰值'] = 0
            daily_avg['谷值'] = 0
        
        # 取最近30天
        daily_avg = daily_avg.tail(30)
        daily_avg['日期标签'] = daily_avg['日期'].apply(lambda d: f"{d.month}月{d.day}日")
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=daily_avg['日期标签'], y=daily_avg['均价'], name='均价', line=dict(color='#007bff', width=2)))
        fig.add_trace(go.Scatter(x=daily_avg['日期标签'], y=daily_avg['峰值'], name='峰值', line=dict(color='#dc3545', width=1, dash='dot')))
        fig.add_trace(go.Scatter(x=daily_avg['日期标签'], y=daily_avg['谷值'], name='谷值', line=dict(color='#28a745', width=1, dash='dot')))
        
        fig.update_layout(
            height=200, template="neumorphic", showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=7, color="#000000")),
            hovermode="x unified",
            margin=dict(l=30, r=10, t=5, b=25),
            font=dict(size=7, color="#000000"),
            xaxis=dict(tickfont=dict(size=6, color="#000000")),
            yaxis=dict(title="元/MWh", title_font=dict(size=7, color="#000000"))
        )
        st.plotly_chart(fig, use_container_width=True)


# ============================================================
# 右列：电价对比 + 统调负荷对比 + 周度趋势 + 峰谷分析
# ============================================================
with col_right:
    if not price_df.empty:
        # 电价对比图表
        with st.container(border=True):
            st.markdown('<div class="mod-head mod-head-b">📊 电价对比<span class="mod-sub">日前 vs 实时</span></div>', unsafe_allow_html=True)
            
            # 选择日期
            _cmp_date_options = sorted(price_df['日期'].dt.strftime('%Y-%m-%d').unique(), reverse=True)
            _cmp_sel_date = st.selectbox("选择日期", _cmp_date_options, index=0, key="cmp_date_sel", label_visibility="collapsed")
            
            # 日前电价实际值
            _cmp_fig = go.Figure()
            _cmp_has = False
            
            _cmp_sel_dt = pd.to_datetime(_cmp_sel_date)
            _cmp_act = price_df[price_df['日期'] == _cmp_sel_dt]
            if not _cmp_act.empty:
                _cmp_da_vals = [_cmp_act.iloc[0][h] for h in hour_cols]
                _cmp_fig.add_trace(go.Scattergl(
                    x=list(range(24)), y=_cmp_da_vals,
                    name="日前电价",
                    line=dict(color="#007bff", width=2),
                    mode="lines+markers",
                    marker=dict(size=4, color="#ffffff", line=dict(color="#007bff", width=1.5)),
                    fill="tozeroy", fillcolor="rgba(0,123,255,0.06)"
                ))
                _cmp_has = True
            
            # 实时电价实际值
            _rt_actual_dir = get_realtime_price_dir()
            _rt_actual_path = os.path.join(_rt_actual_dir, str(int(_cmp_sel_date[5:7])))
            _rt_hourly = None
            if os.path.exists(_rt_actual_path):
                _rt_file = os.path.join(_rt_actual_path, f"实时节点电价查询({_cmp_sel_date}).xlsx")
                if os.path.exists(_rt_file):
                    try:
                        _rt_df = pd.read_excel(_rt_file)
                        _rt_time_cols = [c for c in _rt_df.columns if ':' in str(c)]
                        if len(_rt_time_cols) >= 96:
                            _rt_avg = _rt_df[_rt_time_cols].mean()
                            _rt_hourly = []
                            for h in range(24):
                                _quarter_cols = [f'{h:02d}:{m:02d}' for m in [0, 15, 30, 45]]
                                _vals = [_rt_avg[c] for c in _quarter_cols if c in _rt_avg.index]
                                _rt_hourly.append(float(np.mean(_vals)) if _vals else np.nan)
                            _cmp_fig.add_trace(go.Scattergl(
                                x=list(range(24)), y=_rt_hourly,
                                name="实时电价",
                                line=dict(color="#ff6b6b", width=2),
                                mode="lines+markers",
                                marker=dict(size=4, color="#ffffff", line=dict(color="#ff6b6b", width=1.5)),
                                fill="tozeroy", fillcolor="rgba(255,107,107,0.06)"
                            ))
                            _cmp_has = True
                    except:
                        pass
            
            if _cmp_has:
                _cmp_fig.update_layout(
                    height=200, template="neumorphic", showlegend=True,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=7, color="#000000")),
                    hovermode="x unified",
                    margin=dict(l=30, r=10, t=5, b=25),
                    font=dict(size=7, color="#000000"),
                    xaxis=dict(dtick=3, tickvals=list(range(0, 24, 3)), ticktext=[f"{i}时" for i in range(0, 24, 3)]),
                    yaxis=dict(title="元/MWh", title_font=dict(size=7, color="#000000"))
                )
                # Y轴自适应
                _cmp_all_y = []
                for _tr in _cmp_fig.data:
                    if _tr.y is not None:
                        _cmp_all_y.extend([v for v in _tr.y if v is not None])
                if _cmp_all_y:
                    _cmp_y_min, _cmp_y_max = min(_cmp_all_y), max(_cmp_all_y)
                    _cmp_pad = max((_cmp_y_max - _cmp_y_min) * 0.1, 10)
                    _cmp_fig.update_yaxes(range=[_cmp_y_min - _cmp_pad, _cmp_y_max + _cmp_pad])
                st.plotly_chart(_cmp_fig, use_container_width=True)
                
                # 电价对比KPI（始终显示）
                if '_cmp_da_vals' in dir() and '_rt_hourly' in dir() and _rt_hourly:
                    _cmp_da_avg = np.nanmean(_cmp_da_vals)
                    _cmp_rt_avg = np.nanmean(_rt_hourly)
                    _cmp_diff = _cmp_rt_avg - _cmp_da_avg
                    _cmp_diff_pct = _cmp_diff / _cmp_da_avg * 100 if _cmp_da_avg != 0 else 0
                    _cmp_arrow = "↑" if _cmp_diff > 0 else "↓" if _cmp_diff < 0 else "→"
                    _cmp_color = "#dc3545" if _cmp_diff > 0 else "#0D7A3F" if _cmp_diff < 0 else "#666"
                    st.markdown(f'<span style="font-size:0.6rem;color:#666">日前均价 <b>{_cmp_da_avg:.0f}</b> 元/MWh | 实时均价 <b>{_cmp_rt_avg:.0f}</b> 元/MWh | 价差 <span style="color:{_cmp_color};font-weight:bold">{_cmp_arrow} {_cmp_diff:+.0f} ({_cmp_diff_pct:+.1f}%)</span></span>', unsafe_allow_html=True)
                else:
                    st.markdown('<span style="font-size:0.6rem;color:#666">日前均价 <b>--</b> 元/MWh | 实时均价 <b>--</b> 元/MWh | 价差 <b>--</b></span>', unsafe_allow_html=True)
        
        # 统调负荷对比图表
        with st.container(border=True):
            st.markdown('<div class="mod-head mod-head-r">⚡ 统调负荷对比<span class="mod-sub">日前预测 vs 实际</span></div>', unsafe_allow_html=True)
            
            # 选择日期（从披露数据获取）
            _ld_cmp_disclosure_dir = get_disclosure_pred_dir()
            _ld_cmp_date_options = []
            if os.path.exists(_ld_cmp_disclosure_dir):
                import glob
                _ld_cmp_files = glob.glob(os.path.join(_ld_cmp_disclosure_dir, "信息披露查询预测信息(*.xlsx"))
                for _f in _ld_cmp_files:
                    import re
                    _m = re.search(r'(\d{4}-\d{2}-\d{2})', os.path.basename(_f))
                    if _m:
                        _ld_cmp_date_options.append(_m.group(1))
            _ld_cmp_date_options = sorted(set(_ld_cmp_date_options), reverse=True)
            
            if _ld_cmp_date_options:
                _ld_cmp_sel_date = st.selectbox("选择日期", _ld_cmp_date_options, index=0, key="ld_cmp_date_sel", label_visibility="collapsed")
            else:
                _ld_cmp_sel_date = None
            
            # 实际统调负荷
            _ld_cmp_fig = go.Figure()
            _ld_cmp_has = False
            
            _ld_actual_dir = get_disclosure_actual_dir()
            _ld_actual_file = os.path.join(_ld_actual_dir, f"信息披露查询实际信息({_ld_cmp_sel_date}).xlsx")
            _ld_actual_hourly = None
            
            if os.path.exists(_ld_actual_file):
                try:
                    _ld_actual_df = pd.read_excel(_ld_actual_file, sheet_name=0, header=None, skiprows=1)
                    if len(_ld_actual_df) > 0:
                        _ld_actual_vals = []
                        for col_idx in range(2, min(98, len(_ld_actual_df.columns))):
                            try:
                                _ld_actual_vals.append(float(_ld_actual_df.iloc[0, col_idx]))
                            except:
                                pass
                        if len(_ld_actual_vals) >= 96:
                            _ld_actual_hourly = [np.mean(_ld_actual_vals[h*4:(h+1)*4]) for h in range(24)]
                            _ld_cmp_fig.add_trace(go.Scattergl(
                                x=list(range(24)), y=_ld_actual_hourly,
                                name="实际统调负荷",
                                line=dict(color="#ff6b6b", width=2),
                                mode="lines+markers",
                                marker=dict(size=4, color="#ffffff", line=dict(color="#ff6b6b", width=1.5)),
                                fill="tozeroy", fillcolor="rgba(255,107,107,0.06)"
                            ))
                            _ld_cmp_has = True
                except:
                    pass
            
            # 日前预测统调负荷
            _ld_forecast_dir = get_disclosure_pred_dir()
            _ld_forecast_file = os.path.join(_ld_forecast_dir, f"信息披露查询预测信息({_ld_cmp_sel_date}).xlsx")
            _ld_forecast_hourly = None
            
            if os.path.exists(_ld_forecast_file):
                try:
                    _ld_fc_xl = pd.ExcelFile(_ld_forecast_file)
                    for s in _ld_fc_xl.sheet_names:
                        if "负荷预测" in s:
                            _ld_fc_df = pd.read_excel(_ld_forecast_file, sheet_name=s, header=None, skiprows=1)
                            if len(_ld_fc_df) > 0:
                                _ld_fc_vals = []
                                for col_idx in range(2, min(98, len(_ld_fc_df.columns))):
                                    try:
                                        _ld_fc_vals.append(float(_ld_fc_df.iloc[0, col_idx]))
                                    except:
                                        pass
                                if len(_ld_fc_vals) >= 96:
                                    _ld_forecast_hourly = [np.mean(_ld_fc_vals[h*4:(h+1)*4]) for h in range(24)]
                                    _ld_cmp_fig.add_trace(go.Scattergl(
                                        x=list(range(24)), y=_ld_forecast_hourly,
                                        name="日前预测负荷",
                                        line=dict(color="#007bff", width=2, dash="dot"),
                                        mode="lines+markers", marker=dict(size=3)
                                    ))
                                    _ld_cmp_has = True
                            break
                except:
                    pass
            
            if _ld_cmp_has:
                _ld_cmp_fig.update_layout(
                    height=210, template="neumorphic", showlegend=True,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=7, color="#000000")),
                    hovermode="x unified",
                    margin=dict(l=30, r=10, t=5, b=25),
                    font=dict(size=7, color="#000000"),
                    xaxis=dict(dtick=3, tickvals=list(range(0, 24, 3)), ticktext=[f"{i}时" for i in range(0, 24, 3)]),
                    yaxis=dict(title="MW", title_font=dict(size=7, color="#000000"))
                )
                # Y轴自适应
                _ld_cmp_all_y = []
                for _tr in _ld_cmp_fig.data:
                    if _tr.y is not None:
                        _ld_cmp_all_y.extend([v for v in _tr.y if v is not None])
                if _ld_cmp_all_y:
                    _ld_cmp_y_min, _ld_cmp_y_max = min(_ld_cmp_all_y), max(_ld_cmp_all_y)
                    _ld_cmp_pad = max((_ld_cmp_y_max - _ld_cmp_y_min) * 0.1, 1000)
                    _ld_cmp_fig.update_yaxes(range=[_ld_cmp_y_min - _ld_cmp_pad, _ld_cmp_y_max + _ld_cmp_pad])
                st.plotly_chart(_ld_cmp_fig, use_container_width=True)
                
                # 负荷对比KPI（始终显示）
                if _ld_actual_hourly and _ld_forecast_hourly:
                    _ld_actual_avg = np.nanmean(_ld_actual_hourly)
                    _ld_forecast_avg = np.nanmean(_ld_forecast_hourly)
                    _ld_diff = _ld_actual_avg - _ld_forecast_avg
                    _ld_diff_pct = _ld_diff / _ld_forecast_avg * 100 if _ld_forecast_avg != 0 else 0
                    _ld_arrow = "↑" if _ld_diff > 0 else "↓" if _ld_diff < 0 else "→"
                    _ld_color = "#dc3545" if _ld_diff > 0 else "#0D7A3F" if _ld_diff < 0 else "#666"
                    st.markdown(f'<span style="font-size:0.6rem;color:#666">实际均负荷 <b>{_ld_actual_avg:.0f}</b> MW | 预测均负荷 <b>{_ld_forecast_avg:.0f}</b> MW | 偏差 <span style="color:{_ld_color};font-weight:bold">{_ld_arrow} {_ld_diff:+.0f} ({_ld_diff_pct:+.1f}%)</span></span>', unsafe_allow_html=True)
                else:
                    st.markdown('<span style="font-size:0.6rem;color:#666">实际均负荷 <b>--</b> MW | 预测均负荷 <b>--</b> MW | 偏差 <b>--</b></span>', unsafe_allow_html=True)
        
        
        # 峰谷分析
        with st.container(border=True):
            st.markdown('<div class="mod-head mod-head-o">📊 峰谷时段分析<span class="mod-sub">近30天分布</span></div>', unsafe_allow_html=True)
            
            daily_stats = price_df.copy()
            # 检查列名是否存在
            valid_hour_cols_stats = [h for h in hour_cols if h in daily_stats.columns]
            if valid_hour_cols_stats:
                daily_stats['峰值'] = daily_stats[valid_hour_cols_stats].max(axis=1)
                daily_stats['谷值'] = daily_stats[valid_hour_cols_stats].min(axis=1)
                daily_stats['峰时'] = daily_stats[valid_hour_cols_stats].idxmax(axis=1).apply(lambda x: int(x.replace('时', '')))
                daily_stats['谷时'] = daily_stats[valid_hour_cols_stats].idxmin(axis=1).apply(lambda x: int(x.replace('时', '')))
            else:
                daily_stats['峰值'] = 0
                daily_stats['谷值'] = 0
                daily_stats['峰时'] = 0
                daily_stats['谷时'] = 0
            daily_stats['峰谷差'] = daily_stats['峰值'] - daily_stats['谷值']
            
            # 取最近30天
            daily_stats = daily_stats.tail(30)
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig1 = go.Figure()
                fig1.add_trace(go.Histogram(x=daily_stats['峰时'], nbinsx=24, name='峰时分布', marker_color='#dc3545'))
                fig1.update_layout(
                    height=160, template="neumorphic", showlegend=False,
                    margin=dict(l=20, r=10, t=5, b=20),
                    font=dict(size=8, color="#000000"),
                    xaxis=dict(title="小时", tickfont=dict(size=10, color="#000000")),
                    yaxis=dict(title="天数", tickfont=dict(size=10, color="#000000"))
                )
                st.plotly_chart(fig1, use_container_width=True)
            
            with col2:
                fig2 = go.Figure()
                fig2.add_trace(go.Histogram(x=daily_stats['谷时'], nbinsx=24, name='谷时分布', marker_color='#28a745'))
                fig2.update_layout(
                    height=160, template="neumorphic", showlegend=False,
                    margin=dict(l=20, r=10, t=5, b=20),
                    font=dict(size=8, color="#000000"),
                    xaxis=dict(title="小时", tickfont=dict(size=10, color="#000000")),
                    yaxis=dict(title="天数", tickfont=dict(size=10, color="#000000"))
                )
                st.plotly_chart(fig2, use_container_width=True)
            
            # 峰谷统计
            st.markdown(f'<span style="font-size:0.6rem;color:#666">平均峰谷差 <b>{daily_stats["峰谷差"].mean():.0f}</b> 元/MWh | 最大 {daily_stats["峰谷差"].max():.0f} | 最小 {daily_stats["峰谷差"].min():.0f}</span>', unsafe_allow_html=True)

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
