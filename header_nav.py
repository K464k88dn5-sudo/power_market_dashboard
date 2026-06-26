"""
共享的标题栏和导航栏模块
"""
import streamlit as st
import streamlit.components.v1 as components
import os
import base64
from datetime import datetime, timezone, timedelta

_CN_TZ = timezone(timedelta(hours=8))

def _now():
    return datetime.now(_CN_TZ)

def render_header_nav(current_page="电力大屏"):
    """渲染标题栏和导航栏"""
    from styles import inject_styles
    inject_styles()
    
    # Logo
    _logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.png")
    if os.path.exists(_logo_path):
        with open(_logo_path, "rb") as _f:
            _logo_b64 = base64.b64encode(_f.read()).decode()
        _logo_html = f'<img src="data:image/png;base64,{_logo_b64}" style="height:36px;">'
    else:
        _logo_html = ''

    # 标题栏
    _header_html = f'''<div style="margin-top:6px;margin-bottom:6px;background:linear-gradient(135deg,rgba(255,255,255,0.9) 0%,rgba(240,242,245,0.95) 100%);border:1px solid #ffffff;border-radius:14px;padding:8px 16px;display:flex;align-items:center;gap:12px;box-shadow:0 4px 12px rgba(0,0,0,0.06);height:54px;">
        {_logo_html}
        <span style="font-size:1.15rem;font-weight:700;color:#1D1D1F;letter-spacing:0.2em;white-space:nowrap;">电力市场多源数据监控大屏</span>
        <span style="font-size:0.65rem;color:#666;margin-left:auto;">{_now().strftime("%Y-%m-%d %H:%M")}</span>
    </div>'''
    st.markdown(_header_html, unsafe_allow_html=True)
    
    # 导航按钮 + 同步按钮
    _nav_pages = [
        ("📊", "电力大屏", "app.py"),
        ("📈", "数据分析", "pages/2_📊_数据分析.py"),
        ("📋", "历史数据", "pages/3_📈_历史数据.py"),
        ("📰", "资讯", "pages/1_📰_资讯.py"),
    ]
    
    # 导航按钮 + 同步按钮（最右侧）
    _nav_cols = st.columns([1]*len(_nav_pages) + [3, 1])
    for i, (icon, name, page) in enumerate(_nav_pages):
        with _nav_cols[i]:
            if st.button(icon + " " + name, key="nav_btn_" + name, use_container_width=True):
                st.switch_page(page)
    
    # 同步按钮放在最后一列
    with _nav_cols[len(_nav_pages) + 1]:
        if st.button("☁️ 同步公网", key="nav_sync_btn", use_container_width=True):
            import subprocess
            _repo = os.path.dirname(os.path.abspath(__file__))
            with st.spinner("同步中..."):
                _result = subprocess.run(
                    ["bash", os.path.join(_repo, "sync_data.sh")],
                    capture_output=True, text=True, cwd=_repo, timeout=60
                )
                if _result.returncode == 0:
                    st.toast("✅ 同步成功", icon="☁️")
                else:
                    st.toast(f"❌ 同步失败: {_result.stderr[:100]}", icon="⚠️")
    
    # 白色分隔线
    st.markdown('<div style="height:1px;background:#ffffff;margin-top:-8px;margin-bottom:0;"></div>', unsafe_allow_html=True)
    
    # 使用components.html注入JS高亮当前按钮
    components.html(f'''
    <script>
    var btns = parent.document.querySelectorAll('button');
    btns.forEach(function(btn) {{
        if (btn.textContent.includes('{current_page}')) {{
            btn.style.setProperty('background', '#007bff', 'important');
            btn.style.setProperty('color', 'white', 'important');
            btn.style.setProperty('border-color', '#007bff', 'important');
        }}
    }});
    </script>
    ''', height=0)
