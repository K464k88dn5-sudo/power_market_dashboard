"""
电价数据接口
数据源：广东电力交易中心（爬取）+ AKShare + 北极星售电网
注意：广东电力交易中心无公开API，需网页爬取
"""

import pandas as pd
import requests
from datetime import datetime, timedelta
from typing import Optional
import re
import json
import os
import logging as _logging

_log = _logging.getLogger("price_api")
_log.addHandler(_logging.NullHandler())

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False
    _log.warning("[电价数据] beautifulsoup4未安装")

try:
    import akshare as ak
    HAS_AKSHARE = True
except ImportError:
    HAS_AKSHARE = False

# 请求头
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def fetch_guangdong_spot_from_bjx() -> pd.DataFrame:
    """
    从北极星售电网获取广东电力交易数据
    北极星汇总各省交易结果，相对稳定
    """
    if not HAS_BS4:
        return pd.DataFrame()
    
    try:
        # 北极星售电网 - 广东电力交易
        url = "https://sd.bjx.com.cn/topics/gddljy/"
        resp = requests.get(url, headers=HEADERS, timeout=(1, 5))
        resp.encoding = resp.apparent_encoding

        soup = BeautifulSoup(resp.text, "lxml")

        # 查找新闻列表中的电价信息
        articles = []
        for item in soup.select("li a"):
            title = item.get_text(strip=True)
            href = item.get("href", "")
            if any(kw in title for kw in ["电价", "出清", "交易结果", "日前市场", "月度"]):
                articles.append({
                    "标题": title,
                    "链接": href if href.startswith("http") else f"https://sd.bjx.com.cn{href}",
                })

        if articles:
            return pd.DataFrame(articles[:10])

    except (requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError):
        _log.warning("[电价数据] 北极星不可达，跳过")
    except Exception as e:
        _log.warning(f"[电价数据] 北极星爬取失败: {e}")
    
    return pd.DataFrame()


def fetch_guangdong_spot_from_gddl() -> pd.DataFrame:
    """
    从广东电力交易中心获取日前市场出清价格
    URL: https://www.gddl.cn
    快速降级：首个URL超时即跳过其余URL
    """
    if not HAS_BS4:
        return pd.DataFrame()

    try:
        urls_to_try = [
            "https://www.gddl.cn/xxpl/scjg/",  # 市场结果
            "https://www.gddl.cn/xxpl/",         # 信息披露
            "https://pmo.gddl.cn/",              # 市场运营系统
        ]

        for url in urls_to_try:
            try:
                resp = requests.get(url, headers=HEADERS, timeout=(1, 5), verify=False)
                if resp.status_code == 200:
                    resp.encoding = resp.apparent_encoding
                    tables = pd.read_html(resp.text)
                    if tables:
                        _log.info(f"[电价数据] 从 {url} 获取到 {len(tables)} 个表格")
                        for table in tables:
                            if len(table) > 2:
                                return table
            except (requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError):
                # 主机不可达，同一站点后续URL也会超时，直接退出
                _log.warning(f"[电价数据] {url} 不可达，快速降级")
                break
            except requests.exceptions.Timeout:
                _log.warning(f"[电价数据] {url} 读取超时")
                continue
            except Exception as e:
                _log.warning(f"[电价数据] {url} 访问失败: {e}")
                continue

        _log.warning("[电价数据] 广东电力交易中心无法访问")

    except Exception as e:
        _log.warning(f"[电价数据] 广东交易中心爬取失败: {e}")

    return pd.DataFrame()


def fetch_electricity_price_akshare() -> pd.DataFrame:
    """
    通过AKShare获取电力相关数据
    """
    if not HAS_AKSHARE:
        return pd.DataFrame()
    
    try:
        # 尝试获取电力期货或现货数据
        # AKShare可能有部分电力数据接口
        df = ak.futures_spot_price_daily(start_day=(datetime.now() - timedelta(days=30)).strftime("%Y%m%d"),
                                          end_day=datetime.now().strftime("%Y%m%d"),
                                          vars_list=["电力"])
        if df is not None and not df.empty:
            return df
    except:
        pass
    
    return pd.DataFrame()


def generate_guangdong_price_template() -> pd.DataFrame:
    """
    生成广东日前电价模板（24小时）
    基于广东电力市场典型价格曲线特征：
    - 峰时(8-12, 14-17): 高价
    - 谷时(0-6): 低价
    - 尖峰(10-12, 15-17): 最高价
    """
    import numpy as np
    
    hours = list(range(24))
    # 广东典型日前电价曲线 (元/MWh)
    base_prices = [
        280, 260, 250, 245, 250, 270,  # 0-5: 低谷
        320, 380, 420, 450, 480, 470,  # 6-11: 上午峰
        430, 410, 420, 440, 470, 460,  # 12-17: 下午峰
        430, 400, 380, 350, 320, 290,  # 18-23: 晚间下降
    ]
    
    today = datetime.now().date()
    dates = [today + timedelta(days=i) for i in range(7)]
    
    records = []
    np.random.seed(int(today.strftime("%Y%m%d")))
    
    for d in dates:
        # 加入日期间波动
        day_factor = 1 + np.random.normal(0, 0.05)
        for h in hours:
            price = base_prices[h] * day_factor + np.random.normal(0, 15)
            price = max(price, 80)  # 最低价限制
            records.append({
                "日期": d.strftime("%Y-%m-%d"),
                "小时": h,
                "参考电价(元/MWh)": round(price, 2),
            })
    
    return pd.DataFrame(records)


