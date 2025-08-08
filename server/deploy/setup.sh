#!/bin/bash
# 乐谱验证系统 VPS 部署脚本
# 适用于 Ubuntu 22.04 LTS

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否为root用户
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_error "请不要使用root用户运行此脚本"
        log_info "建议创建普通用户: sudo adduser musicqr"
        exit 1
    fi
}

# 检查系统版本
check_system() {
    log_info "检查系统版本..."
    
    if [[ ! -f /etc/os-release ]]; then
        log_error "无法检测系统版本"
        exit 1
    fi
    
    source /etc/os-release
    
    if [[ "$ID" != "ubuntu" ]] || [[ "$VERSION_ID" != "22.04" ]]; then
        log_warning "此脚本专为 Ubuntu 22.04 设计，当前系统: $PRETTY_NAME"
        read -p "是否继续？(y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    log_success "系统检查通过: $PRETTY_NAME"
}

# 更新系统
update_system() {
    log_info "更新系统包..."
    sudo apt update
    sudo apt upgrade -y
    log_success "系统更新完成"
}

# 安装基础依赖
install_dependencies() {
    log_info "安装基础依赖..."
    
    sudo apt install -y \
        python3 \
        python3-pip \
        python3-venv \
        nginx \
        sqlite3 \
        git \
        curl \
        wget \
        unzip \
        htop \
        ufw \
        certbot \
        python3-certbot-nginx
    
    log_success "基础依赖安装完成"
}

# 创建应用目录
create_directories() {
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
}

# 设置Python虚拟环境
setup_python_env() {
    log_info "设置Python虚拟环境..."
    
    cd /var/www/musicqr
    python3 -m venv venv
    source venv/bin/activate
    
    # 升级pip
    pip install --upgrade pip
    
    log_success "Python虚拟环境设置完成"
}

