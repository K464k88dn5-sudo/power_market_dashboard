"""
广东日前电价预测模块
调用 ~/projects/gd-price-forecast 已有的生产预测脚本
模型重训后自动生效
"""

import os
import subprocess
import pandas as pd
from datetime import datetime, timedelta

FORECAST_PROJECT = os.path.expanduser("~/projects/gd-price-forecast")
SCRIPT = os.path.join(FORECAST_PROJECT, "scripts", "predict_production.py")


def forecast_price(target_date: str = None) -> pd.DataFrame:
    """
    执行日前电价预测
    调用 predict_production.py 脚本，解析输出
    返回 DataFrame: 小时(0-23), 预测电价(元/MWh)
    """
    if target_date is None:
        target_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    try:
        result = subprocess.run(
            ["python3", SCRIPT, target_date],
            capture_output=True, text=True, timeout=120,
            cwd=FORECAST_PROJECT,
        )

        if result.returncode != 0:
            print(f"[预测] 脚本错误: {result.stderr[:500]}")
            return pd.DataFrame()

        # 解析输出：每行格式 "H00      506.56     494.08     -12.48"
        lines = result.stdout.strip().split("\n")
        rows = []
        for line in lines:
            line = line.strip()
            if line.startswith("H") and len(line) > 3:
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        h = int(parts[0].replace("H", ""))
                        price = float(parts[1])  # 校准后价格
                        if 0 <= h <= 23 and price > 0:
                            rows.append({"小时": h, "预测电价(元/MWh)": round(price, 1)})
                    except (ValueError, IndexError):
                        continue

        if rows:
            df = pd.DataFrame(rows).sort_values("小时").reset_index(drop=True)
            df["日期"] = target_date
            return df

        print(f"[预测] 无法解析输出:\n{result.stdout[:1000]}")
        return pd.DataFrame()

    except subprocess.TimeoutExpired:
        print("[预测] 超时(120s)")
        return pd.DataFrame()
    except Exception as e:
        print(f"[预测] 失败: {e}")
        return pd.DataFrame()


if __name__ == "__main__":
    result = forecast_price("2026-06-05")
    if not result.empty:
        print(result.to_string(index=False))
        print(f"\n均价: {result['预测电价(元/MWh)'].mean():.1f}")
        print(f"峰值: {result['预测电价(元/MWh)'].max():.1f} ({result['预测电价(元/MWh)'].idxmax()}时)")
        print(f"谷值: {result['预测电价(元/MWh)'].min():.1f} ({result['预测电价(元/MWh)'].idxmin()}时)")
    else:
        print("预测失败")
