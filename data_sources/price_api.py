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

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False
    print("[电价数据] beautifulsoup4未安装，请运行: pip install beautifulsoup4")

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
        resp = requests.get(url, headers=HEADERS, timeout=15)
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
        
    except Exception as e:
        print(f"[电价数据] 北极星爬取失败: {e}")
    
    return pd.DataFrame()


def fetch_guangdong_spot_from_gddl() -> pd.DataFrame:
    """
    从广东电力交易中心获取日前市场出清价格
    URL: https://www.gddl.cn
    注意：该站点可能有反爬机制，需测试可达性
    """
    if not HAS_BS4:
        return pd.DataFrame()
    
    try:
        # 尝试访问广东电力交易中心信息披露页面
        urls_to_try = [
            "https://www.gddl.cn/xxpl/scjg/",  # 市场结果
            "https://www.gddl.cn/xxpl/",         # 信息披露
            "https://pmo.gddl.cn/",              # 市场运营系统
        ]
        
        for url in urls_to_try:
            try:
                resp = requests.get(url, headers=HEADERS, timeout=10, verify=False)
                if resp.status_code == 200:
                    resp.encoding = resp.apparent_encoding
                    soup = BeautifulSoup(resp.text, "lxml")
                    
                    # 提取表格数据
                    tables = pd.read_html(resp.text)
                    if tables:
                        print(f"[电价数据] 从 {url} 获取到 {len(tables)} 个表格")
                        # 返回第一个有效表格
                        for table in tables:
                            if len(table) > 2:
                                return table
            except:
                continue
        
        print("[电价数据] 广东电力交易中心无法访问")
        
    except Exception as e:
        print(f"[电价数据] 广东交易中心爬取失败: {e}")
    
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
            resp = requests.get(url, headers=HEADERS, timeout=10)
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
        except Exception as e:
            print(f"[电价新闻] {source_name} 爬取失败: {e}")
    
    if all_news:
        df = pd.DataFrame(all_news).drop_duplicates(subset=["标题"]).head(15)
        return df
    
    return pd.DataFrame()


# ============================================================
# 综合获取
# ============================================================
def fetch_electricity_data() -> dict:
    """
    综合获取电价相关数据
    返回字典：日前电价、新闻资讯
    """
    result = {
        "spot_price": pd.DataFrame(),
        "news": pd.DataFrame(),
        "source": "unknown",
    }
    
    # 优先尝试广东交易中心
    spot = fetch_guangdong_spot_from_gddl()
    if not spot.empty:
        result["spot_price"] = spot
        result["source"] = "广东电力交易中心"
        return result
    
    # 备选：北极星
    spot = fetch_guangdong_spot_from_bjx()
    if not spot.empty:
        result["spot_price"] = spot
        result["source"] = "北极星售电网"
    
    # 兜底：生成参考模板
    result["spot_price"] = generate_guangdong_price_template()
    result["source"] = "参考模板（基于历史价格曲线特征）"
    
    # 获取相关新闻
    result["news"] = fetch_price_news()
    
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
