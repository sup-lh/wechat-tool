#!/bin/bash

# 微信公众号工具部署脚本 🎮
# 适用于 hl.aismrti.com 域名部署

# 设置严格错误处理
set -e  # 命令失败时立即退出
set -u  # 使用未定义变量时退出
set -o pipefail  # 管道中任何命令失败都会导致整个管道失败

# 部署配置
REMOTE_HOST="39.108.136.240"
REMOTE_USER="root"
REMOTE_DIR="/www/jar/wx_tool"
SERVICE_NAME="wechat-bot"
APP_PORT="9595"
CONFIG_NAME="测试公众号"
DOMAIN="hl.aismrti.com"

# 颜色输出函数
red() { echo -e "\033[31m$1\033[0m"; }
green() { echo -e "\033[32m$1\033[0m"; }
yellow() { echo -e "\033[33m$1\033[0m"; }
blue() { echo -e "\033[34m$1\033[0m"; }

# 错误处理函数
error_exit() {
    red "❌ 错误: $1"
    exit 1
}

# 成功输出函数
success() {
    green "✅ $1"
}

# 信息输出函数
info() {
    blue "ℹ️  $1"
}

# 警告输出函数
warning() {
    yellow "⚠️  $1"
}

echo "🚀 开始部署微信公众号工具到 ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}"

# 步骤1: 创建远程目录
info "步骤1: 创建远程目录..."
ssh ${REMOTE_USER}@${REMOTE_HOST} "mkdir -p ${REMOTE_DIR}" || error_exit "创建远程目录失败"
success "远程目录创建完成"

# 步骤2: 停止现有服务
info "步骤2: 停止现有服务..."
ssh ${REMOTE_USER}@${REMOTE_HOST} "
    # 停止 systemd 服务（如果存在）
    systemctl stop ${SERVICE_NAME} 2>/dev/null || true
    # 停止任何运行中的微信服务
    pkill -f 'python.*main.py.*server' || true
    sleep 2
" || warning "停止服务时出现警告，继续部署..."
success "现有服务已停止"

# 步骤3: 备份现有配置
info "步骤3: 备份现有配置..."
ssh ${REMOTE_USER}@${REMOTE_HOST} "
    if [ -f ${REMOTE_DIR}/wx_config.json ]; then
        cp ${REMOTE_DIR}/wx_config.json ${REMOTE_DIR}/wx_config.json.backup.\$(date +%Y%m%d_%H%M%S)
        echo '备份配置文件完成'
    fi
" || warning "配置备份失败，继续部署..."

