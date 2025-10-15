#!/bin/bash

# 下载速度测试工具 - Linux后台常驻运行脚本
# 支持启动、停止、重启、状态查看等功能

# 配置变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="speed_test"
APP_FILE="speed_test.py"
PID_FILE="/tmp/${APP_NAME}.pid"
LOG_FILE="/tmp/${APP_NAME}.log"
ERROR_LOG_FILE="/tmp/${APP_NAME}_error.log"
PORT=5000

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 检查Python环境
check_python() {
    if ! command -v python3 &> /dev/null; then
        print_error "未找到Python3，请先安装Python3"
        exit 1
    fi
    print_success "Python3环境检查通过"
}

# 检查Flask依赖
check_dependencies() {
    if ! python3 -c "import flask" &> /dev/null; then
        print_warning "Flask未安装，正在安装依赖包..."
        pip3 install -r requirements.txt
        if [ $? -ne 0 ]; then
            print_error "依赖安装失败，请手动运行: pip3 install -r requirements.txt"
            exit 1
        fi
    fi
    print_success "依赖检查通过"
}

# 检查端口是否被占用
check_port() {
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_warning "端口 $PORT 已被占用"
        return 1
    fi
    return 0
}

# 获取进程PID
get_pid() {
    if [ -f "$PID_FILE" ]; then
        cat "$PID_FILE"
    else
        echo ""
    fi
}

