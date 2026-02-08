#!/bin/bash
# -*- coding: utf-8 -*-
"""
12306 抢票 Agent - 一键安装脚本

⚠️⚠️⚠️ 重要警告 ⚠️⚠️⚠️

1. 本工具仅供学习研究使用
2. 使用本工具存在账号被封禁的风险
3. 自动化操作可能违反12306服务条款
4. 请于24小时内删除本工具
5. 不保证抢票成功

使用即表示您已了解并同意以上声明

功能：
- 自动下载项目到本地
- 安装依赖
- 配置账户
- 启动监控

使用方法：
    chmod +x install.sh
    ./install.sh

作者: OpenClaw
版本: v2.0
"""

set -e  # 遇错即停

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目配置
PROJECT_NAME="12306-ticket-bot"
GIT_REPO="https://github.com/openclaw/12306-ticket-bot.git"
INSTALL_DIR="$HOME/.12306-bot"

echo_step() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

echo_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

echo_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

echo_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 检查系统
check_system() {
    echo_step "检查系统环境"
    
    # 检查 Python
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1)
        echo_success "Python: $PYTHON_VERSION"
    else
        echo_error "未安装 Python 3，请先安装 Python 3.8+"
        exit 1
    fi
    
    # 检查 pip
    if command -v pip3 &> /dev/null; then
        echo_success "pip3 已安装"
    else
        echo_warning "未安装 pip3，尝试安装..."
        python3 -m ensurepip --default-pip 2>/dev/null || true
    fi
    
    # 检查 git
    if command -v git &> /dev/null; then
        echo_success "git 已安装"
    else
        echo_warning "未安装 git，将使用 zip 下载"
    fi
}

