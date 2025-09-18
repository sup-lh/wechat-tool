#!/usr/bin/env python3
"""
微信消息指令处理器
将CLI功能转换为微信消息处理
"""
import re
import time
import os
from typing import Dict, Optional, Tuple, List
from config import ConfigManager
from wechat_api import WeChatAPI
import logging

logger = logging.getLogger(__name__)

class CommandProcessor:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.wechat_api = WeChatAPI()

        # 管理员会话状态 (用户ID -> 权限到期时间)
        self.admin_sessions = {}

        # 管理员密码 (生产环境应该从环境变量读取)
        self.admin_password = "admin123456"

        # 会话过期时间 (30分钟)
        self.session_timeout = 30 * 60

    def is_admin(self, user_id: str) -> bool:
        """检查用户是否有管理员权限"""
        if user_id not in self.admin_sessions:
            return False

        # 检查会话是否过期
        if time.time() > self.admin_sessions[user_id]:
            del self.admin_sessions[user_id]
            return False

        return True

    def grant_admin_access(self, user_id: str, password: str) -> bool:
        """验证管理员密码并授权"""
        if password == self.admin_password:
            # 授权30分钟
            self.admin_sessions[user_id] = time.time() + self.session_timeout
            logger.info(f"用户 {user_id} 获得管理员权限")
            return True
        return False

    def parse_command(self, content: str) -> Tuple[str, Dict]:
        """解析消息指令"""
        content = content.strip()

        # 检查是否是管理员指令
        if content.startswith('/'):
            return self._parse_admin_command(content)

        # 普通用户指令
        return self._parse_user_command(content)

    def _parse_admin_command(self, content: str) -> Tuple[str, Dict]:
        """解析管理员指令"""
        lines = content.split('\n')
        first_line = lines[0].strip()

        # 解析指令和参数
        parts = first_line.split(' ', 2)
        command = parts[0][1:]  # 去掉 /

        params = {}

        if command == 'admin':
            # /admin 密码
            if len(parts) > 1:
                params['password'] = parts[1]
            return command, params

        elif command == 'bind':
            # /bind 配置名称
            if len(parts) > 1:
                params['name'] = parts[1]

            # 解析多行参数
            for line in lines[1:]:
                line = line.strip()
                if ':' in line:
                    key, value = line.split(':', 1)
                    params[key.strip()] = value.strip()

            return command, params

        elif command == 'publish':
            # /publish 配置名称
            if len(parts) > 1:
                params['name'] = parts[1]

            # 解析多行参数
            for line in lines[1:]:
                line = line.strip()
                if ':' in line:
                    key, value = line.split(':', 1)
                    params[key.strip()] = value.strip()

            return command, params

        elif command in ['list', 'help']:
            return command, params

        elif command in ['delete', 'test']:
            # /delete 配置名称 或 /test 配置名称
            if len(parts) > 1:
                params['name'] = parts[1]
            return command, params

        return 'unknown', params

    def _parse_user_command(self, content: str) -> Tuple[str, Dict]:
        """解析用户指令"""
        content = content.strip()
        content_lower = content.lower()

        # 绑定格式：绑定 {appid} {secret} {昵称}
        bind_pattern = r'^绑定\s+([a-zA-Z0-9_]+)\s+([a-zA-Z0-9_]+)\s+(.+)$'
        bind_match = re.match(bind_pattern, content)
        if bind_match:
            appid, secret, nickname = bind_match.groups()
            return 'user_bind', {
                'appid': appid.strip(),
                'secret': secret.strip(),
                'nickname': nickname.strip()
            }

        # 简单绑定格式检测（格式错误提示）
        if content.startswith('绑定'):
            return 'user_bind_help', {}

        # 我的配置
        if content in ['我的配置', '配置列表', '我的账号', '查看配置']:
            return 'user_list_configs', {}

        # 测试格式：测试 {昵称}
        test_pattern = r'^测试\s+(.+)$'
        test_match = re.match(test_pattern, content)
        if test_match:
            nickname = test_match.group(1).strip()
            return 'user_test', {'nickname': nickname}

        # 发布格式：使用 {昵称} 发布 {标题} {内容} [作者]
        publish_pattern = r'^使用\s+(.+?)\s+发布\s+(.+?)\s+(.+?)(?:\s+(.+?))?$'
        publish_match = re.match(publish_pattern, content)
        if publish_match:
            nickname, title, content_text, author = publish_match.groups()
            # 如果没有提供作者，使用默认值
            if not author:
                author = "不存在的画廊"
            return 'user_publish', {
                'nickname': nickname.strip(),
                'title': title.strip(),
                'content': content_text.strip(),
                'author': author.strip() if author else "不存在的画廊"
            }

        # 发布格式检测（格式错误提示）
        if '发布' in content and '使用' in content:
            return 'user_publish_help', {}

        # 原有的基础指令
        if '你好' in content or 'hello' in content_lower:
            return 'greeting', {}
        elif '帮助' in content or 'help' in content_lower:
            return 'help', {}
        elif '功能' in content or 'functions' in content_lower:
            return 'user_functions', {}
        elif '时间' in content or 'time' in content_lower:
            return 'time', {}
        elif '状态' in content or 'status' in content_lower:
            return 'status', {}
        else:
            return 'chat', {'content': content}

    def process_command(self, user_id: str, command: str, params: Dict) -> str:
        """处理指令并返回回复"""
        logger.info(f"处理指令: {command}, 参数: {params}, 用户: {user_id}")

        # 检查用户是否处于特殊状态（封面选择等）
        user_state = self.config_manager.get_user_state(user_id)
        if user_state:
            return self._handle_user_state(user_id, user_state, params.get('content', ''))

        # 管理员指令处理
        if command == 'admin':
            return self._handle_admin_login(user_id, params)

        # 检查管理员权限 (简化后只保留核心功能)
        if command in ['list']:
            if not self.is_admin(user_id):
                return "❌ 需要管理员权限！\r\n\r\n发送 \"/admin 密码\" 获取权限"

        # 管理员功能 (简化)
        if command == 'list':
            return self._handle_admin_list()
        elif command == 'admin_help':
            return self._handle_admin_help()
        elif command == 'help' and self.is_admin(user_id):
            return self._handle_admin_help()

        # 用户功能（非管理员）
        elif command == 'user_bind':
            return self._handle_user_bind(user_id, params)
        elif command == 'user_bind_help':
            return self._handle_user_bind_help()
        elif command == 'user_test':
            return self._handle_user_test(user_id, params)
        elif command == 'user_publish':
            return self._handle_user_publish(user_id, params)
        elif command == 'user_publish_help':
            return self._handle_user_publish_help()
        elif command == 'user_list_configs':
            return self._handle_user_list_configs(user_id)

        # 基础功能
        elif command == 'greeting':
            return "嘿嘿~ 你好呀！我是「不存在的画廊」的微信公众号助手～ (´∀｀) 💖"
        elif command == 'help':
            return self._handle_user_help()
        elif command == 'user_functions':
            return self._handle_user_functions(user_id)
        elif command == 'time':
            current_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
            return f"当前时间是: {current_time} 呀～ \\(^o^)/"
        elif command == 'status':
            return self._handle_status()
        elif command == 'chat':
            return self._handle_chat_with_humor(params.get('content', ''))
        else:
            return self._handle_unknown_command(params.get('content', ''))

    def _handle_admin_login(self, user_id: str, params: Dict) -> str:
        """处理管理员登录"""
        password = params.get('password', '')

        if self.grant_admin_access(user_id, password):
            return """✅ 管理员权限获取成功！

🔧 管理员功能：
• /list - 查看所有用户的配置
• /help - 管理员帮助

⏰ 权限有效期：30分钟

发送 "/help" 查看详细管理功能"""
        else:
            return "❌ 管理员密码错误！"

    def _handle_bind(self, params: Dict) -> str:
        """处理绑定配置"""
        name = params.get('name', '')
        appid = params.get('appid', '')
        secret = params.get('secret', '')
        token = params.get('token', '')

        if not name or not appid or not secret:
            return """❌ 参数不完整！

正确格式：
/bind 配置名称
appid:wx1234567890
secret:abcdef1234567890
token:your_token"""

        # 验证配置
        logger.info(f"验证微信配置: {appid}")
        if self.wechat_api.validate_wechat_config(appid, secret):
            # 保存配置
            if self.config_manager.save_wx_config(name, appid, secret, token):
                return f"""✅ 配置绑定成功！

📱 配置名称: {name}
🔑 AppID: {appid}
🔐 Secret: {'*' * (len(secret) - 8)}{secret[-8:]}
🎯 Token: {token if token else '未设置'}

配置已保存并验证通过！"""
            else:
                return "❌ 配置保存失败！"
        else:
            return "❌ 微信配置验证失败，请检查AppID和AppSecret是否正确"





    def _handle_admin_help(self) -> str:
        """处理管理员帮助"""
        return """🔧 管理员专用功能：

📋 监控功能：
• /list - 查看所有用户的配置情况
• /help - 显示此帮助

🎯 管理员只负责监控用户配置使用情况
所有功能操作都由用户通过微信消息完成

嘿嘿~ 简洁高效的管理！(´∀｀) 💖"""

    def _handle_admin_list(self) -> str:
        """处理管理员查看所有配置"""
        # 获取所有用户配置
        user_configs = self.config_manager.config_data.get('user_configs', {})

        result = "🔧 用户配置监控面板\r\n\r\n"

        # 用户配置统计
        if user_configs:
            result += f"👥 用户配置统计：\r\n"
            result += f"• 总用户数: {len(user_configs)}\r\n"
            total_user_configs = sum(len(configs) for configs in user_configs.values())
            result += f"• 总配置数: {total_user_configs}\r\n\r\n"

            result += "👤 用户详情：\r\n"
            for user_id, configs in user_configs.items():
                result += f"• 用户 {user_id}: {len(configs)}个配置\r\n"
                for nickname, config in configs.items():
                    result += f"  └ {nickname}\r\n"
                    result += f"    AppID: {config.get('appid', 'N/A')}\r\n"
                    result += f"    Secret: {config.get('secret', 'N/A')}\r\n"
            result += "\r\n"
        else:
            result += "👥 暂无用户配置\r\n\r\n"

        result += "📊 系统运行正常！"
        return result

    def _handle_user_help(self) -> str:
        """处理用户帮助"""
        return """嘿嘿~ 欢迎使用「不存在的画廊」的公众号助手！✨

🎮 基础功能：
• 发送"你好"来打招呼～
• 发送"时间"看现在几点啦
• 发送"状态"查看我的运行情况
• 发张图片给我试试看！

💖 想看我有什么特殊功能？
发送"功能"查看完整功能列表！

嘿嘿~ 试着跟我聊聊吧！(´∀｀)💫"""

    def _handle_user_functions(self, user_id: str) -> str:
        """处理用户功能列表"""
        # 获取用户的配置
        user_configs = self.config_manager.list_user_configs(user_id)

        result = """🎯 我的功能列表：

🎮 基础功能：
• 你好 - 问候功能
• 时间 - 获取当前时间
• 状态 - 查看系统状态
• 帮助 - 查看基础帮助
• 功能 - 查看此功能列表

📱 公众号管理功能：
• 绑定 AppID Secret 昵称 - 绑定你的公众号
• 我的配置 - 查看你的所有配置
• 测试 昵称 - 测试配置连接
• 使用 昵称 发布 标题 内容 作者 - 发布文章到草稿箱

"""

        # 显示用户当前的配置
        if user_configs:
            result += f"📋 你当前的配置：\r\n"
            for nickname, config in user_configs.items():
                result += f"• {nickname} ({config.get('appid', 'N/A')})\r\n"
            result += "\r\n💡 你可以直接使用昵称来测试和发布！"
        else:
            result += "📭 你还没有绑定任何配置\r\n\r\n💡 发送「绑定 你的AppID 你的Secret 昵称」来开始使用！"

        return result

    def _handle_status(self) -> str:
        """处理状态查询"""
        config_count = len(self.config_manager.list_configs())
        current_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())

        return f"""📊 系统状态：

⏰ 当前时间: {current_time}
📱 已绑定配置: {config_count} 个
🤖 服务状态: 正常运行
💖 版本: v2.0 (消息指令版)

嘿嘿~ 一切正常呢！(´∀｀)"""

    # 用户功能处理方法
    def _handle_user_bind(self, user_id: str, params: Dict) -> str:
        """处理用户绑定配置"""
        appid = params.get('appid', '')
        secret = params.get('secret', '')
        nickname = params.get('nickname', '')

        # 验证配置
        logger.info(f"用户 {user_id} 验证微信配置: {appid}")
        if self.wechat_api.validate_wechat_config(appid, secret):
            # 保存用户配置
            if self.config_manager.save_user_config(user_id, nickname, appid, secret):
                return f"""✅ 绑定成功！\r\n\r\n🎯 昵称: {nickname}\r\n🔑 AppID: {appid}\r\n🔐 Secret: {'*' * (len(secret) - 8)}{secret[-8:]}\r\n\r\n现在你可以使用 "测试 {nickname}" 来测试连接啦～"""
            else:
                return "❌ 配置保存失败！请稍后重试～"
        else:
            return "❌ 微信配置验证失败！\r\n\r\n请检查AppID和Secret是否正确呀～ (￣▽￣)"

    def _handle_user_bind_help(self) -> str:
        """处理绑定格式帮助"""
        return """嘿嘿~ 绑定格式不对哦！\r\n\r\n正确格式：\r\n绑定 你的AppID 你的Secret 昵称\r\n\r\n例如：\r\n绑定 wx123456 abc123secret 我的公众号\r\n\r\n记得用空格分开哦～ (´∀｀)"""

    def _handle_user_test(self, user_id: str, params: Dict) -> str:
        """处理用户测试配置"""
        nickname = params.get('nickname', '')

        config = self.config_manager.get_user_config(user_id, nickname)
        if not config:
            return f"❌ 找不到昵称 '{nickname}' 的配置\r\n\r\n要不先绑定一个？嘿嘿~ (´∀｀)"

        logger.info(f"用户 {user_id} 测试配置: {nickname}")
        if self.wechat_api.validate_wechat_config(config['appid'], config['secret']):
            return f"✅ '{nickname}' 连接测试成功！\r\n\r\n可以正常使用啦～ \\(^o^)/"
        else:
            return f"❌ '{nickname}' 连接测试失败\r\n\r\n配置可能有问题哦～ (ﾟДﾟ)"

    def _handle_user_publish(self, user_id: str, params: Dict) -> str:
        """处理用户发布文章"""
        nickname = params.get('nickname', '')
        title = params.get('title', '')
        content = params.get('content', '')
        author = params.get('author', '不存在的画廊')  # 获取作者参数

        config = self.config_manager.get_user_config(user_id, nickname)
        if not config:
            return f"❌ 找不到昵称 '{nickname}' 的配置\r\n\r\n要不先绑定一个？嘿嘿~ (´∀｀)"

        # 不直接发布，而是设置状态等待封面选择
        logger.info(f"用户 {user_id} 准备发布文章: {title} (作者: {author})")

        # 设置用户状态等待封面选择
        self.config_manager.set_user_state(user_id, 'cover_selection', {
            'title': title,
            'content': content,
            'nickname': nickname,
            'author': author,
            'config': config  # 保存配置信息用于后续发布
        })

        return f"""📝 准备发布文章～\r\n\r\n📄 标题: {title}\r\n📱 公众号: {nickname}\r\n👤 作者: {author}\r\n\r\n🎨 请选择封面方式：\r\n回复 "0" - 使用标题翻译作为封面文字\r\n发送图片 - 使用您的图片作为封面\r\n\r\n选择后立即发布到草稿箱！ (5分钟内有效) ✨"""

    def _handle_user_publish_help(self) -> str:
        """处理发布格式帮助"""
        return """嘿嘿~ 发布格式不对哦！\r\n\r\n正确格式：\r\n使用 昵称 发布 标题 内容 [作者]\r\n\r\n例如：\r\n使用 我的公众号 发布 今日资讯 这是今天的精彩内容 小编\r\n\r\n作者是可选的，不填默认是"不存在的画廊"哦～ (´∀｀)"""

    def _handle_user_state(self, user_id: str, user_state: Dict, content: str) -> str:
        """处理用户特殊状态"""
        state = user_state.get('state')
        state_data = user_state.get('data', {})

        if state == 'cover_selection':
            if content.strip() == '0':
                # 用户选择使用标题翻译作为封面，执行发布
                title = state_data.get('title', '')
                content_text = state_data.get('content', '')
                nickname = state_data.get('nickname', '')
                author = state_data.get('author', '不存在的画廊')
                config = state_data.get('config', {})

                self.config_manager.clear_user_state(user_id)

                logger.info(f"用户 {user_id} 选择标题翻译封面，开始发布文章: {title}")

                # 执行实际发布
                success = self.wechat_api.publish_to_draft(
                    config['appid'],
                    config['secret'],
                    title,
                    content_text,
                    author  # 传递作者参数
                )

                if success:
                    translated_title = self.wechat_api.translate_to_english(title)
                    return f"""✅ 文章发布成功！\r\n\r\n📝 标题: {title}\r\n📱 公众号: {nickname}\r\n👤 作者: {author}\r\n🎯 已发布到草稿箱\r\n\r\n🎨 封面: 使用翻译文字 "{translated_title}"\r\n\r\n快去微信公众平台后台看看吧～ ✨"""
                else:
                    return f"""❌ 文章发布失败\r\n\r\n📝 标题: {title}\r\n请检查网络连接和配置～ (ﾟ∀ﾟ)"""
            else:
                # 用户发送了其他内容，可能是文字或者将要发送图片
                return f"""🎨 等待您发送封面图片...\r\n\r\n📸 请发送一张图片作为 "{state_data.get('title', '')}" 的封面\r\n\r\n或者回复 "0" 使用标题翻译作为封面文字\r\n\r\n(还剩几分钟时间哦) ⏰"""

        return "🤔 状态处理出错了，请重新操作～"

    def _handle_image_cover_selection(self, user_id: str, user_state: Dict, pic_url: str, media_id: str) -> str:
        """处理图片封面选择"""
        state_data = user_state.get('data', {})
        title = state_data.get('title', '')
        content_text = state_data.get('content', '')
        nickname = state_data.get('nickname', '')
        author = state_data.get('author', '不存在的画廊')
        config = state_data.get('config', {})

        self.config_manager.clear_user_state(user_id)

        logger.info(f"用户 {user_id} 选择图片封面，开始发布文章: {title}")
        logger.info(f"收到图片封面 - PicUrl: {pic_url}, MediaId: {media_id}")

        # 首先获取access_token用于下载图片
        access_token = self.wechat_api.get_access_token(config['appid'], config['secret'])
        if not access_token:
            return f"""❌ 获取访问令牌失败\r\n\r\n📝 标题: {title}\r\n请检查配置～ (ﾟ∀ﾟ)"""

        # 下载用户的图片
        user_image_path = self.wechat_api.download_wechat_image(access_token, media_id)
        user_thumb_media_id = None

        if user_image_path:
            # 将用户图片上传为永久素材
            user_thumb_media_id = self.wechat_api.upload_material(access_token, user_image_path)

            # 清理下载的临时文件
            try:
                if user_image_path and os.path.exists(user_image_path):
                    os.unlink(user_image_path)
                    logger.info(f"清理临时下载文件: {user_image_path}")
            except Exception as e:
                logger.warning(f"清理临时文件失败: {e}")

        # 执行实际发布，使用用户的图片MediaId作为封面
        success = self.wechat_api.publish_to_draft(
            config['appid'],
            config['secret'],
            title,
            content_text,
            author,  # 传递作者参数
            user_thumb_media_id  # 使用用户图片的MediaId
        )

        if success:
            cover_info = "使用您的自定义图片" if user_thumb_media_id else "使用默认封面"
            logger.info(f"图片封面发布成功，用户: {user_id}, 标题: {title}")
            success_message = f"""✅ 文章发布成功！\r\n\r\n📝 标题: {title}\r\n📱 公众号: {nickname}\r\n👤 作者: {author}\r\n🎯 已发布到草稿箱\r\n\r\n🎨 封面: {cover_info}\r\n\r\n快去微信公众平台后台看看吧～ ✨"""
            logger.info(f"返回成功消息，长度: {len(success_message)}")
            return success_message
        else:
            logger.error(f"图片封面发布失败，用户: {user_id}, 标题: {title}")
            error_message = f"""❌ 文章发布失败\r\n\r\n📝 标题: {title}\r\n请检查网络连接和配置～ (ﾟ∀ﾟ)"""
            logger.info(f"返回失败消息，长度: {len(error_message)}")
            return error_message

    def _handle_chat_with_humor(self, content: str) -> str:
        """处理聊天消息（诙谐风格）"""
        humor_responses = [
            f"收到你的消息啦～ 你说: 「{content}」\r\n\r\n嘿嘿~ 我是个专业的公众号助手，不是聊天机器人哦！\r\n试试发送「你好」看看我能做什么吧～ (´∀｀)💖",
            f"哇~ 你说的是「{content}」呀！\r\n\r\n不过我主要是帮你管理公众号的呢～\r\n如果需要帮助就说「你好」吧！✨",
            f"「{content}」... 嗯嗯，听起来很有趣！\r\n\r\n不过我更擅长的是公众号管理哦～\r\n有什么需要帮忙的就告诉我吧！(￣▽￣)",
        ]
        import random
        return random.choice(humor_responses)

    def _handle_unknown_command(self, content: str) -> str:
        """处理未知指令（诙谐回复）"""
        humor_responses = [
            f"呃... 「{content}」是什么呢？\r\n\r\n我好像听不懂诶～ 要不试试说「你好」？(´･ω･`)",
            f"嗯嗯... 你是想说「{content}」吗？\r\n\r\n我还在学习中呢！发个「你好」我就知道怎么回答啦～ ✨",
            f"哎呀~ 「{content}」这个我不太明白呢！\r\n\r\n说「你好」的话我就知道该怎么帮你啦！(´∀｀)",
        ]
        import random
        return random.choice(humor_responses)

    def _handle_user_list_configs(self, user_id: str) -> str:
        """处理用户查看自己的配置列表"""
        user_configs = self.config_manager.list_user_configs(user_id)

        if not user_configs:
            return """📋 你还没有绑定任何公众号配置呢～

🎯 想要绑定一个公众号？发送：
绑定 你的AppID 你的Secret 昵称

例如：
绑定 wx123456 abc123secret 我的测试号

绑定后就可以发布文章啦～ (´∀｀) 💖"""

        result = f"📱 你的公众号配置 (共{len(user_configs)}个)：\r\n\r\n"

        for nickname, config in user_configs.items():
            appid = config.get('appid', '')
            secret = config.get('secret', '')
            # 隐藏部分敏感信息
            masked_appid = appid[:8] + "..." if len(appid) > 8 else appid
            masked_secret = "*" * 20 + secret[-4:] if len(secret) > 4 else "*" * len(secret)

            result += f"🔹 {nickname}\r\n"
            result += f"   AppID: {masked_appid}\r\n"
            result += f"   Secret: {masked_secret}\r\n\r\n"

        result += "💡 使用提示：\r\n"
        result += "• 测试连接：测试 昵称\r\n"
        result += "• 发布文章：使用 昵称 发布 标题 内容 作者\r\n"
        result += "• 查看配置：我的配置\r\n\r\n"
        result += "嘿嘿~ 这些都是你专属的配置哦！(´∀｀) 💖"

        return result