# 检查进程是否运行
is_running() {
    local pid=$(get_pid)
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

# 启动服务
start_service() {
    print_info "启动下载速度测试服务..."
    mkdir -p log
    
    # 检查是否已经在运行
    if is_running; then
        print_warning "服务已经在运行中 (PID: $(get_pid))"
        return 0
    fi
    
    # 检查端口
    if ! check_port; then
        print_error "端口 $PORT 被占用，请检查是否有其他服务在使用"
        return 1
    fi
    
    # 切换到脚本目录
    cd "$SCRIPT_DIR" || {
        print_error "无法切换到脚本目录: $SCRIPT_DIR"
        return 1
    }
    
    # 启动服务（后台运行）
    nohup python3 "$APP_FILE" > "$LOG_FILE" 2> "$ERROR_LOG_FILE" &
    local pid=$!
    
    # 保存PID
    echo $pid > "$PID_FILE"
    
    # 等待服务启动
    sleep 2
    
    # 检查是否启动成功
    if is_running; then
        print_success "服务启动成功！"
        print_info "PID: $pid"
        print_info "端口: $PORT"
        print_info "日志文件: $LOG_FILE"
        print_info "错误日志: $ERROR_LOG_FILE"
        print_info "访问地址: http://localhost:$PORT"
        echo ""
        print_info "使用以下命令管理服务:"
        echo "  停止服务: $0 stop"
        echo "  重启服务: $0 restart"
        echo "  查看状态: $0 status"
        echo "  查看日志: $0 logs"
    else
        print_error "服务启动失败"
        rm -f "$PID_FILE"
        return 1
    fi
}

# 停止服务
stop_service() {
    print_info "停止下载速度测试服务..."
    
    if ! is_running; then
        print_warning "服务未运行"
        rm -f "$PID_FILE"
        return 0
    fi
    
    local pid=$(get_pid)
    print_info "正在停止进程 $pid..."
    
    # 优雅停止
    kill -TERM "$pid" 2>/dev/null
    
    # 等待进程结束
    local count=0
    while kill -0 "$pid" 2>/dev/null && [ $count -lt 10 ]; do
        sleep 1
        count=$((count + 1))
    done
    
    # 如果还在运行，强制杀死
    if kill -0 "$pid" 2>/dev/null; then
        print_warning "强制停止进程..."
        kill -KILL "$pid" 2>/dev/null
        sleep 1
    fi
    
    # 清理PID文件
    rm -f "$PID_FILE"
    
    if ! kill -0 "$pid" 2>/dev/null; then
        print_success "服务已停止"
    else
        print_error "服务停止失败"
        return 1
    fi
}

# 重启服务
restart_service() {
    print_info "重启下载速度测试服务..."
    stop_service
    sleep 1
    start_service
}

# 查看服务状态
show_status() {
    print_info "服务状态检查..."
    echo ""
    
    if is_running; then
        local pid=$(get_pid)
        print_success "服务正在运行"
        echo "  PID: $pid"
        echo "  端口: $PORT"
        echo "  启动时间: $(ps -o lstart= -p $pid 2>/dev/null || echo '未知')"
        echo "  内存使用: $(ps -o rss= -p $pid 2>/dev/null | awk '{print $1/1024 " MB"}' || echo '未知')"
        echo "  访问地址: http://localhost:$PORT"
        
        # 检查端口监听
        if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
            print_success "端口 $PORT 正在监听"
        else
            print_warning "端口 $PORT 未在监听"
        fi
    else
        print_error "服务未运行"
        echo "  PID文件: $PID_FILE"
        echo "  日志文件: $LOG_FILE"
    fi
}

# 查看日志
show_logs() {
    local lines=${1:-50}
    print_info "显示最近 $lines 行日志..."
    echo ""
    
    if [ -f "$LOG_FILE" ]; then
        echo "=== 应用日志 ==="
        tail -n "$lines" "$LOG_FILE"
    else
        print_warning "日志文件不存在: $LOG_FILE"
    fi
    
    if [ -f "$ERROR_LOG_FILE" ] && [ -s "$ERROR_LOG_FILE" ]; then
        echo ""
        echo "=== 错误日志 ==="
        tail -n "$lines" "$ERROR_LOG_FILE"
    fi
}

# 实时查看日志
tail_logs() {
    print_info "实时查看日志 (按 Ctrl+C 退出)..."
    echo ""
    
    if [ -f "$LOG_FILE" ]; then
        tail -f "$LOG_FILE"
    else
        print_warning "日志文件不存在: $LOG_FILE"
    fi
}

# 安装为系统服务（可选）
install_service() {
    print_info "安装为系统服务..."
    
    # 检查是否为root用户
    if [ "$EUID" -ne 0 ]; then
        print_error "需要root权限来安装系统服务"
        echo "请使用: sudo $0 install"
        return 1
    fi
    
    # 创建systemd服务文件
    local service_file="/etc/systemd/system/${APP_NAME}.service"
    
    cat > "$service_file" << EOF
[Unit]
Description=Speed Test Web Application
After=network.target

[Service]
Type=simple
User=$SUDO_USER
WorkingDirectory=$SCRIPT_DIR
ExecStart=/usr/bin/python3 $SCRIPT_DIR/$APP_FILE
Restart=always
RestartSec=3
StandardOutput=append:$LOG_FILE
StandardError=append:$ERROR_LOG_FILE

[Install]
WantedBy=multi-user.target
EOF

    # 重新加载systemd
    systemctl daemon-reload
    
    # 启用服务
    systemctl enable "$APP_NAME"
    
    print_success "系统服务安装完成"
    print_info "使用以下命令管理服务:"
    echo "  启动: sudo systemctl start $APP_NAME"
    echo "  停止: sudo systemctl stop $APP_NAME"
    echo "  状态: sudo systemctl status $APP_NAME"
    echo "  日志: sudo journalctl -u $APP_NAME -f"
}

# 显示帮助信息
show_help() {
    echo "下载速度测试工具 - Linux后台运行脚本"
    echo ""
    echo "用法: $0 {start|stop|restart|status|logs|tail|install|help}"
    echo ""
    echo "命令:"
    echo "  start     - 启动服务（后台运行）"
    echo "  stop      - 停止服务"
    echo "  restart   - 重启服务"
    echo "  status    - 查看服务状态"
    echo "  logs      - 查看日志 (默认50行)"
    echo "  tail      - 实时查看日志"
    echo "  install   - 安装为系统服务 (需要root权限)"
    echo "  help      - 显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 start          # 启动服务"
    echo "  $0 logs 100       # 查看最近100行日志"
    echo "  sudo $0 install   # 安装为系统服务"
}

# 主函数
main() {
    # 检查环境
    check_python
    check_dependencies
    
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
            show_logs "$2"
            ;;
        tail)
            tail_logs
            ;;
        install)
            install_service
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "未知命令: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@"