#!/bin/bash
# ============================================================
# 电力市场数据自动同步到 GitHub
# 用法: ./sync_data.sh
# 定时: launchd 每天 09:00 自动执行
# ============================================================

REPO_DIR="/Users/duchaochao/Desktop/power_market_dashboard"
LOG_FILE="$REPO_DIR/sync_data.log"
SRC_DISCLOSURE="$HOME/Desktop/能源电力资料/日前训练数据/信息披露日前"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始同步..." >> "$LOG_FILE"
cd "$REPO_DIR" || exit 1

CHANGED=false

# 1. 同步电价数据文件
for f in "日前节点电价.xlsx" "广东日前电价预测.xlsx"; do
    if [ -f "$f" ]; then
        if ! git diff --quiet "$f" 2>/dev/null; then
            git add "$f"
            CHANGED=true
            echo "[$(date '+%H:%M:%S')] 更新: $f" >> "$LOG_FILE"
        fi
    fi
done

# 2. 同步检修数据（复制最近7天到仓库 disclosure/ 目录）
mkdir -p disclosure
for i in $(seq 0 6); do
    D=$(date -v-${i}d '+%Y-%m-%d')
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

# 3. 推送
if [ "$CHANGED" = true ]; then
    DATE_STR=$(date '+%Y-%m-%d')
    git commit -m "data: ${DATE_STR} 更新电价+检修数据"
    git push origin main >> "$LOG_FILE" 2>&1
    echo "[$(date '+%H:%M:%S')] ✅ 推送成功" >> "$LOG_FILE"
else
    echo "[$(date '+%H:%M:%S')] 数据无变化，跳过" >> "$LOG_FILE"
fi