# 步骤4: 上传文件（排除不需要的文件和目录）
info "步骤4: 上传文件到远程服务器..."
rsync -av \
  --exclude='venv' \
  --exclude='env' \
  --exclude='.venv' \
  --exclude='.git' \
  --exclude='.DS_Store' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='*.log' \
  --exclude='.claude' \
  --exclude='.cursor' \
  --exclude='spider_data' \
  --exclude='cookies.json' \
  --exclude='cookies_backup.json' \
  --exclude='captcha.jpg' \
  --exclude='demo.py' \
  --exclude='*.backup.*' \
  ./* ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}/ || error_exit "文件上传失败"
success "文件上传完成"

# 步骤5: 服务器环境配置
info "步骤5: 配置服务器环境..."
ssh ${REMOTE_USER}@${REMOTE_HOST} "
    cd ${REMOTE_DIR}

    # 创建必要目录
    mkdir -p logs

    # 检查 Python3 是否安装
    if ! command -v python3 &> /dev/null; then
        echo '正在安装 Python3...'
        apt update && apt install -y python3 python3-pip python3-venv
    fi

    # 创建虚拟环境
    if [ ! -d venv ]; then
        echo '创建 Python 虚拟环境...'
        python3 -m venv venv
    fi

    # 激活虚拟环境并安装依赖
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt

    echo '服务器环境配置完成'
" || error_exit "服务器环境配置失败"
success "服务器环境配置完成"

# 步骤6: 创建 systemd 服务文件
info "步骤6: 创建系统服务..."
ssh ${REMOTE_USER}@${REMOTE_HOST} "
    cat > /etc/systemd/system/${SERVICE_NAME}.service << EOF
[Unit]
Description=WeChat Bot Message Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${REMOTE_DIR}
Environment=PATH=${REMOTE_DIR}/venv/bin
ExecStart=${REMOTE_DIR}/venv/bin/python main.py server -n \"${CONFIG_NAME}\" -d \"${DOMAIN}\" -p ${APP_PORT}
Restart=always
RestartSec=10
StandardOutput=append:${REMOTE_DIR}/logs/wechat.log
StandardError=append:${REMOTE_DIR}/logs/wechat.error.log

[Install]
WantedBy=multi-user.target
EOF

    # 重新加载 systemd
    systemctl daemon-reload
    systemctl enable ${SERVICE_NAME}

    echo '系统服务创建完成'
" || error_exit "系统服务创建失败"
success "系统服务创建完成"

# 步骤7: 检查配置并启动服务
info "步骤7: 启动微信服务..."
ssh ${REMOTE_USER}@${REMOTE_HOST} "
    cd ${REMOTE_DIR}
    source venv/bin/activate

    # 检查配置是否存在
    if [ ! -f wx_config.json ]; then
        echo '警告: wx_config.json 不存在，请手动配置'
        echo '使用命令: python main.py bind -n \"${CONFIG_NAME}\" -a \"your_appid\" -s \"your_secret\" -t \"suplin123123\"'
    else
        echo '发现配置文件 wx_config.json'
        python main.py list
    fi

    # 启动服务
    systemctl start ${SERVICE_NAME}
    sleep 3

    # 检查服务状态
    if systemctl is-active --quiet ${SERVICE_NAME}; then
        echo '✅ 微信服务启动成功'
        systemctl status ${SERVICE_NAME} --no-pager -l
    else
        echo '❌ 微信服务启动失败'
        systemctl status ${SERVICE_NAME} --no-pager -l
        exit 1
    fi
" || error_exit "启动微信服务失败"

# 步骤8: 验证部署结果
info "步骤8: 验证部署结果..."
sleep 5
ssh ${REMOTE_USER}@${REMOTE_HOST} "
    cd ${REMOTE_DIR}

    # 检查服务状态
    if systemctl is-active --quiet ${SERVICE_NAME}; then
        echo '🎉 服务运行正常'
    else
        echo '❌ 服务未运行'
        exit 1
    fi

    # 检查端口监听
    if netstat -tlnp | grep :${APP_PORT} > /dev/null; then
        echo '✅ 端口 ${APP_PORT} 监听正常'
    else
        echo '⚠️  端口 ${APP_PORT} 未监听'
    fi

    # 测试健康检查（如果可以访问）
    if curl -s http://localhost:${APP_PORT}/health > /dev/null; then
        echo '✅ 健康检查通过'
    else
        echo 'ℹ️  健康检查暂时无法访问（可能需要配置反向代理）'
    fi
" || warning "验证过程出现警告"

success "🎉 微信公众号工具部署完成！"

echo ""
info "📋 部署信息总结:"
echo "  🖥️  服务器: ${REMOTE_HOST}"
echo "  📁 目录: ${REMOTE_DIR}"
echo "  🚀 服务: ${SERVICE_NAME}"
echo "  🌐 域名: https://${DOMAIN}"
echo "  🔌 端口: ${APP_PORT}"
echo ""
info "🔧 常用命令:"
echo "  查看服务状态: ssh ${REMOTE_USER}@${REMOTE_HOST} 'systemctl status ${SERVICE_NAME}'"
echo "  查看实时日志: ssh ${REMOTE_USER}@${REMOTE_HOST} 'journalctl -u ${SERVICE_NAME} -f'"
echo "  重启服务: ssh ${REMOTE_USER}@${REMOTE_HOST} 'systemctl restart ${SERVICE_NAME}'"
echo "  停止服务: ssh ${REMOTE_USER}@${REMOTE_HOST} 'systemctl stop ${SERVICE_NAME}'"
echo ""
warning "⚠️  下一步操作:"
echo "  1. 配置 Nginx 反向代理（参考 deployment_guide.md）"
echo "  2. 在微信公众平台完成 URL 验证"
echo "  3. 测试消息收发功能"
echo ""
success "嘿嘿~ 部署完成！微信公众号机器人已经准备就绪啦～ (´∀｀) 💖"