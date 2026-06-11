"""
线路检修数据接口
数据源：手动导入Excel / 调度系统导出
说明：线路检修数据属于调度内部数据，无公开API
      提供Excel模板导入 + 手动录入功能
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import os


def load_maintenance_from_excel(file_path: str) -> pd.DataFrame:
    """
    从Excel文件加载检修计划
    预期列：线路名称、检修类型、开始时间、结束时间、影响容量(MW)、影响区域、状态
    """
    try:
        if file_path.endswith('.xlsx') or file_path.endswith('.xls'):
            df = pd.read_excel(file_path)
        elif file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            _log.info(f"[检修数据] 不支持的文件格式: {file_path}")
            return pd.DataFrame()
        
        # 标准化列名
        col_mapping = {
            '线路': '线路名称',
            '名称': '线路名称',
            '类型': '检修类型',
            '开始': '开始时间',
            '结束': '结束时间',
            '容量': '影响容量(MW)',
            'MW': '影响容量(MW)',
            '区域': '影响区域',
        }
        
        for old_name, new_name in col_mapping.items():
            for col in df.columns:
                if old_name in str(col):
                    df = df.rename(columns={col: new_name})
                    break
        
        # 确保时间列为datetime
        for col in ['开始时间', '结束时间']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col]).dt.strftime('%Y-%m-%d')
        
        return df
        
    except Exception as e:
        _log.info(f"[检修数据] 读取Excel失败: {e}")
        return pd.DataFrame()


def get_maintenance_template() -> pd.DataFrame:
    """
    生成检修计划模板（可手动填写）
    """
    template = pd.DataFrame({
        '线路名称': ['示例：穗东-莞北 500kV'],
        '检修类型': ['计划检修'],
        '开始时间': ['2026-06-10'],
        '结束时间': ['2026-06-12'],
        '影响容量(MW)': [2000],
        '影响区域': ['广州东部'],
        '状态': ['待执行'],
        '备注': [''],
    })
    return template


def save_maintenance_template(file_path: str = None):
    """
    保存检修计划模板到文件
    """
    if file_path is None:
        file_path = os.path.expanduser("~/Desktop/检修计划模板.xlsx")
    
    template = get_maintenance_template()
    template.to_excel(file_path, index=False)
    _log.info(f"[检修数据] 模板已保存到: {file_path}")
    return file_path


def calculate_security_margin(maintenance_df: pd.DataFrame, 
                               peak_load_mw: float = 120000) -> dict:
    """
    计算检修影响下的安全裕度
    peak_load_mw: 广东夏季高峰负荷（MW）
    """
    if maintenance_df.empty:
        return {
            "总检修容量": 0,
            "进行中容量": 0,
            "安全裕度": 100.0,
            "预警等级": "充裕",
        }
    
    total_capacity = maintenance_df['影响容量(MW)'].sum()
    
    active = maintenance_df[maintenance_df['状态'] == '进行中']
    active_capacity = active['影响容量(MW)'].sum() if not active.empty else 0
    
    available = peak_load_mw - active_capacity
    margin = available / peak_load_mw * 100
    
    if margin > 95:
        level = "充裕"
    elif margin > 90:
        level = "偏紧"
    else:
        level = "紧张"
    
    return {
        "总检修容量(MW)": total_capacity,
        "进行中容量(MW)": active_capacity,
        "安全裕度(%)": round(margin, 1),
        "预警等级": level,
        "高峰负荷(MW)": peak_load_mw,
    }


# ============================================================
# 测试
# ============================================================
if __name__ == "__main__":
    _log.info("=== 检修数据模块 ===")
    
    # 生成模板
    path = save_maintenance_template()
    
    # 计算安全裕度
    template = get_maintenance_template()
    margin = calculate_security_margin(template)
    _log.info(f"\n安全裕度: {margin}")
