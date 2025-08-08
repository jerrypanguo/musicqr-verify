#!/bin/bash
# 乐谱验证系统管理脚本
# 用于日常维护和管理

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 配置
APP_NAME="musicqr-api"
APP_DIR="/var/www/musicqr"
DB_PATH="/var/lib/musicqr/musicqr.db"
LOG_DIR="/var/log/musicqr"
BACKUP_DIR="/var/backups/musicqr"

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

# 显示帮助信息
show_help() {
    echo "乐谱验证系统管理脚本"
    echo
    echo "用法: $0 [命令]"
    echo
    echo "命令:"
    echo "  start       启动服务"
    echo "  stop        停止服务"
    echo "  restart     重启服务"
    echo "  status      查看服务状态"
    echo "  logs        查看实时日志"
    echo "  backup      备份数据库"
    echo "  restore     恢复数据库"
    echo "  update      更新应用"
    echo "  stats       显示统计信息"
    echo "  health      健康检查"
    echo "  cleanup     清理日志和备份"
    echo "  help        显示此帮助信息"
    echo
}

# 启动服务
start_service() {
    log_info "启动 $APP_NAME 服务..."
    sudo systemctl start $APP_NAME
    sudo systemctl start nginx
    
    if systemctl is-active --quiet $APP_NAME; then
        log_success "服务启动成功"
    else
        log_error "服务启动失败"
        exit 1
    fi
}

# 停止服务
stop_service() {
    log_info "停止 $APP_NAME 服务..."
    sudo systemctl stop $APP_NAME
    log_success "服务已停止"
}

# 重启服务
restart_service() {
    log_info "重启 $APP_NAME 服务..."
    sudo systemctl restart $APP_NAME
    sudo systemctl reload nginx
    
    if systemctl is-active --quiet $APP_NAME; then
        log_success "服务重启成功"
    else
        log_error "服务重启失败"
        exit 1
    fi
}

# 查看服务状态
show_status() {
    log_info "服务状态:"
    echo
    
    # API服务状态
    echo "=== API服务 ==="
    sudo systemctl status $APP_NAME --no-pager -l
    echo
    
    # Nginx状态
    echo "=== Nginx服务 ==="
    sudo systemctl status nginx --no-pager -l
    echo
    
    # 端口监听状态
    echo "=== 端口监听 ==="
    sudo netstat -tlnp | grep -E ':(80|443|5000)'
    echo
    
    # 磁盘使用情况
    echo "=== 磁盘使用 ==="
    df -h /var/www/musicqr /var/lib/musicqr /var/log/musicqr
    echo
}

# 查看实时日志
show_logs() {
    log_info "显示实时日志 (Ctrl+C 退出)..."
    sudo journalctl -u $APP_NAME -f --no-pager
}

# 备份数据库
backup_database() {
    log_info "备份数据库..."
    
    if [[ ! -f "$DB_PATH" ]]; then
        log_error "数据库文件不存在: $DB_PATH"
        exit 1
    fi
    
    # 创建备份目录
    mkdir -p "$BACKUP_DIR"
    
    # 生成备份文件名
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="$BACKUP_DIR/musicqr_backup_$TIMESTAMP.db"
    
    # 执行备份
    cp "$DB_PATH" "$BACKUP_FILE"
    
    # 压缩备份文件
    gzip "$BACKUP_FILE"
    BACKUP_FILE="$BACKUP_FILE.gz"
    
    log_success "数据库备份完成: $BACKUP_FILE"
    
    # 显示备份文件大小
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    log_info "备份文件大小: $BACKUP_SIZE"
    
    # 清理旧备份（保留最近7天）
    find "$BACKUP_DIR" -name "musicqr_backup_*.db.gz" -mtime +7 -delete
    log_info "已清理7天前的旧备份"
}

# 恢复数据库
restore_database() {
    log_info "可用的备份文件:"
    ls -la "$BACKUP_DIR"/musicqr_backup_*.db.gz 2>/dev/null || {
        log_error "没有找到备份文件"
        exit 1
    }
    
    echo
    read -p "请输入要恢复的备份文件名: " BACKUP_FILE
    
    if [[ ! -f "$BACKUP_DIR/$BACKUP_FILE" ]]; then
        log_error "备份文件不存在: $BACKUP_DIR/$BACKUP_FILE"
        exit 1
    fi
    
    log_warning "恢复数据库将覆盖当前数据，是否继续？"
    read -p "输入 'yes' 确认: " CONFIRM
    
    if [[ "$CONFIRM" != "yes" ]]; then
        log_info "操作已取消"
        exit 0
    fi
    
    # 停止服务
    stop_service
    
    # 备份当前数据库
    if [[ -f "$DB_PATH" ]]; then
        cp "$DB_PATH" "$DB_PATH.before_restore"
        log_info "当前数据库已备份为: $DB_PATH.before_restore"
    fi
    
    # 恢复数据库
    gunzip -c "$BACKUP_DIR/$BACKUP_FILE" > "$DB_PATH"
    
    # 启动服务
    start_service
    
    log_success "数据库恢复完成"
}

