#!/bin/bash
# 管理后台更新脚本

set -e

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

echo "=== 更新管理后台 ==="

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_DIR="$(dirname "$SERVER_DIR")"

log_info "项目目录: $PROJECT_DIR"

# 1. 备份当前版本
log_info "备份当前版本..."
sudo cp -r /var/www/musicqr /var/www/musicqr_backup_$(date +%Y%m%d_%H%M%S)

# 2. 复制新代码
log_info "复制新代码..."
sudo cp -r "$SERVER_DIR"/* /var/www/musicqr/

# 3. 设置权限
log_info "设置权限..."
sudo chown -R musicqr:musicqr /var/www/musicqr

# 4. 安装新依赖（如果需要）
log_info "检查依赖..."
cd /var/www/musicqr
source venv/bin/activate

# 检查是否需要安装psutil
if ! python3 -c "import psutil" 2>/dev/null; then
    log_info "安装psutil..."
    pip install psutil
fi

# 5. 重启服务
log_info "重启API服务..."
sudo systemctl restart musicqr-api

# 6. 检查服务状态
log_info "检查服务状态..."
sleep 3

if sudo systemctl is-active --quiet musicqr-api; then
    log_success "API服务重启成功"
else
    echo "❌ API服务重启失败"
    sudo systemctl status musicqr-api --no-pager
    exit 1
fi

# 7. 测试管理后台
log_info "测试管理后台..."
if curl -s http://localhost/admin >/dev/null; then
    log_success "管理后台访问正常"
else
    echo "⚠️ 管理后台访问可能有问题"
fi

log_success "管理后台更新完成！"
echo
echo "=== 访问信息 ==="
echo "管理后台: https://verify.yuzeguitar.me/admin"
echo "默认账号: admin"
echo "默认密码: musicqr2024"
echo
echo "=== 自定义管理员账号 ==="
echo "编辑 /var/www/musicqr/.env 文件："
echo "ADMIN_USERNAME=your_admin"
echo "ADMIN_PASSWORD=your_password"
echo "然后重启服务: sudo systemctl restart musicqr-api"
echo
