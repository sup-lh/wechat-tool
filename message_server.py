#!/usr/bin/env python3
"""
微信公众号消息监听服务器
实现消息接收、URL验证、自动回复等功能
"""
from flask import Flask, request, abort
import hashlib
import xml.etree.ElementTree as ET
from typing import Optional, Dict
import time
import logging
from config import ConfigManager
from command_processor import CommandProcessor

app = Flask(__name__)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('wechat_messages.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class WeChatMessageServer:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.token = "your_wechat_token"  # 默认token，会被动态设置
        self.command_processor = CommandProcessor()  # 指令处理器

    def validate_signature(self, signature: str, timestamp: str, nonce: str, token: str) -> bool:
        """验证微信服务器发送的签名"""
        logger.info(f"验证签名 - signature: {signature}, timestamp: {timestamp}, nonce: {nonce}, token: {token}")

        # 将token、timestamp、nonce三个参数进行字典序排序
        tmp_arr = [token, timestamp, nonce]
        tmp_arr.sort()
        logger.info(f"排序后参数: {tmp_arr}")

        # 将三个参数字符串拼接成一个字符串进行sha1加密
        tmp_str = ''.join(tmp_arr)
        logger.info(f"拼接字符串: {tmp_str}")

        tmp_str = hashlib.sha1(tmp_str.encode('utf-8')).hexdigest()
        logger.info(f"SHA1加密结果: {tmp_str}")

        # 比较加密后的字符串与signature
        result = tmp_str == signature
        logger.info(f"签名验证结果: {result}")
        return result

    def parse_xml_message(self, xml_data: str) -> Dict:
        """解析微信XML消息"""
        try:
            root = ET.fromstring(xml_data)
            message = {}

            # 提取基本信息
            message['ToUserName'] = root.find('ToUserName').text if root.find('ToUserName') is not None else ''
            message['FromUserName'] = root.find('FromUserName').text if root.find('FromUserName') is not None else ''
            message['CreateTime'] = root.find('CreateTime').text if root.find('CreateTime') is not None else ''
            message['MsgType'] = root.find('MsgType').text if root.find('MsgType') is not None else ''

            # 根据消息类型提取特定信息
            if message['MsgType'] == 'text':
                message['Content'] = root.find('Content').text if root.find('Content') is not None else ''
                message['MsgId'] = root.find('MsgId').text if root.find('MsgId') is not None else ''
            elif message['MsgType'] == 'image':
                message['PicUrl'] = root.find('PicUrl').text if root.find('PicUrl') is not None else ''
                message['MediaId'] = root.find('MediaId').text if root.find('MediaId') is not None else ''
                message['MsgId'] = root.find('MsgId').text if root.find('MsgId') is not None else ''
            elif message['MsgType'] == 'event':
                message['Event'] = root.find('Event').text if root.find('Event') is not None else ''
                if message['Event'] == 'subscribe':
                    message['EventKey'] = root.find('EventKey').text if root.find('EventKey') is not None else ''

            return message
        except Exception as e:
            logger.error(f"解析XML消息失败: {e}")
            return {}

    def create_text_reply(self, to_user: str, from_user: str, content: str) -> str:
        """创建文本回复消息"""
        reply_xml = f"""<xml>
<ToUserName><![CDATA[{to_user}]]></ToUserName>
<FromUserName><![CDATA[{from_user}]]></FromUserName>
<CreateTime>{int(time.time())}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[{content}]]></Content>
</xml>"""
        return reply_xml

    def handle_message(self, message: Dict) -> str:
        """处理接收到的消息并生成回复"""
        msg_type = message.get('MsgType', '')
        from_user = message.get('FromUserName', '')
        to_user = message.get('ToUserName', '')

        logger.info(f"收到消息 - 类型: {msg_type}, 来自: {from_user}")

        if msg_type == 'text':
            content = message.get('Content', '')
            logger.info(f"文本内容: {content}")

            # 使用指令处理器处理消息
            command, params = self.command_processor.parse_command(content)
            reply = self.command_processor.process_command(from_user, command, params)

            return self.create_text_reply(from_user, to_user, reply)

        elif msg_type == 'image':
            logger.info("收到图片消息")
            pic_url = message.get('PicUrl', '')
            media_id = message.get('MediaId', '')

            # 检查是否已处理过这个MediaId
            if self.command_processor.config_manager.is_media_processed(media_id):
                logger.info(f"MediaId {media_id} 已被处理过，忽略重复消息")
                return ""  # 返回空字符串，不回复

            # 检查用户是否处于封面选择状态
            user_state = self.command_processor.config_manager.get_user_state(from_user)
            if user_state and user_state.get('state') == 'cover_selection':
                # 标记MediaId为已处理
                self.command_processor.config_manager.mark_media_processed(media_id)
                logger.info(f"用户 {from_user} 处于封面选择状态，开始处理图片上传")

                # 立即处理图片并返回结果
                try:
                    logger.info("开始图片处理任务")
                    result = self.command_processor._handle_image_cover_selection(from_user, user_state, pic_url, media_id)
                    logger.info(f"图片处理完成，结果: {result[:100] if result else 'None'}...")

                    if result:
                        # 成功处理，返回结果和提醒
                        reply = f"🎉 图片处理完成！\r\n\r\n{result}\r\n\r\n📝 请前往微信公众平台后台的「素材管理」→「草稿箱」查看您的文章！(´∀｀) 💖"
                    else:
                        reply = "❌ 图片处理失败，请稍后重试～ (´∀｀)"

                except Exception as e:
                    logger.error(f"图片处理失败: {e}")
                    reply = "❌ 图片处理时发生错误，请稍后重试～ (´∀｀)"
            else:
                reply = "哇~ 收到一张图片呢！✨ 图片很棒哦～ 嘿嘿~ (´∀｀) 🎨"
                logger.info(f"普通图片消息，回复: {reply}")

            if reply:
                logger.info(f"准备发送图片消息回复，内容长度: {len(reply) if reply else 0}")
                return self.create_text_reply(from_user, to_user, reply)
            else:
                logger.warning("图片处理后回复内容为空，不发送回复")
                return ""

        elif msg_type == 'event':
            event = message.get('Event', '')
            if event == 'subscribe':
                logger.info("新用户关注")
                reply = """欢迎关注「不存在的画廊」的公众号！🎉

嘿嘿~ 这里是一个用 Python 开发的智能公众号呢！(´∀｀) 💖

🌟 主要功能：
- 📱 通过微信消息管理公众号配置
- 📝 直接发布文章到草稿箱
- 🔧 实时配置测试和管理
- 💬 智能消息回复

发送"帮助"了解更多功能吧～ \\(^o^)/

管理员可发送 "/admin 密码" 获取高级权限！"""
                return self.create_text_reply(from_user, to_user, reply)

        # 默认回复
        logger.info(f"未处理的消息类型: {msg_type}")
        return ""

# 创建全局服务器实例
message_server = WeChatMessageServer()

@app.route('/wechat', methods=['GET', 'POST'])
def wechat_handler():
    """微信消息处理接口"""
    if request.method == 'GET':
        # URL验证
        signature = request.args.get('signature', '')
        timestamp = request.args.get('timestamp', '')
        nonce = request.args.get('nonce', '')
        echostr = request.args.get('echostr', '')

        # 使用配置的Token
        token = message_server.token

        if message_server.validate_signature(signature, timestamp, nonce, token):
            logger.info("URL验证成功")
            return echostr
        else:
            logger.error("URL验证失败")
            abort(403)

    elif request.method == 'POST':
        # 处理消息
        xml_data = request.data.decode('utf-8')
        logger.info(f"收到POST请求，数据: {xml_data}")

        # 解析消息
        message = message_server.parse_xml_message(xml_data)
        if not message:
            logger.error("消息解析失败")
            return ""

        # 处理消息并生成回复
        reply = message_server.handle_message(message)

        if reply:
            logger.info(f"发送回复: {reply}")
            return reply, 200, {'Content-Type': 'application/xml'}
        else:
            return "", 200

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "message": "微信公众号消息服务器运行正常 (´∀｀) 💖"
    }

if __name__ == '__main__':
    logger.info("启动微信消息监听服务器...")
    logger.info("URL验证地址: http://your-domain.com/wechat")
    logger.info("健康检查地址: http://localhost:5000/health")

    # 在生产环境中，建议使用 gunicorn 等 WSGI 服务器
    app.run(host='0.0.0.0', port=5000, debug=True)