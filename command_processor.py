#!/usr/bin/env python3
"""
微信消息指令处理器
将CLI功能转换为微信消息处理
"""
import re
import time
import os
import threading
import html
from typing import Dict, Tuple, List
from config import ConfigManager
from wechat_api import WeChatAPI
from tutu_api import TutuAPI
from work_storage import WorkStorage
import logging

logger = logging.getLogger(__name__)

class CommandProcessor:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.wechat_api = WeChatAPI()
        self.tutu_api = TutuAPI()
        self.work_storage = WorkStorage()

        # 启动时清理过期的工作数据（保留7天）
        try:
            cleaned_count = self.work_storage.clean_expired_works(days=7)
            if cleaned_count > 0:
                logger.info(f"启动时清理了 {cleaned_count} 个过期的图图工作")
        except Exception as e:
            logger.warning(f"清理过期工作数据失败: {e}")

        # 管理员会话状态 (用户ID -> 权限到期时间)
        self.admin_sessions = {}

        # 管理员密码 (生产环境应该从环境变量读取)
        self.admin_password = "admin123456"

        # 会话过期时间 (30分钟)
        self.session_timeout = 30 * 60

        # 暂存生成时的标题信息 (work_id -> {'title': str, 'timestamp': float})
        self.pending_titles = {}

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

        # 图图生成格式：图图 {标题} {描述}
        tutu_pattern = r'^图图\s+(.+?)\s+(.+)$'
        tutu_match = re.match(tutu_pattern, content)
        if tutu_match:
            title, plot = tutu_match.groups()
            return 'tutu_generate', {
                'title': title.strip(),
                'plot': plot.strip()
            }

        # 图图格式检测（格式错误提示）
        if content.startswith('图图'):
            return 'tutu_help', {}

        # 查询图图格式：查询图图 {工作ID}
        query_tutu_pattern = r'^查询图图\s+([a-zA-Z0-9]+)$'
        query_tutu_match = re.match(query_tutu_pattern, content)
        if query_tutu_match:
            work_id = query_tutu_match.group(1)
            return 'tutu_query', {
                'work_id': work_id.strip()
            }

        # 查询图图格式检测（格式错误提示）
        if content.startswith('查询图图'):
            return 'tutu_query_help', {}

        # 查询发布结果格式：查询发布结果 {工作ID}
        query_publish_pattern = r'^查询发布结果\s+([a-zA-Z0-9]+)$'
        query_publish_match = re.match(query_publish_pattern, content)
        if query_publish_match:
            work_id = query_publish_match.group(1)
            return 'tutu_publish_query', {
                'work_id': work_id.strip()
            }

        # 查询发布结果格式检测（格式错误提示）
        if content.startswith('查询发布结果'):
            return 'tutu_publish_query_help', {}

        # 发布图图格式：发布图图 {工作ID} {昵称} {标题} [作者]
        publish_tutu_pattern = r'^发布图图\s+([a-zA-Z0-9]+)\s+(.+?)\s+(.+?)(?:\s+(.+?))?$'
        publish_tutu_match = re.match(publish_tutu_pattern, content)
        if publish_tutu_match:
            work_id, nickname, title, author = publish_tutu_match.groups()
            return 'tutu_publish', {
                'work_id': work_id.strip(),
                'nickname': nickname.strip(),
                'title': title.strip(),
                'author': author.strip() if author else "不存在的画廊"
            }

        # 发布图图格式检测（格式错误提示）
        if content.startswith('发布图图'):
            return 'tutu_publish_help', {}


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
        elif command == 'tutu_generate':
            return self._handle_tutu_generate(params)
        elif command == 'tutu_help':
            return self._handle_tutu_help()
        elif command == 'tutu_query':
            return self._handle_tutu_query(params)
        elif command == 'tutu_query_help':
            return self._handle_tutu_query_help()
        elif command == 'tutu_publish':
            return self._handle_tutu_publish(user_id, params)
        elif command == 'tutu_publish_help':
            return self._handle_tutu_publish_help()
        elif command == 'tutu_publish_query':
            return self._handle_tutu_publish_query(params)
        elif command == 'tutu_publish_query_help':
            return self._handle_tutu_publish_query_help()

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

