#!/bin/bash
# ============================================================
# 电力市场数据自动同步到 GitHub
# 用法: ./sync_data.sh
# ============================================================

REPO_DIR="/Users/duchaochao/Desktop/power_market_dashboard"
LOG_FILE="$REPO_DIR/sync_data.log"
SRC_PRICE="$HOME/projects/能源电力资料/日前训练数据"
SRC_DISCLOSURE="$SRC_PRICE/信息披露日前"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始同步..." >> "$LOG_FILE"
cd "$REPO_DIR" || exit 1

CHANGED=false

# 1. 同步电价数据（只读源文件 → 仓库）
for f in "日前节点电价.xlsx"; do
    SRC="$SRC_PRICE/$f"
    if [ -f "$SRC" ]; then
        if [ ! -f "$f" ] || ! cmp -s "$SRC" "$f"; then
            cp "$SRC" "$f"
            git add "$f"
            CHANGED=true
            echo "[$(date '+%H:%M:%S')] 更新: $f" >> "$LOG_FILE"
        fi
    fi
done

# 2. 同步预测电价（仓库内文件，直接add）
if [ -f "广东日前电价预测.xlsx" ]; then
    if ! git diff --quiet "广东日前电价预测.xlsx" 2>/dev/null; then
        git add "广东日前电价预测.xlsx"
        CHANGED=true
        echo "[$(date '+%H:%M:%S')] 更新: 广东日前电价预测.xlsx" >> "$LOG_FILE"
    fi
fi

# 3. 同步检修数据（最近14天 + 明天，覆盖D+1预测）
mkdir -p disclosure
for i in $(seq -1 13); do
    D=$(date -v+${i}d '+%Y-%m-%d')
    SRC="$SRC_DISCLOSURE/信息披露查询预测信息($D).xlsx"
    DST="disclosure/信息披露查询预测信息($D).xlsx"
    if [ -f "$SRC" ]; then
        if [ ! -f "$DST" ] || ! cmp -s "$SRC" "$DST"; then
            cp "$SRC" "$DST"
            git add "$DST"
            CHANGED=true
            echo "[$(date '+%H:%M:%S')] 更新: $DST" >> "$LOG_FILE"
        fi
    fi
done

# 4. 推送
if [ "$CHANGED" = true ]; then
    DATE_STR=$(date '+%Y-%m-%d')
    git commit -m "data: ${DATE_STR} 更新电价+检修数据"
    git push origin main >> "$LOG_FILE" 2>&1
    echo "[$(date '+%H:%M:%S')] ✅ 推送成功" >> "$LOG_FILE"
else
    echo "[$(date '+%H:%M:%S')] 数据无变化，跳过" >> "$LOG_FILE"
fi
