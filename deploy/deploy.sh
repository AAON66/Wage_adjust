#!/bin/bash
# ============================================================
# 调薪平台一键部署脚本
# 目标服务器: 10.0.0.60
# 不影响已有服务，使用独立端口和独立 Nginx 配置
# ============================================================
set -e

# ---------- 配置区域 ----------
APP_NAME="wage-adjust"
APP_DIR="/opt/${APP_NAME}"
BACKEND_PORT=8011
FRONTEND_PORT=8080    # Nginx 对外端口，确认不与已有服务冲突
PYTHON_VERSION="python3"
NODE_VERSION="18"     # 需要 Node.js >= 18

echo "=========================================="
echo "  调薪平台部署脚本"
echo "=========================================="

# ---------- 1. 系统依赖 ----------
echo "[1/8] 安装系统依赖..."
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip nginx redis-server git curl

# 检查 Node.js
if ! command -v node &> /dev/null || [ "$(node -v | cut -d. -f1 | tr -d 'v')" -lt 18 ]; then
    echo "  安装 Node.js ${NODE_VERSION}..."
    curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash -
    apt-get install -y -qq nodejs
fi

echo "  Python: $(${PYTHON_VERSION} --version)"
echo "  Node: $(node --version)"
echo "  npm: $(npm --version)"

# ---------- 2. 创建应用目录 ----------
echo "[2/8] 创建应用目录..."
mkdir -p ${APP_DIR}

# 如果代码已存在则更新，否则需要手动上传
if [ ! -f "${APP_DIR}/requirements.txt" ]; then
    echo "  请先将项目代码上传到 ${APP_DIR}"
    echo "  可以使用: scp -r ./* root@10.0.0.60:${APP_DIR}/"
    echo "  或者使用 git clone"
    exit 1
fi

# ---------- 3. 后端环境 ----------
echo "[3/8] 配置后端 Python 环境..."
cd ${APP_DIR}
${PYTHON_VERSION} -m venv .venv
source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
pip install gunicorn -q

# ---------- 4. 配置 .env ----------
echo "[4/8] 检查 .env 配置..."
if [ ! -f "${APP_DIR}/.env" ]; then
    cp ${APP_DIR}/.env.example ${APP_DIR}/.env
    # 生成安全密钥
    JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    API_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    ENCRYPTION_KEY=$(python3 -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())")
    sed -i "s|JWT_SECRET_KEY=change_me|JWT_SECRET_KEY=${JWT_SECRET}|" ${APP_DIR}/.env
    sed -i "s|PUBLIC_API_KEY=your_public_api_key|PUBLIC_API_KEY=${API_KEY}|" ${APP_DIR}/.env
    sed -i "s|NATIONAL_ID_ENCRYPTION_KEY=|NATIONAL_ID_ENCRYPTION_KEY=${ENCRYPTION_KEY}|" ${APP_DIR}/.env
    # 添加 CORS 配置（包含服务器 IP）
    sed -i "s|BACKEND_CORS_ORIGINS=.*|BACKEND_CORS_ORIGINS=[\"http://10.0.0.60:${FRONTEND_PORT}\",\"http://localhost:${FRONTEND_PORT}\"]|" ${APP_DIR}/.env
    echo ""
    echo "  ⚠️  已生成 .env 文件，请手动编辑以下配置："
    echo "     - DATABASE_URL（数据库连接）"
    echo "     - DEEPSEEK_API_KEY（AI 服务密钥）"
    echo "     - REDIS_URL（如非默认地址）"
    echo "  文件位置: ${APP_DIR}/.env"
    echo ""
fi

# ---------- 5. 创建上传目录 ----------
echo "[5/8] 创建上传目录..."
mkdir -p ${APP_DIR}/uploads

# ---------- 6. 前端构建 ----------
echo "[6/8] 构建前端..."
cd ${APP_DIR}/frontend
npm install --legacy-peer-deps
# 设置 API 地址为服务器地址
VITE_API_BASE_URL="http://10.0.0.60:${FRONTEND_PORT}/api/v1" npm run build
echo "  前端构建完成: ${APP_DIR}/frontend/dist/"

# ---------- 7. 配置 Systemd ----------
echo "[7/8] 配置 Systemd 服务..."