🎨 图片生成功能：
• 图图 标题 描述 - 生成专属图片
• 查询图图 工作ID - 查看图片生成进度并自动绑定
• 发布图图 工作ID 昵称 标题 [作者] - 发布系列图片草稿箱
• 查询发布结果 工作ID - 查看详细的发布记录和统计

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

    def _handle_tutu_generate(self, params: Dict) -> str:
        """处理图图生成请求"""
        title = params.get('title', '')
        plot = params.get('plot', '')

        if not title or not plot:
            return self._handle_tutu_help()

        logger.info(f"处理图图生成请求 - 标题: {title}, 描述: {plot}")

        # 调用图图API
        result = self.tutu_api.create_image(title, plot)

        if result:
            # 如果生成成功，保存标题信息以备后续查询时使用
            if result.get('code') == 200:
                data = result.get('data', {})
                work_id = data.get('id', '')
                if work_id:
                    self.pending_titles[work_id] = {
                        'title': title,
                        'timestamp': time.time()
                    }
                    logger.info(f"保存标题信息: {work_id} -> {title}")

                    # 清理过期的暂存标题（超过1小时的）
                    self._clean_expired_pending_titles()

            return self.tutu_api.format_api_response(result, title, plot)
        else:
            return f"""❌ 图片生成失败

🎨 标题: {title}
📝 描述: {plot}

请检查网络连接或稍后重试～ (´∀｀)"""

    def _handle_tutu_help(self) -> str:
        """处理图图帮助信息"""
        return """🎨 图图生成功能帮助

正确格式：
图图 标题 描述

例如：
图图 美丽风景 一片美丽的山水风景，阳光明媚，绿树成荫

📝 使用说明：
• 标题：简短描述图片主题
• 描述：详细描述您想要的图片内容
• 每次生成4张图片
• 使用快速模式生成

嘿嘿~ 试试用图图来创作你的专属图片吧！(´∀｀) 🎨✨"""

    def _handle_tutu_query(self, params: Dict) -> str:
        """处理查询图图请求"""
        work_id = params.get('work_id', '')

        if not work_id:
            return self._handle_tutu_query_help()

        logger.info(f"处理图图查询请求 - 工作ID: {work_id}")

        # 首先检查本地是否已经绑定
        if self.work_storage.work_exists(work_id):
            work_data = self.work_storage.get_work(work_id)
            image_count = len(work_data.get('image_urls', []))
            title = work_data.get('title', '未知作品')

            return f"""✅ 已经生成并绑定成功{image_count}张图片！

🆔 工作ID: #{work_id}
🎨 标题: {title}
📊 状态: 已完成并绑定
📸 图片数量: {image_count}张

💡 现在可以使用以下指令发布到草稿箱：
发布图图 {work_id} 昵称 文章标题 [作者]

例如：发布图图 {work_id} 我的公众号 {title}作品集 小编

嘿嘿~ 快去发布你的专属图片作品吧！(´∀｀) 🎨✨"""

        # 调用图图API查询分镜
        result = self.tutu_api.get_work_shots(work_id)

        if result and result.get('code') == 200:
            shots_data = result.get('data', [])
            completed_shots = [shot for shot in shots_data if shot.get('status') == 'COMPLETED']

            # 如果所有分镜都完成了，自动绑定
            if completed_shots and len(completed_shots) == len(shots_data):
                # 尝试从暂存的标题信息中获取标题
                pending_info = self.pending_titles.get(work_id, {})
                title = pending_info.get('title', "AI生成图片")

                success = self.work_storage.save_work(work_id, title, shots_data)

                if success:
                    image_count = len(completed_shots)
                    logger.info(f"工作 {work_id} 自动绑定成功，包含 {image_count} 张图片")

                    # 清理暂存的标题信息
                    if work_id in self.pending_titles:
                        del self.pending_titles[work_id]
                        logger.info(f"清理暂存标题信息: {work_id}")

                    return f"""✅ 已经生成并绑定成功{image_count}张图片！

🆔 工作ID: #{work_id}
🎨 标题: {title}
📊 状态: 刚刚完成并自动绑定
📸 图片数量: {image_count}张

💡 现在可以使用以下指令发布到草稿箱：
发布图图 {work_id} 昵称 文章标题 [作者]

例如：发布图图 {work_id} 我的公众号 {title}作品集 小编

嘿嘿~ 快去发布你的专属图片作品吧！(´∀｀) 🎨✨"""
                else:
                    logger.error(f"工作 {work_id} 自动绑定失败")

            # 如果还没完成或绑定失败，返回普通查询结果
            return self.tutu_api.format_shots_response(shots_data, work_id)
        else:
            error_message = result.get('message', '查询失败') if result else '网络错误'
            return f"""❌ 查询图图作品失败

🆔 工作ID: #{work_id}
❗ 错误信息: {error_message}

请检查工作ID是否正确或稍后重试～ (´∀｀)"""

    def _handle_tutu_query_help(self) -> str:
        """处理查询图图帮助信息"""
        return """📸 查询图图功能帮助

正确格式：
查询图图 工作ID

例如：
查询图图 e8bcd7eb6182101601067111e8d231a9

📝 使用说明：
• 工作ID：生成图片时返回的任务ID
• 查询当前作品的分镜生成进度
• 显示已完成分镜的图片链接

嘿嘿~ 用这个指令来查看你的图片生成进度吧！(´∀｀) 📸✨"""

    def _handle_tutu_publish(self, user_id: str, params: Dict) -> str:
        """处理发布图图到草稿箱请求 - 快速验证并异步处理"""
        work_id = params.get('work_id', '')
        nickname = params.get('nickname', '')
        title = params.get('title', '')
        author = params.get('author', '不存在的画廊')

        if not work_id or not nickname or not title:
            return self._handle_tutu_publish_help()

        logger.info(f"用户 {user_id} 请求发布图图作品 - 工作ID: {work_id}, 配置: {nickname}, 标题: {title}")

        # 快速验证阶段 - 必须在5秒内完成
        # 1. 验证WorkID是否存在
        if not self.work_storage.work_exists(work_id):
            return f"""❌ 工作ID未找到或未绑定

🆔 工作ID: #{work_id}

请先使用「查询图图 {work_id}」确认图片已生成并绑定成功～ (´∀｀)"""

        # 2. 检查是否已经发布过相同的内容
        if self.work_storage.is_published(work_id, user_id, nickname, title):
            published_records = self.work_storage.get_published_records(work_id)
            matching_records = [r for r in published_records if
                              r.get('user_id') == user_id and
                              r.get('nickname') == nickname and
                              r.get('title') == title]

            if matching_records:
                last_record = matching_records[-1]
                published_time = last_record.get('published_at', '未知时间')

                return f"""⚠️ 已经发布过相同内容

🆔 工作ID: #{work_id}
📝 标题: {title}
📱 公众号: {nickname}
👤 作者: {author}
⏰ 上次发布时间: {published_time[:19]}

💡 如果确实需要重复发布，请更换标题或使用不同的昵称～ (´∀｀)"""

        # 3. 验证用户配置
        config = self.config_manager.get_user_config(user_id, nickname)
        if not config:
            return f"❌ 找不到昵称 '{nickname}' 的配置\r\n\r\n要不先绑定一个？嘿嘿~ (´∀｀)"

        # 4. 验证图片是否存在
        image_urls = self.work_storage.get_image_urls(work_id)
        if not image_urls:
            return f"""❌ 未找到绑定的图片

🆔 工作ID: #{work_id}

请重新查询图图状态确认图片已正确绑定～ (´∀｀)"""

        # 快速验证通过，启动后台处理
        threading.Thread(
            target=self._async_process_tutu_publish,
            args=(user_id, work_id, nickname, title, author, config, image_urls),
            daemon=True
        ).start()

        # 立即返回处理中的消息
        return f"""🚀 开始发布图片作品集

🆔 工作ID: #{work_id}
📝 标题: {title}
📱 公众号: {nickname}
👤 作者: {author}
📸 包含图片: {len(image_urls)}张

⏳ 正在后台处理中，预计需要1-2分钟...
📱 请稍后到微信公众平台后台「素材管理」→「草稿箱」查看

嘿嘿~ 马上就好啦！(´∀｀) ✨"""

    def _async_process_tutu_publish(self, user_id: str, work_id: str, nickname: str,
                                   title: str, author: str, config: Dict, image_urls: List[str]) -> None:
        """异步处理图图发布 - 使用图文消息图片上传接口"""
        try:
            logger.info(f"开始异步处理图图发布 - 用户: {user_id}, 工作ID: {work_id}")

            # 1. 获取access_token
            logger.info(f"🔑 正在获取access_token, AppID: {config['appid']}")
            access_token = self.wechat_api.get_access_token(config['appid'], config['secret'])
            if not access_token:
                logger.error(f"异步处理失败：获取access_token失败 - 工作ID: {work_id}")
                return
            else:
                logger.info(f"✅ access_token获取成功: {access_token[:20]}...")

            logger.info(f"开始处理 {len(image_urls)} 张图片，使用图文消息图片上传接口")

            # 2. 批量下载并上传图片，获取微信图片URL
            wechat_image_urls = []
            temp_files = []
            processing_stats = {
                "total_images": len(image_urls),
                "downloaded_count": 0,
                "uploaded_count": 0,
                "failed_downloads": [],
                "failed_uploads": [],
                "successful_images": []
            }

            try:
                for i, image_url in enumerate(image_urls, 1):
                    logger.info(f"📥 处理第 {i}/{len(image_urls)} 张图片")
                    logger.info(f"🔗 原始图片URL: {image_url}")

                    # 下载图片
                    temp_path = self.wechat_api.download_image_from_url(image_url)

                    if temp_path:
                        temp_files.append(temp_path)
                        processing_stats["downloaded_count"] += 1
                        logger.info(f"✅ 图片下载成功: {temp_path}")

                        # 使用图文消息图片上传接口
                        logger.info(f"🔄 开始上传图片到微信...")
                        wechat_image_url = self.wechat_api.upload_image_for_article(access_token, temp_path)

                        if wechat_image_url:
                            wechat_image_urls.append(wechat_image_url)
                            processing_stats["uploaded_count"] += 1
                            processing_stats["successful_images"].append({
                                "index": i,
                                "original_url": image_url,
                                "wechat_url": wechat_image_url
                            })
                            logger.info(f"✅ 第 {i} 张图片上传成功: {wechat_image_url}")
                        else:
                            processing_stats["failed_uploads"].append({
                                "index": i,
                                "original_url": image_url,
                                "reason": "上传到微信失败"
                            })
                            logger.error(f"❌ 第 {i} 张图片上传失败，详细错误请查看控制台输出")
                            # 继续处理其他图片，不中断
                    else:
                        processing_stats["failed_downloads"].append({
                            "index": i,
                            "original_url": image_url,
                            "reason": "下载失败"
                        })
                        logger.error(f"❌ 第 {i} 张图片下载失败，URL: {image_url}")
                        # 继续处理其他图片，不中断

                logger.info(f"📊 图片处理统计: 总共{processing_stats['total_images']}张, 下载成功{processing_stats['downloaded_count']}张, 上传成功{processing_stats['uploaded_count']}张")

                # 3. 只要有一张图片成功就继续发布
                if wechat_image_urls:
                    work_data = self.work_storage.get_work(work_id)
                    original_title = work_data.get('title', 'AI生成图片')

                    content = self._generate_tutu_article_content(
                        wechat_image_urls, work_id, original_title
                    )

                    # 4. 处理封面图片（使用第一张成功的图片作为封面）
                    thumb_media_id = ""
                    if temp_files:
                        try:
                            # 找到第一张成功上传的图片对应的临时文件
                            first_successful_index = processing_stats["successful_images"][0]["index"] - 1
                            if first_successful_index < len(temp_files):
                                first_temp_file = temp_files[first_successful_index]
                                upload_result = self.wechat_api.upload_material(access_token, first_temp_file)

                                if upload_result:
                                    thumb_media_id = upload_result.get('media_id', '')
                                    logger.info(f"✅ 封面图片上传成功: {thumb_media_id}")
                                else:
                                    logger.warning("封面图片上传失败")
                        except Exception as e:
                            logger.warning(f"封面图片处理失败: {e}")

                    # 5. 创建草稿箱
                    draft_media_id = self.wechat_api.add_draft(
                        access_token, title, content, thumb_media_id, author
                    )

                    if draft_media_id:
                        # 6. 记录发布信息（包含详细的处理结果）
                        publish_result = {
                            "draft_media_id": draft_media_id,
                            "processing_stats": processing_stats,
                            "has_cover": bool(thumb_media_id),
                            "cover_media_id": thumb_media_id
                        }

                        self.work_storage.mark_as_published(work_id, user_id, nickname, title, author, publish_result)
                        logger.info(f"✅ 异步发布成功 - 工作ID: {work_id}, 草稿箱ID: {draft_media_id}, 成功图片: {processing_stats['uploaded_count']}/{processing_stats['total_images']}")
                    else:
                        logger.error(f"❌ 异步发布失败：草稿箱创建失败 - 工作ID: {work_id}")
                else:
                    logger.error(f"❌ 异步发布失败：所有图片处理失败 - 工作ID: {work_id}")
                    logger.error(f"失败详情: 下载失败{len(processing_stats['failed_downloads'])}张, 上传失败{len(processing_stats['failed_uploads'])}张")

            finally:
                # 7. 清理临时文件（包括压缩后的文件）
                for temp_file in temp_files:
                    try:
                        if os.path.exists(temp_file):
                            os.unlink(temp_file)
                            logger.info(f"🧹 清理临时文件: {temp_file}")

                        # 清理可能的压缩文件
                        compressed_file = temp_file.replace('.jpg', '_compressed.jpg')
                        if os.path.exists(compressed_file):
                            os.unlink(compressed_file)
                            logger.info(f"🧹 清理压缩文件: {compressed_file}")
                    except Exception as e:
                        logger.warning(f"清理临时文件失败: {e}")

        except Exception as e:
            logger.error(f"异步处理图图发布时发生错误: {e}, 工作ID: {work_id}")

    def _generate_tutu_article_content(self, image_urls: List[str], work_id: str, original_title: str) -> str:
        """生成图图文章的富文本内容（精简版：只包含图片，无文字描述）"""

        # 生成唯一容器ID
        timestamp = int(time.time())
        container_id = f"markdown-preview-{timestamp}"

        # 生成图片HTML列表，直接使用远程URL，去掉所有文字
        img_htmls = []
        for i, image_url in enumerate(image_urls, 1):
            # 确保图片URL安全
            safe_image_url = html.escape(str(image_url))
            alt_text = f"AI生成图片{i}"

            # 只保留图片，去掉标题和描述
            img_html = f"""<section style="margin: 15px 0; text-align: center;">
<img src="{safe_image_url}" alt="{alt_text}" style="max-width: 100%; height: auto; display: block; margin: 0 auto; border-radius: 8px;">
</section>"""
            img_htmls.append(img_html)

        # 组装完整的HTML内容，只包含图片
        full_content = f"""<section id="{container_id}" style="padding: 20px; max-width: 100%; box-sizing: border-box;">
{chr(10).join(img_htmls)}
</section>"""

        return full_content

    def _handle_tutu_publish_help(self) -> str:
        """处理发布图图帮助信息"""
        return """📤 发布图图功能帮助

正确格式：
发布图图 工作ID 昵称 标题 [作者]

例如：
发布图图 e8bcd7eb6182101601067111e8d231a9 我的公众号 美丽风景作品集 小编

📝 使用说明：
• 工作ID：已绑定的图图任务ID
• 昵称：您绑定的公众号配置昵称
• 标题：草稿箱文章标题
• 作者：可选，默认为"不存在的画廊"

🎨 功能特点：
• 自动下载所有生成的图片
• 批量上传到微信永久素材库
• 创建包含所有图片的富文本草稿箱
• 使用第一张图片作为封面
• 包含分镜描述和作品信息

💡 提示：
先用「查询图图 工作ID」确认图片已绑定
再用此指令创建专属的图片作品集

嘿嘿~ 让你的AI图片变成精美的公众号文章！(´∀｀) 📤✨"""

    def _clean_expired_pending_titles(self) -> None:
        """清理过期的暂存标题信息（超过1小时的）"""
        try:
            current_time = time.time()
            expired_keys = []

            for work_id, info in self.pending_titles.items():
                timestamp = info.get('timestamp', 0)
                if current_time - timestamp > 3600:  # 1小时 = 3600秒
                    expired_keys.append(work_id)

            for key in expired_keys:
                del self.pending_titles[key]

            if expired_keys:
                logger.info(f"清理了 {len(expired_keys)} 个过期的暂存标题")

        except Exception as e:
            logger.warning(f"清理过期暂存标题失败: {e}")

    def _handle_tutu_publish_query(self, params: Dict) -> str:
        """处理查询发布结果请求"""
        work_id = params.get('work_id', '')
        if not work_id:
            return self._handle_tutu_publish_query_help()

        logger.info(f"处理查询发布结果请求 - 工作ID: {work_id}")

        # 检查工作是否存在
        if not self.work_storage.work_exists(work_id):
            return f"""❌ 工作ID不存在
🆔 工作ID: #{work_id}
请检查工作ID是否正确，或先使用「查询图图 {work_id}」确认作品已生成～ (´∀｀)"""

        # 获取工作数据
        work_data = self.work_storage.get_work(work_id)
        title = work_data.get('title', '未知作品')
        total_images = len(work_data.get('image_urls', []))
        created_at = work_data.get('created_at', '')

        # 获取发布记录
        published_records = self.work_storage.get_published_records(work_id)

        if not published_records:
            return f"""📊 发布结果查询
🆔 工作ID: #{work_id}
🎨 作品标题: {title}
📸 包含图片: {total_images}张
📅 创建时间: {created_at[:19] if created_at else '未知'}

📋 发布状态: 暂未发布
💡 使用「发布图图 {work_id} 昵称 标题」来发布作品～ (´∀｀)"""

        # 格式化发布记录
        message = f"""📊 发布结果查询
🆔 工作ID: #{work_id}
🎨 作品标题: {title}
📸 包含图片: {total_images}张
📅 创建时间: {created_at[:19] if created_at else '未知'}

📋 发布记录 (共{len(published_records)}次):
"""

        for i, record in enumerate(published_records, 1):
            user_id = record.get('user_id', '未知用户')
            nickname = record.get('nickname', '未知昵称')
            publish_title = record.get('title', '未知标题')
            author = record.get('author', '未知作者')
            published_at = record.get('published_at', '')
            result = record.get('result', {})

            # 解析发布结果统计
            stats = result.get('processing_stats', {}) if isinstance(result, dict) else {}
            total_processed = stats.get('total_images', 0)
            uploaded_count = stats.get('uploaded_count', 0)
            successful_count = len(stats.get('successful_images', []))

            success_rate = f"{uploaded_count}/{total_processed}" if total_processed > 0 else "未知"

            message += f"""
🔖 发布记录 #{i}:
  👤 用户: {user_id}
  📱 昵称: {nickname}
  📝 标题: {publish_title}
  ✍️ 作者: {author}
  ⏰ 发布时间: {published_at[:19] if published_at else '未知'}
  📊 成功率: {success_rate}张图片上传成功"""

            if stats:
                failed_downloads = stats.get('failed_downloads', [])
                failed_uploads = stats.get('failed_uploads', [])
                if failed_downloads or failed_uploads:
                    message += f"\n  ⚠️ 失败详情:"
                    if failed_downloads:
                        message += f" 下载失败{len(failed_downloads)}张"
                    if failed_uploads:
                        message += f" 上传失败{len(failed_uploads)}张"

        message += "\n\n✨ 查询完成！详细的发布统计数据已显示～ (´∀｀)"
        return message

    def _handle_tutu_publish_query_help(self) -> str:
        """处理查询发布结果帮助信息"""
        return """📊 查询发布结果功能帮助

正确格式：
查询发布结果 工作ID

例如：
查询发布结果 e8bcd7eb6182101601067111e8d231a9

📝 使用说明：
• 工作ID：图图作品的工作ID
• 查看该作品的所有发布记录
• 显示详细的图片处理统计信息
• 包含成功率、失败原因等数据

💡 提示：
可以查看作品被发布到哪些公众号
以及每次发布时的图片转换情况

嘿嘿~ 用这个指令来查看你的发布历史记录吧！(´∀｀) 📊✨"""

