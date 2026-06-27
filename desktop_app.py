#!/usr/bin/env python3
"""
电力市场监控大屏 - 桌面版
"""
import subprocess
import time
import os
import sys
import signal
import urllib.request

# 配置
PORT = 8501
APP_DIR = os.path.expanduser("~/Desktop/power_market_dashboard")
URL = f"http://localhost:{PORT}"

# Streamlit进程
streamlit_proc = None

def start_streamlit():
    """启动Streamlit服务"""
    global streamlit_proc
    os.chdir(APP_DIR)
    streamlit_proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app.py",
         "--server.port", str(PORT), "--server.headless", "true"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return streamlit_proc

def stop_streamlit():
    """停止Streamlit服务"""
    global streamlit_proc
    if streamlit_proc:
        try:
            streamlit_proc.terminate()
            streamlit_proc.wait(timeout=5)
        except:
            try:
                streamlit_proc.kill()
            except:
                pass
        streamlit_proc = None

def wait_for_server(url, timeout=30):
    """等待服务器启动"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except:
            time.sleep(0.5)
    return False

def is_server_running():
    """检查服务器是否已在运行"""
    try:
        urllib.request.urlopen(URL + "/_stcore/health", timeout=2)
        return True
    except:
        return False

def main():
    # 如果服务器已在运行，直接打开桌面窗口
    if is_server_running():
        print("电力大屏已在运行")
    else:
        # 启动Streamlit
        print("正在启动电力大屏...")
        start_streamlit()
        
        # 等待服务器就绪
        if not wait_for_server(URL):
            print("启动超时")
            stop_streamlit()
            return
        
        print("启动成功")
    
    # 尝试打开桌面窗口
    print("正在打开桌面窗口...")
    try:
        import webview
        
        def on_closed():
            stop_streamlit()
        
        window = webview.create_window(
            title="电力市场多源数据监控大屏",
            url=URL,
            width=1920,
            height=1080,
            min_size=(1280, 720),
            resizable=True,
            zoomable=True,
            text_select=True,
        )
        window.events.closed += on_closed
        
        # 启动GUI
        webview.start(debug=False)
    except Exception as e:
        print(f"桌面窗口启动失败: {e}")
        print("正在打开浏览器...")
        import webbrowser
        webbrowser.open(URL)
        
        # 保持运行
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    
    # 清理
    stop_streamlit()

if __name__ == "__main__":
    main()