def fetch_price_news() -> pd.DataFrame:
    """
    获取最新电价相关新闻/政策
    """
    if not HAS_BS4:
        return pd.DataFrame()
    
    sources = [
        ("北极星售电网", "https://sd.bjx.com.cn/"),
        ("南方能源观察", "https://www.ne21.com/"),
    ]
    
    all_news = []
    
    for source_name, url in sources:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=(1, 5))
            resp.encoding = resp.apparent_encoding
            soup = BeautifulSoup(resp.text, "lxml")

            for item in soup.select("a"):
                title = item.get_text(strip=True)
                href = item.get("href", "")
                if len(title) > 10 and any(kw in title for kw in
                    ["电价", "电力市场", "现货", "交易", "出清", "新能源", "储能", "虚拟电厂"]):
                    all_news.append({
                        "来源": source_name,
                        "标题": title[:80],
                        "链接": href if href.startswith("http") else url.rstrip("/") + href,
                    })
        except (requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError):
            _log.warning(f"[电价新闻] {source_name} 不可达，跳过")
            break  # 网络不通，后续源也会超时
        except Exception as e:
            _log.warning(f"[电价新闻] {source_name} 爬取失败: {e}")
    
    if all_news:
        df = pd.DataFrame(all_news).drop_duplicates(subset=["标题"]).head(15)
        return df
    
    return pd.DataFrame()


# ============================================================
# 综合获取
# ============================================================
import socket as _socket
import json as _json

_PRICE_CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".price_cache.json")

def _load_price_cache(max_age=86400) -> dict:
    """从本地缓存加载电价数据（默认24小时内有效）"""
    try:
        if os.path.exists(_PRICE_CACHE_FILE):
            with open(_PRICE_CACHE_FILE, "r") as f:
                cached = _json.load(f)
            # 检查缓存是否在有效期内
            from datetime import datetime as _dt
            cached_time = _dt.fromisoformat(cached.get("timestamp", "2000-01-01"))
            if (_dt.now() - cached_time).total_seconds() < max_age:
                _log.info(f"[电价数据] 使用本地缓存")
                return {
                    "spot_price": pd.DataFrame(cached.get("spot_price", [])),
                    "news": pd.DataFrame(cached.get("news", [])),
                    "source": cached.get("source", "unknown") + "（缓存）",
                }
    except Exception as e:
        _log.warning(f"[电价数据] 缓存读取失败: {e}")
    return {}

def _save_price_cache(data: dict):
    """保存电价数据到本地缓存"""
    try:
        cache_data = {
            "timestamp": datetime.now().isoformat(),
            "source": data.get("source", "unknown"),
            "spot_price": data.get("spot_price", pd.DataFrame()).to_dict(orient="records"),
            "news": data.get("news", pd.DataFrame()).to_dict(orient="records"),
        }
        with open(_PRICE_CACHE_FILE, "w") as f:
            _json.dump(cache_data, f, ensure_ascii=False)
    except Exception as e:
        _log.warning(f"[电价数据] 缓存写入失败: {e}")

def _network_reachable(host="8.8.8.8", port=53, timeout=1) -> bool:
    """快速探测网络是否可达（DNS端口，1秒超时）"""
    try:
        s = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((host, port))
        s.close()
        return True
    except Exception:
        return False

def fetch_electricity_data() -> dict:
    """
    综合获取电价相关数据
    返回字典：日前电价、新闻资讯
    优先使用本地缓存（1小时内有效），避免频繁网络请求
    """
    result = {
        "spot_price": pd.DataFrame(),
        "news": pd.DataFrame(),
        "source": "unknown",
    }

    # 优先检查本地缓存（1小时内有效）
    cached = _load_price_cache(max_age=3600)
    if cached:
        return cached

    # 无缓存时：先用模板快速响应，后台不阻塞
    # 网络预检：不可达则直接用模板
    if not _network_reachable():
        _log.warning("[电价数据] 网络不可达，使用参考模板")
        result["spot_price"] = generate_guangdong_price_template()
        result["source"] = "参考模板（网络不可达）"
        _save_price_cache(result)
        return result

    try:
        # 优先尝试广东交易中心
        spot = fetch_guangdong_spot_from_gddl()
        if not spot.empty:
            result["spot_price"] = spot
            result["source"] = "广东电力交易中心"
            _save_price_cache(result)
            return result

        # 备选：北极星
        spot = fetch_guangdong_spot_from_bjx()
        if not spot.empty:
            result["spot_price"] = spot
            result["source"] = "北极星售电网"
    except Exception as e:
        _log.warning(f"[电价数据] 数据获取异常: {e}")

    # 兜底：生成参考模板
    result["spot_price"] = generate_guangdong_price_template()
    result["source"] = "参考模板（基于历史价格曲线特征）"

    # 获取相关新闻
    try:
        result["news"] = fetch_price_news()
    except Exception as e:
        _log.warning(f"[电价数据] 新闻获取失败: {e}")

    # 保存到缓存
    _save_price_cache(result)

    return result


# ============================================================
# 测试
# ============================================================
if __name__ == "__main__":
    print("=== 测试电价数据接口 ===")
    
    data = fetch_electricity_data()
    print(f"数据来源: {data['source']}")
    
    if not data["spot_price"].empty:
        print(f"\n电价数据: {len(data['spot_price'])} 条")
        print(data["spot_price"].head(10))
    
    if not data["news"].empty:
        print(f"\n相关新闻: {len(data['news'])} 条")
        print(data["news"].head())