# 后端服务
cat > /etc/systemd/system/${APP_NAME}-backend.service << 'UNIT'
[Unit]
Description=Wage Adjust Backend (FastAPI)
After=network.target redis-server.service
Wants=redis-server.service

[Service]
Type=notify
User=root
Group=root
WorkingDirectory=/opt/wage-adjust
Environment="PATH=/opt/wage-adjust/.venv/bin:/usr/local/bin:/usr/bin"
ExecStart=/opt/wage-adjust/.venv/bin/gunicorn backend.app.main:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers 4 \
    --bind 127.0.0.1:8011 \
    --timeout 120 \
    --access-logfile /var/log/wage-adjust/access.log \
    --error-logfile /var/log/wage-adjust/error.log
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

# Celery Worker 服务
cat > /etc/systemd/system/${APP_NAME}-celery.service << 'UNIT'
[Unit]
Description=Wage Adjust Celery Worker
After=network.target redis-server.service
Wants=redis-server.service

[Service]
Type=forking
User=root
Group=root
WorkingDirectory=/opt/wage-adjust
Environment="PATH=/opt/wage-adjust/.venv/bin:/usr/local/bin:/usr/bin"
ExecStart=/opt/wage-adjust/.venv/bin/celery -A backend.app.celery_app worker \
    --loglevel=info \
    --logfile=/var/log/wage-adjust/celery.log \
    --detach
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
UNIT

# 创建日志目录
mkdir -p /var/log/${APP_NAME}

# ---------- 8. 配置 Nginx ----------
echo "[8/8] 配置 Nginx..."

cat > /etc/nginx/sites-available/${APP_NAME} << NGINX
# 调薪平台 - 独立端口，不影响已有服务
server {
    listen ${FRONTEND_PORT};
    server_name 10.0.0.60;

    # 前端静态文件
    root ${APP_DIR}/frontend/dist;
    index index.html;

    # 前端路由 - SPA fallback
    location / {
        try_files \$uri \$uri/ /index.html;
    }

    # 后端 API 反向代理
    location /api/ {
        proxy_pass http://127.0.0.1:${BACKEND_PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # 文件上传大小限制
        client_max_body_size 200M;

        # 超时设置（AI 调用可能较慢）
        proxy_read_timeout 300s;
        proxy_connect_timeout 10s;
        proxy_send_timeout 300s;
    }

    # 静态文件缓存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    access_log /var/log/nginx/${APP_NAME}-access.log;
    error_log /var/log/nginx/${APP_NAME}-error.log;
}
NGINX

# 启用站点（不影响 default 或其他已有配置）
ln -sf /etc/nginx/sites-available/${APP_NAME} /etc/nginx/sites-enabled/${APP_NAME}

# 测试 Nginx 配置
nginx -t

# ---------- 启动服务 ----------
echo ""
echo "=========================================="
echo "  启动服务"
echo "=========================================="

systemctl daemon-reload
systemctl enable redis-server
systemctl start redis-server

systemctl enable ${APP_NAME}-backend
systemctl start ${APP_NAME}-backend

systemctl enable ${APP_NAME}-celery
systemctl start ${APP_NAME}-celery

systemctl reload nginx

echo ""
echo "=========================================="
echo "  部署完成！"
echo "=========================================="
echo ""
echo "  前端访问地址: http://10.0.0.60:${FRONTEND_PORT}"
echo "  后端 API 地址: http://10.0.0.60:${FRONTEND_PORT}/api/v1"
echo ""
echo "  管理命令："
echo "    查看后端状态:  systemctl status ${APP_NAME}-backend"
echo "    查看后端日志:  journalctl -u ${APP_NAME}-backend -f"
echo "    重启后端:      systemctl restart ${APP_NAME}-backend"
echo "    查看 Celery:   systemctl status ${APP_NAME}-celery"
echo "    查看 Nginx:    systemctl status nginx"
echo ""
echo "  ⚠️  请确认："
echo "    1. 编辑 /opt/wage-adjust/.env 配置数据库和 DeepSeek API Key"
echo "    2. 配置完成后重启: systemctl restart ${APP_NAME}-backend"
echo "    3. 确认防火墙已开放端口 ${FRONTEND_PORT}"
echo ""
