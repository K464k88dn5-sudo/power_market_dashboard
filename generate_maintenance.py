"""
广东电网检修计划数据生成器
基于实际检修规则生成仿真数据，覆盖21地市
可直接导入大屏使用
"""

import pandas as pd
import random
from datetime import datetime, timedelta
import os

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "检修计划数据.xlsx")

# 广东21地市
CITIES = {
    "广州": {"电压等级": ["500kV","220kV","110kV"], "典型线路": ["穗水","穗东","穗南","天广","沙广"]},
    "深圳": {"电压等级": ["500kV","220kV","110kV"], "典型线路": ["深鹏","深港","深东","岭深"]},
    "珠海": {"电压等级": ["220kV","110kV"], "典型线路": ["珠澳","珠东","珠西"]},
    "汕头": {"电压等级": ["220kV","110kV"], "典型线路": ["汕华","汕东","汕潮"]},
    "佛山": {"电压等级": ["500kV","220kV","110kV"], "典型线路": ["佛肇","佛南","佛西","罗佛"]},
    "韶关": {"电压等级": ["220kV","110kV"], "典型线路": ["韶北","韶南","韶赣"]},
    "湛江": {"电压等级": ["500kV","220kV","110kV"], "典型线路": ["湛茂","湛东","湛海"]},
    "肇庆": {"电压等级": ["220kV","110kV"], "典型线路": ["肇西","肇东","肇云"]},
    "江门": {"电压等级": ["220kV","110kV"], "典型线路": ["江珠","江门","江恩"]},
    "茂名": {"电压等级": ["220kV","110kV"], "典型线路": ["茂湛","茂名","茂阳"]},
    "惠州": {"电压等级": ["500kV","220kV","110kV"], "典型线路": ["惠东","惠州","惠深","惠莞"]},
    "梅州": {"电压等级": ["220kV","110kV"], "典型线路": ["梅汕","梅州","梅河"]},
    "汕尾": {"电压等级": ["220kV","110kV"], "典型线路": ["汕尾","汕东","汕惠"]},
    "河源": {"电压等级": ["220kV","110kV"], "典型线路": ["河惠","河源","河梅"]},
    "阳江": {"电压等级": ["220kV","110kV"], "典型线路": ["阳江","阳茂","阳云"]},
    "清远": {"电压等级": ["220kV","110kV"], "典型线路": ["清远","清佛","清韶"]},
    "东莞": {"电压等级": ["500kV","220kV","110kV"], "典型线路": ["莞惠","东莞","莞深","陈屋"]},
    "中山": {"电压等级": ["220kV","110kV"], "典型线路": ["中山","中珠","中江"]},
    "潮州": {"电压等级": ["220kV","110kV"], "典型线路": ["潮汕","潮州","潮揭"]},
    "揭阳": {"电压等级": ["220kV","110kV"], "典型线路": ["揭阳","揭汕","揭潮"]},
    "云浮": {"电压等级": ["220kV","110kV"], "典型线路": ["云浮","云肇","云阳"]},
}

# 检修类型及权重
MAINT_TYPES = {
    "计划检修": 0.55,
    "临时检修": 0.20,
    "故障检修": 0.10,
    "技改检修": 0.10,
    "扩建检修": 0.05,
}

# 状态及权重
STATUSES = {
    "进行中": 0.35,
    "待执行": 0.45,
    "已完成": 0.20,
}

# 电压等级对应容量范围(MW)
CAPACITY_MAP = {
    "500kV": (800, 2000),
    "220kV": (200, 800),
    "110kV": (50, 300),
}

def weighted_choice(choices):
    items = list(choices.keys())
    weights = list(choices.values())
    return random.choices(items, weights=weights, k=1)[0]

def generate_maintenance_data(num_records=30):
    """生成检修计划数据"""
    today = datetime.now()
    records = []
    
    for i in range(num_records):
        # 随机选择城市
        city = random.choice(list(CITIES.keys()))
        city_info = CITIES[city]
        
        # 随机选择电压等级
        voltage = random.choice(city_info["电压等级"])
        
        # 随机选择线路名称
        line_prefix = random.choice(city_info["典型线路"])
        suffix = random.choice(["甲线", "乙线", "丙线", "I线", "II线"])
        line_name = f"{line_prefix}{suffix}"
        
        # 检修类型
        maint_type = weighted_choice(MAINT_TYPES)
        
        # 状态
        status = weighted_choice(STATUSES)
        
        # 影响容量
        cap_range = CAPACITY_MAP.get(voltage, (50, 300))
        capacity = random.randint(cap_range[0], cap_range[1])
        
        # 日期
        if status == "已完成":
            start = today - timedelta(days=random.randint(5, 30))
            duration = random.randint(1, 7)
        elif status == "进行中":
            start = today - timedelta(days=random.randint(0, 5))
            duration = random.randint(2, 10)
        else:  # 待执行
            start = today + timedelta(days=random.randint(1, 15))
            duration = random.randint(1, 8)
        
        end = start + timedelta(days=duration)
        
        # 影响范围
        affected = city
        if random.random() > 0.6:
            neighbor = random.choice([c for c in CITIES.keys() if c != city])
            affected = f"{city}、{neighbor}"
        
        records.append({
            "线路名称": line_name,
            "检修类型": maint_type,
            "状态": status,
            "影响容量(MW)": capacity,
            "开始日期": start.strftime("%Y-%m-%d"),
            "结束日期": end.strftime("%Y-%m-%d"),
            "影响范围": affected,
            "电压等级": voltage,
            "来源": "仿真数据",
        })
    
    return pd.DataFrame(records)

if __name__ == "__main__":
    print("=" * 50)
    print("广东电网检修计划数据生成器")
    print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # 生成数据
    df = generate_maintenance_data(30)
    
    # 保存
    df.to_excel(OUTPUT_FILE, index=False, engine="openpyxl")
    print(f"\n已生成 {len(df)} 条检修记录")
    print(f"保存路径: {OUTPUT_FILE}")
    
    # 统计
    print(f"\n=== 数据统计 ===")
    print(f"覆盖城市: {df['影响范围'].nunique()} 个")
    print(f"检修类型: {df['检修类型'].value_counts().to_dict()}")
    print(f"状态分布: {df['状态'].value_counts().to_dict()}")
    print(f"电压等级: {df['电压等级'].value_counts().to_dict()}")
    
    print(f"\n=== 前10条数据 ===")
    print(df.head(10).to_string(index=False))
    
    print("\n" + "=" * 50)
    print("数据生成完成，可直接导入大屏")
    print("=" * 50)
