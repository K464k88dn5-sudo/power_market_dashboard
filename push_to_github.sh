#!/bin/bash
# 定时推送到 GitHub（网络恢复后自动执行）
cd /Users/duchaochao/Desktop/power_market_dashboard

# 推送代码
git push origin main 2>&1
if [ $? -eq 0 ]; then
    echo "代码推送成功"
    
    # 推送标签
    git push origin v3.0.0 2>&1
    if [ $? -eq 0 ]; then
        echo "标签推送成功"
        echo "Done"
        
        # 推送成功后移除定时任务
        crontab -l 2>/dev/null | grep -v "push_to_github.sh" | crontab -
        echo "定时任务已移除"
    else
        echo "标签推送失败"
    fi
else
    echo "代码推送失败"
fi
