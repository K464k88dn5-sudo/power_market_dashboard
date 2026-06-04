"""
广东电力线路检修数据获取工具
数据源：
  1. 南方电网95598停电查询（公开数据）
  2. 广东电力交易中心信息披露（检修计划）
  3. 手动录入模板
运行：python3 fetch_maintenance.py
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import os
import json
import time

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# 检修数据输出路径
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "检修计划数据.xlsx")

# 广东主要城市
GD_CITIES = [
    "广州", "深圳", "珠海", "汕头", "佛山", "韶关", "湛江", "肇庆",
    "江门", "茂名", "惠州", "梅州", "汕尾", "河源", "阳江", "清远",
    "东莞", "中山", "潮州", "揭阳", "云浮",
]


def fetch_95598_outage(city="广州", days=7):
    """
    从南方电网95598获取停电/检修信息
    注意：95598网站需要登录且有反爬机制，此为示例框架
    """
    print(f"[95598] 尝试获取{city}停电信息...")
    
    # 95598停电查询页面
    url = "https://95598.csg.cn/outage/queryOutage"
    
    params = {
        "city": city,
        "startDate": datetime.now().strftime("%Y-%m-%d"),
        "endDate": (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d"),
    }
    
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            # 解析返回数据（需根据实际页面结构调整）
            data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            if data.get("success"):
                records = []
                for item in data.get("data", {}).get("list", []):
                    records.append({
                        "线路名称": item.get("lineName", ""),
                        "检修类型": "计划检修",
                        "状态": "待执行",
                        "影响容量(MW)": item.get("capacity", 0),
                        "开始日期": item.get("startTime", ""),
                        "结束日期": item.get("endTime", ""),
                        "影响范围": item.get("area", ""),
                        "来源": "95598",
                    })
                return records
        print(f"[95598] 请求状态: {resp.status_code}")
    except Exception as e:
        print(f"[95598] 获取失败: {e}")
    
    return []


def fetch_gddl_maintenance():
    """
    从广东电力交易中心获取检修计划信息
    交易中心信息披露包含机组检修计划
    """
    print("[交易中心] 尝试获取检修计划...")
    
    # 广东电力交易中心信息披露页面
    url = "https://www.gddl.cn/xxpl/xxplMain"
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            # 查找检修相关公告
            links = soup.find_all("a", string=lambda t: t and ("检修" in t or "停电" in t or "计划" in t))
            records = []
            for link in links[:20]:
                title = link.get_text(strip=True)
                href = link.get("href", "")
                if href and not href.startswith("http"):
                    href = f"https://www.gddl.cn{href}"
                records.append({
                    "标题": title,
                    "链接": href,
                    "来源": "广东电力交易中心",
                })
            return records
    except Exception as e:
        print(f"[交易中心] 获取失败: {e}")
    
    return []


def generate_template():
    """
    生成检修计划Excel模板
    """
    print("[模板] 生成检修计划模板...")
    
    # 示例数据
    today = datetime.now()
    sample_data = [
        {
            "线路名称": "穗水甲线",
            "检修类型": "计划检修",
            "状态": "进行中",
            "影响容量(MW)": 500,
            "开始日期": (today - timedelta(days=2)).strftime("%Y-%m-%d"),
            "结束日期": (today + timedelta(days=5)).strftime("%Y-%m-%d"),
            "影响范围": "广州",
            "电压等级": "220kV",
            "来源": "模板",
        },
        {
            "线路名称": "深鹏乙线",
            "检修类型": "计划检修",
            "状态": "待执行",
            "影响容量(MW)": 300,
            "开始日期": (today + timedelta(days=3)).strftime("%Y-%m-%d"),
            "结束日期": (today + timedelta(days=8)).strftime("%Y-%m-%d"),
            "影响范围": "深圳",
            "电压等级": "220kV",
            "来源": "模板",
        },
        {
            "线路名称": "佛肇线",
            "检修类型": "临时检修",
            "状态": "进行中",
            "影响容量(MW)": 200,
            "开始日期": (today - timedelta(days=1)).strftime("%Y-%m-%d"),
            "结束日期": (today + timedelta(days=2)).strftime("%Y-%m-%d"),
            "影响范围": "佛山、肇庆",
            "电压等级": "110kV",
            "来源": "模板",
        },
        {
            "线路名称": "莞惠甲线",
            "检修类型": "计划检修",
            "状态": "已完成",
            "影响容量(MW)": 400,
            "开始日期": (today - timedelta(days=10)).strftime("%Y-%m-%d"),
            "结束日期": (today - timedelta(days=3)).strftime("%Y-%m-%d"),
            "影响范围": "东莞、惠州",
            "电压等级": "220kV",
            "来源": "模板",
        },
        {
            "线路名称": "湛茂线",
            "检修类型": "故障检修",
            "状态": "进行中",
            "影响容量(MW)": 150,
            "开始日期": today.strftime("%Y-%m-%d"),
            "结束日期": (today + timedelta(days=4)).strftime("%Y-%m-%d"),
            "影响范围": "湛江、茂名",
            "电压等级": "110kV",
            "来源": "模板",
        },
    ]
    
    return sample_data


def fetch_all_maintenance():
    """
    汇总所有数据源的检修信息
    """
    all_records = []
    
    # 1. 95598停电查询
    for city in ["广州", "深圳", "佛山"]:
        records = fetch_95598_outage(city)
        all_records.extend(records)
        time.sleep(1)  # 避免请求过快
    
    # 2. 交易中心公告
    gddl_records = fetch_gddl_maintenance()
    if gddl_records:
        print(f"[交易中心] 获取到 {len(gddl_records)} 条公告")
    
    # 3. 如果没有获取到数据，使用模板
    if not all_records:
        print("[提示] 未获取到实时数据，使用示例模板")
        all_records = generate_template()
    
    return all_records, gddl_records


def save_to_excel(records, output_path=OUTPUT_FILE):
    """
    保存检修数据到Excel
    """
    if not records:
        print("[保存] 无数据可保存")
        return
    
    df = pd.DataFrame(records)
    
    # 确保列顺序
    cols = ["线路名称", "检修类型", "状态", "影响容量(MW)", "开始日期", "结束日期", "影响范围", "电压等级", "来源"]
    df = df[[c for c in cols if c in df.columns]]
    
    df.to_excel(output_path, index=False, engine="openpyxl")
    print(f"[保存] 已保存 {len(df)} 条记录到: {output_path}")
    
    return df


def save_news_to_excel(records, output_path=None):
    """
    保存交易中心公告到Excel
    """
    if not records:
        return
    
    if output_path is None:
        output_path = os.path.join(OUTPUT_DIR, "检修公告列表.xlsx")
    
    df = pd.DataFrame(records)
    df.to_excel(output_path, index=False, engine="openpyxl")
    print(f"[保存] 已保存 {len(df)} 条公告到: {output_path}")


# ============================================================
# 主程序
# ============================================================
if __name__ == "__main__":
    print("=" * 50)
    print("广东电力线路检修数据获取工具")
    print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # 获取数据
    maintenance_records, news_records = fetch_all_maintenance()
    
    # 保存检修计划
    df = save_to_excel(maintenance_records)
    if df is not None:
        print("\n=== 检修计划数据 ===")
        print(df.to_string(index=False))
    
    # 保存公告列表
    if news_records:
        save_news_to_excel(news_records)
        print("\n=== 交易中心公告 ===")
        for r in news_records[:5]:
            print(f"  - {r['标题']}")
    
    print("\n" + "=" * 50)
    print("数据获取完成")
    print(f"检修数据文件: {OUTPUT_FILE}")
    print("可直接导入大屏使用")
    print("=" * 50)
