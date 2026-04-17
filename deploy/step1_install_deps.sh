#!/bin/bash
set -e
echo "=== Step 1: 安装系统依赖 ==="

# 检查已有 Python 版本
echo "检查 Python..."
python3.11 --version 2>/dev/null && PYTHON=python3.11 || {
    python3.10 --version 2>/dev/null && PYTHON=python3.10 || {
        echo "安装 Python 3.11..."
        # TencentOS 基于 CentOS，使用 yum
        yum install -y epel-release 2>/dev/null || true
        # 尝试安装 python3.11
        yum install -y python3.11 python3.11-pip python3.11-devel 2>/dev/null || {
            echo "从 IUS/SCL 安装..."
            yum install -y centos-release-scl 2>/dev/null || true
            yum install -y python311 python311-pip python311-devel 2>/dev/null || {
                echo "编译安装 Python 3.11..."
                yum install -y gcc openssl-devel bzip2-devel libffi-devel zlib-devel readline-devel sqlite-devel wget make 2>/dev/null
                cd /tmp
                if [ ! -f Python-3.11.9.tgz ]; then
                    wget -q https://www.python.org/ftp/python/3.11.9/Python-3.11.9.tgz
                fi
                tar xzf Python-3.11.9.tgz
                cd Python-3.11.9
                ./configure --enable-optimizations --prefix=/usr/local 2>&1 | tail -3
                make -j$(nproc) 2>&1 | tail -3
                make altinstall 2>&1 | tail -3
                cd /
            }
        }
        PYTHON=python3.11
    }
}

echo "Python: $($PYTHON --version)"

# 安装 Redis
echo "安装 Redis..."
if ! command -v redis-server &>/dev/null; then
    yum install -y redis 2>/dev/null || {
        yum install -y epel-release && yum install -y redis
    }
fi
systemctl enable redis
systemctl start redis
echo "Redis: $(redis-cli ping)"

# 创建项目目录
echo "创建项目目录..."
mkdir -p /opt/wage-adjust
mkdir -p /var/log/wage-adjust

echo "=== Step 1 完成 ==="
echo "PYTHON_BIN=$PYTHON"
