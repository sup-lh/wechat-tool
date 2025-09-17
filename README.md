# 微信公众号工具 🎮

呀~ 这是一个超级实用的微信公众号管理工具呢！(´∀｀) 💖

## 功能特性

- 🔗 **公众号绑定验证** - 验证AppID和AppSecret是否正确
- 💾 **本地配置管理** - 安全存储多个公众号配置
- 🎨 **自动生成素材** - 自动生成测试图片作为封面
- 📝 **草稿箱发布** - 一键发布文章到微信公众号草稿箱

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 1. 绑定公众号配置

```bash
python main.py bind -n "我的公众号" -a "你的AppID" -s "你的AppSecret"
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

## 命令详解

### bind 命令
绑定新的公众号配置，会自动验证AppID和AppSecret的有效性。

参数：
- `-n, --name`: 配置名称（必需）
- `-a, --appid`: 公众号AppID（必需）
- `-s, --secret`: 公众号AppSecret（必需）

### publish 命令
发布文章到指定公众号的草稿箱。

参数：
- `-n, --name`: 使用的配置名称（必需）
- `-t, --title`: 文章标题（可选，默认为"测试文章"）
- `-c, --content`: 文章内容（可选，默认为测试内容）

## 配置文件

配置信息存储在 `wx_config.json` 文件中，格式如下：

```json
{
  "我的公众号": {
    "appid": "wx1234567890",
    "secret": "abcdef1234567890"
  }
}
```

## 注意事项

1. 确保公众号已开通相关接口权限
2. 需要将服务器IP添加到公众号的白名单中
3. AppSecret请妥善保管，不要泄露给他人
4. 草稿箱功能需要公众号具备相应权限

## 错误处理

- 如果绑定失败，请检查AppID和AppSecret是否正确
- 如果发布失败，请检查网络连接和公众号权限
- 如果出现其他错误，请查看错误信息进行相应处理

嘿嘿~ 使用愉快！(´∀｀) 💖