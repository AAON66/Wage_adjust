#!/bin/bash
echo "=== 端口占用 ==="
ss -tlnp
echo "=== NGINX ==="
nginx -t 2>&1 || echo "nginx未安装"
echo "=== PYTHON ==="
python3 --version 2>&1 || echo "无python3"
echo "=== NODE ==="
node --version 2>&1 || echo "无node"
echo "=== REDIS ==="
redis-cli ping 2>&1 || echo "无redis"
echo "=== 磁盘 ==="
df -h /
echo "=== /opt目录 ==="
ls -la /opt/
echo "=== 已有systemd服务 ==="
systemctl list-units --type=service --state=running | grep -E "nginx|redis|mysql|postgres|node|pm2|gunicorn|uvicorn" || echo "无相关服务"
echo "=== DONE ==="
