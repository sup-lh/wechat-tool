# 微信公众号工具 🎮

呀~ 这是一个超级实用的微信公众号管理工具呢！(´∀｀) 💖

## 功能特性

- 🔗 **公众号绑定验证** - 验证AppID和AppSecret是否正确
- 💾 **本地配置管理** - 安全存储多个公众号配置
- 🎨 **自动生成素材** - 自动生成测试图片作为封面
- 📝 **草稿箱发布** - 一键发布文章到微信公众号草稿箱
- 🤖 **消息监听服务器** - 实时接收和自动回复用户消息
- ✅ **URL验证** - 自动处理微信服务器的URL有效性验证
- 💬 **智能回复** - 支持文本、图片等多种消息类型的自动回复

## 环境准备

### 1. 创建虚拟环境（推荐）

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
# 在 macOS/Linux 上：
source venv/bin/activate

# 在 Windows 上：
venv\Scripts\activate
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 退出虚拟环境（可选）

```bash
deactivate
```

## 使用方法

> 💡 **小提示**: 使用前请确保已激活虚拟环境哦～ `source venv/bin/activate`

### 1. 绑定公众号配置

```bash
# 基础绑定（仅用于草稿箱发布）
python main.py bind -n "我的公众号" -a "你的AppID" -s "你的AppSecret"

# 完整绑定（包含消息服务器Token）
python main.py bind -n "我的公众号" -a "你的AppID" -s "你的AppSecret" -t "你的Token"
```

### 2. 发布文章到草稿箱

```bash
python main.py publish -n "我的公众号" -t "文章标题" -c "文章内容"
```

### 3. 查看所有配置

```bash
python main.py list
```

### 4. 测试配置连接

```bash
python main.py test -n "我的公众号"
```

### 5. 删除配置

```bash
python main.py delete -n "我的公众号"
```

### 6. 启动消息监听服务器

```bash
# 使用默认端口5000启动
python main.py server -n "我的公众号"

# 自定义端口和地址
python main.py server -n "我的公众号" -p 8080 -h 127.0.0.1
```

## 命令详解

### bind 命令
绑定新的公众号配置，会自动验证AppID和AppSecret的有效性。

参数：
- `-n, --name`: 配置名称（必需）
- `-a, --appid`: 公众号AppID（必需）
- `-s, --secret`: 公众号AppSecret（必需）
- `-t, --token`: 消息服务器Token（可选，用于消息监听）

### publish 命令
发布文章到指定公众号的草稿箱。

参数：
- `-n, --name`: 使用的配置名称（必需）
- `-t, --title`: 文章标题（可选，默认为"测试文章"）
- `-c, --content`: 文章内容（可选，默认为测试内容）

### server 命令
启动消息监听服务器，接收微信用户发送的消息并自动回复。

参数：
- `-n, --name`: 使用的配置名称（必需）
- `-p, --port`: 服务器端口（可选，默认5000）
- `-h, --host`: 服务器地址（可选，默认0.0.0.0）

## 消息服务器配置

### 1. 微信公众平台设置

在「微信开发者平台 - 我的业务 - 公众号 - 消息与事件推送」中配置：

- **URL**: `http://你的域名或IP:端口/wechat`（例如：`http://example.com:5000/wechat`）
- **Token**: 与绑定时设置的Token一致
- **EncodingAESKey**: 可随机生成
- **消息加解密方式**: 建议选择"安全模式"

### 2. 支持的消息类型

- **文本消息**: 智能关键词回复
- **图片消息**: 自动确认收到
- **关注事件**: 欢迎消息

### 3. 内置回复功能

- 发送"你好"或"hello" → 问候回复
- 发送"帮助"或"help" → 功能列表
- 发送"时间"或"time" → 当前时间
- 发送图片 → 图片确认回复
- 关注公众号 → 欢迎消息

## 配置文件

配置信息存储在 `wx_config.json` 文件中，格式如下：

```json
{
  "我的公众号": {
    "appid": "wx1234567890",
    "secret": "abcdef1234567890",
    "token": "my_wechat_token"
  }
}
```

## 注意事项

1. 确保公众号已开通相关接口权限
2. 需要将服务器IP添加到公众号的白名单中
3. AppSecret和Token请妥善保管，不要泄露给他人
4. 草稿箱功能需要公众号具备相应权限
5. 消息服务器需要公网可访问的域名或IP
6. 建议在生产环境使用HTTPS和域名
7. 服务器启动后需要在微信公众平台完成URL验证

## 错误处理

- 如果绑定失败，请检查AppID和AppSecret是否正确
- 如果发布失败，请检查网络连接和公众号权限
- 如果URL验证失败，请检查Token是否与微信公众平台配置一致
- 如果消息服务器无法访问，请检查防火墙和端口设置
- 服务器日志保存在 `wechat_messages.log` 文件中
- 如果出现其他错误，请查看错误信息和日志进行相应处理

嘿嘿~ 使用愉快！(´∀｀) 💖