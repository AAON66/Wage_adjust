#!/bin/bash
# 部署调薪间隔修复到服务器
# 使用方法：将此脚本上传到服务器并执行

set -e

echo "=== 开始部署调薪间隔修复 ==="

cd /root/Wage_adjust

echo "1. 拉取最新代码..."
git pull origin master

echo "2. 检查Python语法..."
source .venv/bin/activate
python -c "from backend.app.services.feishu_service import FeishuService; print('✓ feishu_service.py 语法正确')"
python -c "from backend.app.services.eligibility_service import EligibilityService; print('✓ eligibility_service.py 语法正确')"

echo "3. 重启后端服务..."
pkill -f gunicorn || true
sleep 2
cd /root/Wage_adjust
source .venv/bin/activate
nohup gunicorn -c gunicorn.conf.py backend.app.main:app > /tmp/gunicorn.log 2>&1 &
sleep 3

echo "4. 检查后端服务状态..."
if pgrep -f gunicorn > /dev/null; then
    echo "✓ 后端服务已启动"
else
    echo "✗ 后端服务启动失败，查看日志："
    tail -20 /tmp/gunicorn.log
    exit 1
fi

echo "5. 重新构建前端..."
cd /root/Wage_adjust/frontend
npm run build

echo ""
echo "=== 部署完成 ==="
echo ""
echo "修改内容："
echo "1. sync_hire_info 现在支持同步'历史调薪日期'字段"
echo "2. 调薪间隔计算优先使用 Employee.last_salary_adjustment_date"
echo "3. 前端入职信息同步面板增加 last_salary_adjustment_date 字段"
echo ""
echo "使用方法："
echo "在'调薪资格'页面，使用'入职信息'同步类型"
echo "将飞书表格的'历史调薪日期'字段映射到 last_salary_adjustment_date"
echo "同步后，调薪间隔将使用正确的 2025-10-01 日期"
