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

def render_header_nav(current_page="电力大屏", margin_top="0px", nav_gap="0px"):
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
    _header_html = f'''<div style="margin-top:{margin_top};background:linear-gradient(135deg,rgba(255,255,255,0.9) 0%,rgba(240,242,245,0.95) 100%);border:1px solid #ffffff;border-radius:14px 14px 0 0;padding:8px 16px;display:flex;align-items:center;gap:12px;box-shadow:0 4px 12px rgba(0,0,0,0.06);height:54px;margin-bottom:6px;">
        {_logo_html}
        <span style="font-size:1.5rem;font-weight:700;color:#00d2d3;letter-spacing:0.2em;white-space:nowrap;text-align:center;flex:1;">电力市场多源数据监控大屏</span>
        <span style="font-size:1.0rem;color:#666;">{_now().strftime("%Y-%m-%d %H:%M")}</span>
    </div>'''
    st.markdown(_header_html, unsafe_allow_html=True)
    
    # 导航按钮（紧贴标题栏）
    if nav_gap != "0px":
        st.markdown(f'<style>div[data-testid="stVerticalBlock"] {{ gap: 0 !important; }}</style>', unsafe_allow_html=True)
    _nav_pages = [
        ("电力大屏", "app.py"),
        ("数据分析", "pages/2_📊_数据分析.py"),
        ("历史数据", "pages/3_📈_历史数据.py"),
        ("实时数据", "pages/1_📡_实时数据.py"),
        ("报表管理", "pages/4_📋_报表管理.py"),
        ("数据管理", "pages/5_📁_数据管理.py"),
        ("系统配置", "pages/6_⚙️_系统配置.py"),
    ]
    
    _nav_cols = st.columns([1]*(len(_nav_pages) + 1))
    for i, (name, page) in enumerate(_nav_pages):
        with _nav_cols[i]:
            if st.button(name, key="nav_btn_" + name, use_container_width=True):
                st.switch_page(page)
    
    # 同步按钮
    with _nav_cols[len(_nav_pages)]:
        if st.button("同步公网", key="nav_sync_btn", use_container_width=True):
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
    
    # JavaScript：导航按钮顶部直角 + 高亮当前页面 + 悬停效果
    _js = f'''
    <script>
    (function() {{
        var navNames = ['电力大屏','数据分析','历史数据','实时数据','报表管理','数据管理','系统配置','同步公网'];
        var current = '{current_page}';
        var btns = parent.document.querySelectorAll('button');
        btns.forEach(function(btn) {{
            var text = btn.textContent.trim();
            // 导航按钮顶部直角
            for (var i = 0; i < navNames.length; i++) {{
                if (text.includes(navNames[i])) {{
                    btn.style.setProperty('border-radius', '0 0 8px 8px', 'important');
                    btn.style.setProperty('border-top', 'none', 'important');
                    btn.style.setProperty('margin', '0', 'important');
                    break;
                }}
            }}
            // 高亮当前页面（深蓝色）
            if (text.includes(current)) {{
                btn.style.setProperty('background', '#007AFF', 'important');
                btn.style.setProperty('color', '#ffffff', 'important');
                btn.style.setProperty('border-color', '#007AFF', 'important');
                btn.style.setProperty('font-weight', '600', 'important');
            }}
        }});
    }})();
    </script>
    '''
    components.html(_js, height=0)
