#!/bin/bash
# 乐谱验证系统快速部署脚本
# 简化版本，用于解决权限问题

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo "=== 乐谱验证系统快速部署 ==="

# 获取当前目录信息
CURRENT_DIR=$(pwd)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_DIR="$(dirname "$SERVER_DIR")"

log_info "当前目录: $CURRENT_DIR"
log_info "服务器代码目录: $SERVER_DIR"
log_info "项目根目录: $PROJECT_DIR"

# 1. 创建应用目录
log_info "创建应用目录..."
sudo mkdir -p /var/www/musicqr
sudo mkdir -p /var/lib/musicqr
sudo mkdir -p /var/log/musicqr
sudo mkdir -p /var/backups/musicqr

# 设置权限
sudo chown -R $USER:$USER /var/www/musicqr
sudo chown -R $USER:$USER /var/lib/musicqr
sudo chown -R $USER:$USER /var/log/musicqr
sudo chown -R $USER:$USER /var/backups/musicqr

log_success "目录创建完成"

# 2. 复制应用代码
log_info "复制应用代码..."

# 复制服务器代码
cp -r "$SERVER_DIR"/* /var/www/musicqr/

# 复制前端代码
if [[ -d "$PROJECT_DIR/web" ]]; then
    cp -r "$PROJECT_DIR/web" /var/www/musicqr/
    log_success "前端代码复制完成"
else
    log_error "未找到前端代码目录: $PROJECT_DIR/web"
    exit 1
fi

# 3. 设置Python环境
log_info "设置Python虚拟环境..."
cd /var/www/musicqr

if [[ ! -d "venv" ]]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

log_success "Python环境设置完成"

# 4. 配置环境变量
log_info "配置环境变量..."

SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

cat > /var/www/musicqr/.env << EOF
FLASK_ENV=production
SECRET_KEY=$SECRET_KEY
API_KEY_SALT=musicqr_api_salt_2024
DATABASE_PATH=/var/lib/musicqr/musicqr.db
LOG_FILE=/var/log/musicqr/api.log
BACKUP_DIR=/var/backups/musicqr
EOF

chmod 600 /var/www/musicqr/.env

log_success "环境变量配置完成"
log_info "SECRET_KEY: $SECRET_KEY"

# 5. 初始化数据库
log_info "初始化数据库..."
python3 -c "from models import init_db; init_db('/var/lib/musicqr/musicqr.db')"
log_success "数据库初始化完成"

# 6. 配置systemd服务
log_info "配置systemd服务..."

sudo tee /etc/systemd/system/musicqr-api.service > /dev/null << EOF
[Unit]
Description=Music QR Code Verification API
After=network.target

[Service]
Type=exec
User=$USER
Group=$USER
WorkingDirectory=/var/www/musicqr
Environment=PATH=/var/www/musicqr/venv/bin
EnvironmentFile=/var/www/musicqr/.env
ExecStart=/var/www/musicqr/venv/bin/gunicorn --bind 127.0.0.1:5000 --workers 2 app:app
Restart=always
RestartSec=3

NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/var/lib/musicqr /var/log/musicqr /var/backups/musicqr

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable musicqr-api

log_success "systemd服务配置完成"

# 7. 配置Nginx
log_info "配置Nginx..."

sudo tee /etc/nginx/sites-available/musicqr > /dev/null << 'EOF'
server {
    listen 80;
    server_name verify.yuzeguitar.me;
    
    # 静态文件
    location / {
        root /var/www/musicqr/web;
        try_files $uri $uri/ /index.html;
        
        # 缓存静态资源
        location ~* \.(css|js|png|jpg|jpeg|gif|ico|svg)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
    
    # API代理
    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
    
    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    access_log /var/log/nginx/musicqr_access.log;
    error_log /var/log/nginx/musicqr_error.log;
}
EOF

# 启用站点
sudo ln -sf /etc/nginx/sites-available/musicqr /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# 测试Nginx配置
sudo nginx -t

log_success "Nginx配置完成"

# 8. 启动服务
log_info "启动服务..."

sudo systemctl start musicqr-api
sudo systemctl restart nginx

# 检查服务状态
if sudo systemctl is-active --quiet musicqr-api; then
    log_success "API服务启动成功"
else
    log_error "API服务启动失败"
    sudo systemctl status musicqr-api
    exit 1
fi

if sudo systemctl is-active --quiet nginx; then
    log_success "Nginx服务启动成功"
else
    log_error "Nginx服务启动失败"
    sudo systemctl status nginx
    exit 1
fi

# 9. 创建管理脚本
log_info "创建管理脚本..."
cp deploy/管理脚本.sh /var/www/musicqr/manage.sh
chmod +x /var/www/musicqr/manage.sh

# 10. 显示部署信息
log_success "🎉 部署完成！"
echo
echo "=== 部署信息 ==="
echo "应用目录: /var/www/musicqr"
echo "数据库: /var/lib/musicqr/musicqr.db"
echo "日志目录: /var/log/musicqr"
echo "备份目录: /var/backups/musicqr"
echo
echo "=== 服务管理 ==="
echo "启动API服务: sudo systemctl start musicqr-api"
echo "停止API服务: sudo systemctl stop musicqr-api"
echo "重启API服务: sudo systemctl restart musicqr-api"
echo "查看API状态: sudo systemctl status musicqr-api"
echo "查看API日志: sudo journalctl -u musicqr-api -f"
echo
echo "=== 测试命令 ==="
echo "测试API: curl http://localhost:5000/api/status"
echo "测试网站: curl http://localhost/"
echo
echo "=== API密钥信息 ==="
echo "SECRET_KEY: $SECRET_KEY"
echo "请将此密钥配置到客户端中"
echo
echo "=== 下一步 ==="
echo "1. 配置域名DNS解析到此服务器IP: $(curl -s ifconfig.me 2>/dev/null || echo '获取IP失败')"
echo "2. 运行SSL配置: sudo certbot --nginx -d verify.yuzeguitar.me"
echo "3. 测试完整流程"
echo

log_success "快速部署完成！"