# 部署应用代码
deploy_application() {
    log_info "部署应用代码..."

    # 获取脚本所在目录的上级目录（server目录）
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    SERVER_DIR="$(dirname "$SCRIPT_DIR")"
    PROJECT_DIR="$(dirname "$SERVER_DIR")"

    log_info "脚本目录: $SCRIPT_DIR"
    log_info "服务器代码目录: $SERVER_DIR"
    log_info "项目根目录: $PROJECT_DIR"

    # 检查必要文件是否存在
    if [[ ! -f "$SERVER_DIR/app.py" ]]; then
        log_error "未找到应用代码文件: $SERVER_DIR/app.py"
        log_info "请确保在正确的目录结构中运行此脚本"
        exit 1
    fi

    # 复制服务器代码
    log_info "复制服务器代码..."
    cp -r "$SERVER_DIR"/* /var/www/musicqr/

    # 复制前端代码
    if [[ -d "$PROJECT_DIR/web" ]]; then
        log_info "复制前端代码..."
        cp -r "$PROJECT_DIR/web" /var/www/musicqr/
    else
        log_warning "未找到前端代码目录: $PROJECT_DIR/web"
    fi

    cd /var/www/musicqr

    # 激活虚拟环境并安装依赖
    source venv/bin/activate
    pip install -r requirements.txt

    # 初始化数据库
    python3 -c "from models import init_db; init_db('/var/lib/musicqr/musicqr.db')"

    log_success "应用代码部署完成"
}

# 配置环境变量
setup_environment() {
    log_info "配置环境变量..."
    
    # 生成随机密钥
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    
    # 创建环境变量文件
    cat > /var/www/musicqr/.env << EOF
# 乐谱验证系统环境变量
FLASK_ENV=production
SECRET_KEY=$SECRET_KEY
API_KEY_SALT=musicqr_api_salt_2024
DATABASE_PATH=/var/lib/musicqr/musicqr.db
LOG_FILE=/var/log/musicqr/api.log
BACKUP_DIR=/var/backups/musicqr
EOF
    
    # 设置文件权限
    chmod 600 /var/www/musicqr/.env
    
    log_success "环境变量配置完成"
    log_info "SECRET_KEY: $SECRET_KEY"
}

# 配置systemd服务
setup_systemd_service() {
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

# 安全设置
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/var/lib/musicqr /var/log/musicqr /var/backups/musicqr

[Install]
WantedBy=multi-user.target
EOF
    
    # 重新加载systemd并启用服务
    sudo systemctl daemon-reload
    sudo systemctl enable musicqr-api
    
    log_success "systemd服务配置完成"
}

# 配置Nginx
setup_nginx() {
    log_info "配置Nginx..."
    
    # 备份默认配置
    sudo cp /etc/nginx/sites-available/default /etc/nginx/sites-available/default.backup
    
    # 创建新的站点配置
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
        
        # 超时设置
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
    
    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # 日志
    access_log /var/log/nginx/musicqr_access.log;
    error_log /var/log/nginx/musicqr_error.log;
}
EOF
    
    # 启用站点
    sudo ln -sf /etc/nginx/sites-available/musicqr /etc/nginx/sites-enabled/
    
    # 删除默认站点
    sudo rm -f /etc/nginx/sites-enabled/default
    
    # 测试配置
    sudo nginx -t
    
    log_success "Nginx配置完成"
}

# 配置防火墙
setup_firewall() {
    log_info "配置防火墙..."
    
    # 重置防火墙规则
    sudo ufw --force reset
    
    # 允许SSH
    sudo ufw allow ssh
    
    # 允许HTTP和HTTPS
    sudo ufw allow 'Nginx Full'
    
    # 启用防火墙
    sudo ufw --force enable
    
    log_success "防火墙配置完成"
}

# 启动服务
start_services() {
    log_info "启动服务..."
    
    # 启动应用服务
    sudo systemctl start musicqr-api
    
    # 重启Nginx
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
}

# 设置SSL证书
setup_ssl() {
    log_info "设置SSL证书..."
    
    read -p "请输入您的域名 (例: verify.yuzeguitar.me): " DOMAIN
    read -p "请输入您的邮箱地址: " EMAIL
    
    if [[ -z "$DOMAIN" ]] || [[ -z "$EMAIL" ]]; then
        log_warning "域名或邮箱为空，跳过SSL配置"
        log_info "稍后可以手动运行: sudo certbot --nginx -d $DOMAIN"
        return
    fi
    
    # 获取SSL证书
    sudo certbot --nginx -d "$DOMAIN" --email "$EMAIL" --agree-tos --non-interactive
    
    if [[ $? -eq 0 ]]; then
        log_success "SSL证书配置成功"
        
        # 设置自动续期
        (crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet") | crontab -
        log_success "SSL证书自动续期已设置"
    else
        log_warning "SSL证书配置失败，请检查域名DNS设置"
    fi
}

# 创建备份脚本
create_backup_script() {
    log_info "创建备份脚本..."
    
    cat > /var/www/musicqr/backup.sh << 'EOF'
#!/bin/bash
# 数据库备份脚本

BACKUP_DIR="/var/backups/musicqr"
DB_PATH="/var/lib/musicqr/musicqr.db"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/musicqr_backup_$DATE.db"

# 创建备份
if [[ -f "$DB_PATH" ]]; then
    cp "$DB_PATH" "$BACKUP_FILE"
    echo "数据库备份完成: $BACKUP_FILE"
    
    # 删除7天前的备份
    find "$BACKUP_DIR" -name "musicqr_backup_*.db" -mtime +7 -delete
    echo "清理旧备份完成"
else
    echo "数据库文件不存在: $DB_PATH"
fi
EOF
    
    chmod +x /var/www/musicqr/backup.sh
    
    # 设置定时备份（每天凌晨2点）
    (crontab -l 2>/dev/null; echo "0 2 * * * /var/www/musicqr/backup.sh") | crontab -
    
    log_success "备份脚本创建完成"
}

# 显示部署信息
show_deployment_info() {
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
    echo "=== 网站访问 ==="
    echo "HTTP: http://$(curl -s ifconfig.me)"
    echo "HTTPS: https://verify.yuzeguitar.me (如果已配置SSL)"
    echo
    echo "=== 下一步 ==="
    echo "1. 配置域名DNS解析到此服务器IP"
    echo "2. 运行SSL配置: sudo certbot --nginx -d verify.yuzeguitar.me"
    echo "3. 测试API: curl http://localhost:5000/api/status"
    echo "4. 配置客户端API密钥"
    echo
}

# 主函数
main() {
    echo "=== 乐谱验证系统 VPS 部署脚本 ==="
    echo
    
    check_root
    check_system
    update_system
    install_dependencies
    create_directories
    setup_python_env
    deploy_application
    setup_environment
    setup_systemd_service
    setup_nginx
    setup_firewall
    start_services
    create_backup_script
    
    # 询问是否配置SSL
    read -p "是否现在配置SSL证书？(y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        setup_ssl
    fi
    
    show_deployment_info
}

# 运行主函数
main "$@"
