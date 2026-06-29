"""
数据路径管理器 - 自动检测数据文件位置
优先使用项目内数据，如果没有则使用本地路径
"""
import os

# 项目根目录
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 本地数据目录（仅在本地环境可用）
LOCAL_DATA_DIR = os.path.expanduser("~/projects/能源电力资料")

def get_price_path():
    """获取电价数据路径"""
    # 优先使用项目内文件
    local_path = os.path.join(PROJECT_DIR, "日前节点电价.xlsx")
    if os.path.exists(local_path):
        return local_path
    # 否则使用本地路径
    return os.path.join(LOCAL_DATA_DIR, "日前训练数据", "日前节点电价.xlsx")

def get_disclosure_pred_dir():
    """获取披露预测数据目录"""
    # 优先使用项目内目录
    local_dir = os.path.join(PROJECT_DIR, "disclosure")
    if os.path.exists(local_dir):
        return local_dir
    # 否则使用本地路径
    return os.path.join(LOCAL_DATA_DIR, "日前训练数据", "信息披露日前")

def get_disclosure_actual_dir():
    """获取披露实际数据目录"""
    # 优先使用项目内目录
    local_dir = os.path.join(PROJECT_DIR, "disclosure_actual")
    if os.path.exists(local_dir):
        return local_dir
    # 否则使用本地路径
    return os.path.join(LOCAL_DATA_DIR, "实时训练数据", "信息披露实际")

def get_realtime_price_dir():
    """获取实时电价数据目录"""
    # 优先使用项目内目录
    local_dir = os.path.join(PROJECT_DIR, "realtime_price")
    if os.path.exists(local_dir):
        return local_dir
    # 否则使用本地路径
    return os.path.join(LOCAL_DATA_DIR, "实时训练数据", "日前和实时电价占比", "2026")

def get_disclosure_pred_file(date_str):
    """获取披露预测文件路径"""
    return os.path.join(get_disclosure_pred_dir(), f"信息披露查询预测信息({date_str}).xlsx")

def get_disclosure_actual_file(date_str):
    """获取披露实际文件路径"""
    return os.path.join(get_disclosure_actual_dir(), f"信息披露查询实际信息({date_str}).xlsx")

def get_realtime_price_file(date_str):
    """获取实时电价文件路径"""
    month = str(int(date_str[5:7]))
    return os.path.join(get_realtime_price_dir(), month, f"实时节点电价查询({date_str}).xlsx")