# 更新应用
update_application() {
    log_info "更新应用..."
    
    # 备份当前版本
    backup_database
    
    # 停止服务
    stop_service
    
    # 更新代码（假设使用git）
    cd "$APP_DIR"
    if [[ -d ".git" ]]; then
        git pull origin main
        log_success "代码更新完成"
    else
        log_warning "未检测到git仓库，请手动更新代码"
    fi
    
    # 更新Python依赖
    source venv/bin/activate
    pip install --upgrade -r requirements.txt
    log_success "依赖更新完成"
    
    # 启动服务
    start_service
    
    log_success "应用更新完成"
}

# 显示统计信息
show_stats() {
    log_info "系统统计信息:"
    echo
    
    # 数据库统计
    if [[ -f "$DB_PATH" ]]; then
        echo "=== 数据库统计 ==="
        sqlite3 "$DB_PATH" << 'EOF'
.mode column
.headers on
SELECT 
    COUNT(*) as total_codes,
    SUM(CASE WHEN activated = 1 THEN 1 ELSE 0 END) as activated_codes,
    ROUND(SUM(CASE WHEN activated = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as activation_rate
FROM auth_codes;

SELECT 
    DATE(activation_date) as date,
    COUNT(*) as activations
FROM auth_codes 
WHERE activated = 1 AND activation_date >= DATE('now', '-7 days')
GROUP BY DATE(activation_date)
ORDER BY date DESC;
EOF
        echo
    fi
    
    # 系统资源使用
    echo "=== 系统资源 ==="
    echo "CPU使用率:"
    top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1
    echo
    echo "内存使用:"
    free -h
    echo
    echo "磁盘使用:"
    df -h /
    echo
    
    # 日志文件大小
    echo "=== 日志文件 ==="
    du -sh "$LOG_DIR"/* 2>/dev/null || echo "无日志文件"
    echo
    
    # 备份文件
    echo "=== 备份文件 ==="
    ls -lah "$BACKUP_DIR"/*.gz 2>/dev/null | tail -5 || echo "无备份文件"
    echo
}

# 健康检查
health_check() {
    log_info "执行健康检查..."
    
    # 检查服务状态
    if ! systemctl is-active --quiet $APP_NAME; then
        log_error "API服务未运行"
        return 1
    fi
    
    if ! systemctl is-active --quiet nginx; then
        log_error "Nginx服务未运行"
        return 1
    fi
    
    # 检查端口监听
    if ! netstat -tln | grep -q ":5000"; then
        log_error "API端口5000未监听"
        return 1
    fi
    
    if ! netstat -tln | grep -q ":80"; then
        log_error "HTTP端口80未监听"
        return 1
    fi
    
    # 检查API响应
    if ! curl -s http://localhost:5000/api/status > /dev/null; then
        log_error "API健康检查失败"
        return 1
    fi
    
    # 检查数据库
    if [[ ! -f "$DB_PATH" ]]; then
        log_error "数据库文件不存在"
        return 1
    fi
    
    # 检查磁盘空间
    DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [[ $DISK_USAGE -gt 90 ]]; then
        log_warning "磁盘使用率过高: ${DISK_USAGE}%"
    fi
    
    log_success "健康检查通过"
}

# 清理日志和备份
cleanup() {
    log_info "清理旧文件..."
    
    # 清理日志文件（保留最近30天）
    find "$LOG_DIR" -name "*.log" -mtime +30 -delete
    
    # 清理备份文件（保留最近30天）
    find "$BACKUP_DIR" -name "*.gz" -mtime +30 -delete
    
    # 清理systemd日志
    sudo journalctl --vacuum-time=30d
    
    log_success "清理完成"
}

# 主函数
main() {
    case "${1:-help}" in
        start)
            start_service
            ;;
        stop)
            stop_service
            ;;
        restart)
            restart_service
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs
            ;;
        backup)
            backup_database
            ;;
        restore)
            restore_database
            ;;
        update)
            update_application
            ;;
        stats)
            show_stats
            ;;
        health)
            health_check
            ;;
        cleanup)
            cleanup
            ;;
        help|*)
            show_help
            ;;
    esac
}

# 运行主函数
main "$@"
