#!/bin/bash
# ============================================================
# 同步本地数据文件到项目目录（用于公网部署）
# ============================================================

REPO_DIR="/Users/duchaochao/Desktop/power_market_dashboard"
SRC_BASE="/Users/duchaochao/projects/能源电力资料"

echo "同步本地数据文件..."

# 1. 同步电价数据
cp "$SRC_BASE/日前训练数据/日前节点电价.xlsx" "$REPO_DIR/日前节点电价.xlsx"
echo "✅ 同步: 日前节点电价.xlsx"

# 2. 同步披露数据（最近30天）
mkdir -p "$REPO_DIR/disclosure"
for i in $(seq -30 14); do
    D=$(date -v+${i}d '+%Y-%m-%d' 2>/dev/null)
    if [ -z "$D" ]; then
        continue
    fi
    SRC="$SRC_BASE/日前训练数据/信息披露日前/信息披露查询预测信息($D).xlsx"
    DST="$REPO_DIR/disclosure/信息披露查询预测信息($D).xlsx"
    if [ -f "$SRC" ]; then
        cp "$SRC" "$DST"
    fi
done
echo "✅ 同步: 披露数据"

# 3. 同步实时电价数据（最近7天）
mkdir -p "$REPO_DIR/realtime_price"
for i in $(seq -7 0); do
    D=$(date -v+${i}d '+%Y-%m-%d' 2>/dev/null)
    if [ -z "$D" ]; then
        continue
    fi
    MONTH=$(echo $D | cut -d'-' -f2 | sed 's/^0//')
    SRC_DIR="$SRC_BASE/实时训练数据/日前和实时电价占比/2026/$MONTH"
    if [ -d "$SRC_DIR" ]; then
        mkdir -p "$REPO_DIR/realtime_price/$MONTH"
        SRC="$SRC_DIR/实时节点电价查询($D).xlsx"
        DST="$REPO_DIR/realtime_price/$MONTH/实时节点电价查询($D).xlsx"
        if [ -f "$SRC" ]; then
            cp "$SRC" "$DST"
        fi
    fi
done
echo "✅ 同步: 实时电价数据"

echo "完成！"