# 下载项目
download_project() {
    echo_step "下载项目"
    
    if [ -d "$INSTALL_DIR" ]; then
        echo_warning "项目已存在，是否更新? (按 Enter 继续，Ctrl+C 取消)"
        read -r
    fi
    
    # 创建目录
    mkdir -p "$INSTALL_DIR"
    
    if command -v git &> /dev/null; then
        git clone "$GIT_REPO" "$INSTALL_DIR" || {
            echo_error "Git 克隆失败，尝试下载 zip..."
            TEMP_ZIP="/tmp/12306-bot.zip"
            curl -sL "https://github.com/openclaw/12306-ticket-bot/archive/refs/heads/main.zip" -o "$TEMP_ZIP"
            unzip -q "$TEMP_ZIP" -d /tmp
            mv /tmp/12306-ticket-bot-main/* "$INSTALL_DIR/"
            rm -rf /tmp/12306-ticket-bot-main "$TEMP_ZIP"
        }
        cd "$INSTALL_DIR"
        echo_success "项目已下载到: $INSTALL_DIR"
    else
        TEMP_ZIP="/tmp/12306-bot.zip"
        curl -sL "https://github.com/openclaw/12306-ticket-bot/archive/refs/heads/main.zip" -o "$TEMP_ZIP"
        
        if [ ! -f "$TEMP_ZIP" ]; then
            echo_error "下载失败，请手动下载项目"
            exit 1
        fi
        
        unzip -q "$TEMP_ZIP" -d /tmp
        mv /tmp/12306-ticket-bot-main/* "$INSTALL_DIR/"
        rm -rf /tmp/12306-ticket-bot-main "$TEMP_ZIP"
        
        echo_success "项目已下载到: $INSTALL_DIR"
    fi
}

# 安装依赖
install_dependencies() {
    echo_step "安装依赖"
    
    cd "$INSTALL_DIR"
    
    # 检查是否需要虚拟环境
    if [ -f "requirements.txt" ]; then
        echo "正在安装依赖..."
        pip3 install -r requirements.txt --quiet
        
        if [ $? -eq 0 ]; then
            echo_success "依赖安装完成"
        else
            echo_error "依赖安装失败"
            exit 1
        fi
    else
        echo_error "requirements.txt 不存在"
        exit 1
    fi
}

# 配置账户
configure_account() {
    echo_step "配置账户"
    
    cd "$INSTALL_DIR"
    
    # 检查配置文件
    if [ ! -f "config.yaml" ]; then
        if [ -f "config.example.yaml" ]; then
            cp config.example.yaml config.yaml
            echo_success "已创建 config.yaml"
        else
            echo_error "配置文件不存在"
            exit 1
        fi
    fi
    
    echo -e "\n${YELLOW}请按以下步骤配置账户:${NC}\n"
    echo "1. 打开浏览器，访问 https://12306.cn"
    echo "2. 登录您的 12306 账号"
    echo "3. 按 F12 打开开发者工具"
    echo "4. 切换到 Application/存储 标签"
    echo "5. 找到 Cookies -> https://12306.cn"
    echo "6. 复制以下 Cookie 值:"
    echo "   - _uab_guid"
    echo "   - _jc_save_fromStation"
    echo "   - _jc_save_toStation"  
    echo "   - _jc_save_fromDate"
    echo "   - _jc_save_toDate"
    echo "   - _jc_save_wfdc_flag"
    echo "   - JSESSIONID"
    echo ""
    echo "7. 编辑 config.yaml，填入 Cookie 值"
    echo ""
    echo -e "${BLUE}配置文件路径: $INSTALL_DIR/config.yaml${NC}\n"
    
    read -p "配置完成? 按 Enter 继续..."
}

# 配置通知
configure_notification() {
    echo_step "配置通知（可选）"
    
    cd "$INSTALL_DIR"
    
    echo -e "\n${YELLOW}PushPlus 微信通知配置:${NC}\n"
    echo "1. 微信关注 'PushPlus' 公众号"
    echo "2. 获取您的 token"
    echo "3. 在 config.yaml 中填入 token"
    echo ""
    echo -e "${BLUE}不想配置通知? 直接按 Enter 跳过${NC}\n"
    
    read -p "请输入 PushPlus Token (直接 Enter 跳过): " token
    
    if [ -n "$token" ]; then
        # 替换 config 中的 token
        sed -i "s/token:.*/token: \"$token\"/" config.yaml
        echo_success "PushPlus 配置完成"
    else
        echo_warning "跳过通知配置"
    fi
}

# 启动监控
start_monitor() {
    echo_step "启动监控"
    
    cd "$INSTALL_DIR"
    
    echo -e "\n${GREEN}选择运行模式:${NC}\n"
    echo "1. 前台运行 (适合测试)"
    echo "2. 后台运行 (适合长期监控)"
    echo "3. 安装系统服务 (Linux only，推荐)"
    echo ""
    
    read -p "请选择 [1/2/3]: " mode
    
    case $mode in
        1)
            echo -e "\n${GREEN}启动中... (按 Ctrl+C 停止)${NC}\n"
            python3 main.py --monitor
            ;;
        2)
            python3 local_monitor.py --daemon
            echo_success "监控已在后台启动"
            echo "查看日志: tail -f $INSTALL_DIR/logs/monitor_*.log"
            ;;
        3)
            if [ "$EUID" -ne 0 ]; then
                echo_warning "需要 root 权限安装服务"
                echo "请运行: sudo ./install.sh --install-service"
            else
                python3 local_monitor.py --install-service
                systemctl start 12306-monitor.service
                echo_success "服务已启动"
            fi
            ;;
        *)
            echo_error "无效选择"
            ;;
    esac
}

# 快速启动（用于 cron）
quick_start() {
    cd "$INSTALL_DIR"
    python3 main.py --monitor
}

# 显示帮助
show_help() {
    echo -e "\n${BLUE}使用说明:${NC}\n"
    echo "  ./install.sh          - 完整安装流程"
    echo "  ./install.sh --quick  - 快速启动（已安装时使用）"
    echo "  ./install.sh --status - 查看状态"
    echo "  ./install.sh --stop  - 停止监控"
    echo ""
    echo -e "${BLUE}手动命令:${NC}\n"
    echo "  # 前台运行"
    echo "  python3 main.py --monitor"
    echo ""
    echo "  # 后台运行"
    echo "  python3 local_monitor.py --daemon"
    echo ""
    echo "  # 查看日志"
    echo "  tail -f logs/monitor_*.log"
    echo ""
}

# 主程序
main() {
    echo -e "\n${BLUE}╔════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║     12306 抢票 Agent - 一键安装脚本       ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}\n"
    
    case "${1:-}" in
        --quick)
            quick_start
            ;;
        --status)
            cd "$INSTALL_DIR"
            python3 local_monitor.py --status
            ;;
        --stop)
            cd "$INSTALL_DIR"
            python3 local_monitor.py --stop
            ;;
        --help|-h)
            show_help
            ;;
        *)
            check_system
            download_project
            install_dependencies
            configure_account
            configure_notification
            start_monitor
            ;;
    esac
}

main "$@"
