# 生产环境部署指南 🚀

嘿嘿~ 这是一份详细的生产环境部署指南呢！(´∀｀) 💖

## 你的当前配置

根据你的微信公众平台设置：

- **URL**: `https://hl.aismrti.com`
- **Token**: `suplin123123`
- **EncodingAESKey**: `pchjOYZvGhPsPNCNTyh4F94vPLwyQYvZXS0TpWqH2Gc`
- **消息加解密方式**: 明文模式

## 🔧 部署方案

### 方案 1: 使用 Nginx 反向代理（推荐）

#### 1. 在服务器上运行微信服务

```bash
# 激活虚拟环境
source venv/bin/activate

# 启动服务器（内网端口）
python main.py server -n "测试公众号" -d "hl.aismrti.com" -p 8000
```

#### 2. 配置 Nginx

创建 Nginx 配置文件 `/etc/nginx/sites-available/wechat`:

```nginx
server {
    listen 443 ssl http2;
    server_name hl.aismrti.com;

    # SSL 证书配置
    ssl_certificate /path/to/your/certificate.crt;
    ssl_certificate_key /path/to/your/private.key;

    # SSL 设置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;

    # 微信回调路由
    location /wechat {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 健康检查
    location /health {
        proxy_pass http://127.0.0.1:8000;
    }
}

# HTTP 重定向到 HTTPS
server {
    listen 80;
    server_name hl.aismrti.com;
    return 301 https://$server_name$request_uri;
}
```

#### 3. 启用配置

```bash
# 创建软链接
sudo ln -s /etc/nginx/sites-available/wechat /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重启 Nginx
sudo systemctl reload nginx
```

### 方案 2: 使用 Systemd 服务（后台运行）

创建服务文件 `/etc/systemd/system/wechat-bot.service`:

```ini
[Unit]
Description=WeChat Bot Message Server
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/wx_wechat_tool
Environment=PATH=/path/to/wx_wechat_tool/venv/bin
ExecStart=/path/to/wx_wechat_tool/venv/bin/python main.py server -n "测试公众号" -d "hl.aismrti.com" -p 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用服务：

```bash
# 重新加载 systemd
sudo systemctl daemon-reload

# 启用服务
sudo systemctl enable wechat-bot

# 启动服务
sudo systemctl start wechat-bot

# 查看状态
sudo systemctl status wechat-bot

# 查看日志
sudo journalctl -u wechat-bot -f
```

### 方案 3: 使用 Docker（容器化部署）

创建 `Dockerfile`:

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# 复制项目文件
COPY requirements.txt .
COPY *.py .
COPY demo.jpg .
COPY wx_config.json .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "main.py", "server", "-n", "测试公众号", "-d", "hl.aismrti.com", "-p", "8000", "-h", "0.0.0.0"]
```

创建 `docker-compose.yml`:

```yaml
version: '3.8'

services:
  wechat-bot:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./wx_config.json:/app/wx_config.json
      - ./wechat_messages.log:/app/wechat_messages.log
    restart: unless-stopped
    environment:
      - PYTHONUNBUFFERED=1
```

部署命令：

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

## 🔒 安全建议

1. **防火墙设置**
   ```bash
   # 只允许 80 和 443 端口
   sudo ufw allow 80
   sudo ufw allow 443
   sudo ufw enable
   ```

2. **SSL 证书**
   - 使用 Let's Encrypt 免费证书
   - 或者使用云服务商提供的 SSL 证书

3. **日志监控**
   ```bash
   # 监控微信消息日志
   tail -f wechat_messages.log

   # 设置日志轮转
   sudo logrotate -d /etc/logrotate.conf
   ```

## 🚀 快速启动命令

根据你的具体需求，选择以下命令之一：

### 开发/测试环境
```bash
# 本地测试（HTTP）
python main.py server -n "测试公众号" -d "hl.aismrti.com" -p 8080

# 模拟生产环境（需要 SSL）
python main.py server -n "测试公众号" -d "hl.aismrti.com" -p 443
```

### 生产环境（推荐使用 Nginx 反向代理）
```bash
# 后台运行在内网端口
nohup python main.py server -n "测试公众号" -d "hl.aismrti.com" -p 8000 > wechat.log 2>&1 &
```

## 📋 部署检查清单

- [ ] 域名 DNS 解析到服务器 IP
- [ ] SSL 证书配置正确
- [ ] 防火墙允许 80/443 端口
- [ ] 微信服务器启动成功
- [ ] Nginx 反向代理配置
- [ ] 在微信公众平台完成 URL 验证
- [ ] 测试消息收发功能

## 🔧 故障排除

### URL 验证失败
1. 检查域名是否解析到正确IP
2. 确认 Token 配置一致
3. 检查服务器防火墙设置
4. 查看服务器日志: `tail -f wechat_messages.log`

### 消息接收不到
1. 确认服务器正常运行
2. 检查 Nginx 代理配置
3. 查看微信服务器日志
4. 测试健康检查接口: `https://hl.aismrti.com/health`

嘿嘿~ 按照这个指南一步步来，你的微信公众号机器人就能稳定运行啦！(´∀｀) 💖