"""
微信公众号API模块
实现公众号绑定验证、素材上传和草稿箱发布功能
"""
import requests
import json
import os
import tempfile
import random
import re
from typing import Optional, Dict, Any, List
# from PIL import Image, ImageDraw, ImageFont  # 临时注释掉
from io import BytesIO

class WeChatAPI:
    def __init__(self):
        self.base_url = "https://api.weixin.qq.com"

    def translate_to_english(self, text: str) -> str:
        """将中文翻译为英文（使用简单的翻译服务）"""
        try:
            # 如果已经是英文，直接返回
            if re.match(r'^[a-zA-Z0-9\s\.\,\!\?\-\_]+$', text):
                return text

            # 使用简单的词汇映射翻译（避免外部API依赖）
            translation_dict = {
                '今日': 'Today', '资讯': 'News', '新闻': 'News', '消息': 'Message',
                '通知': 'Notice', '公告': 'Announcement', '更新': 'Update',
                '科技': 'Technology', '技术': 'Tech', '数码': 'Digital',
                '生活': 'Life', '健康': 'Health', '美食': 'Food',
                '旅游': 'Travel', '音乐': 'Music', '电影': 'Movie',
                '游戏': 'Game', '体育': 'Sports', '财经': 'Finance',
                '教育': 'Education', '文化': 'Culture', '艺术': 'Art',
                '时尚': 'Fashion', '汽车': 'Car', '房产': 'Real Estate',
                '特朗普': 'Trump', '拜登': 'Biden', '中国': 'China',
                '美国': 'USA', '日本': 'Japan', '韩国': 'Korea',
                '测试': 'Test', '文章': 'Article', '内容': 'Content',
                '标题': 'Title', '封面': 'Cover', '图片': 'Image'
            }

            # 尝试翻译文本中的中文词汇
            translated_text = text
            for chinese, english in translation_dict.items():
                if chinese in translated_text:
                    translated_text = translated_text.replace(chinese, english)

            # 如果翻译后还有中文，使用拼音或简化版本
            if re.search(r'[\u4e00-\u9fff]', translated_text):
                # 简化处理：如果还有中文，就使用原标题的前10个字符
                translated_text = f"Article_{random.randint(1000, 9999)}"

            # 确保不超过适合显示的长度
            if len(translated_text) > 20:
                translated_text = translated_text[:17] + "..."

            return translated_text

        except Exception as e:
            print(f"翻译失败: {e}")
            return f"Cover_{random.randint(1000, 9999)}"

    def get_access_token(self, appid: str, secret: str) -> Optional[str]:
        """获取访问令牌，用于验证公众号配置是否正确"""
        url = f"{self.base_url}/cgi-bin/token"
        params = {
            "grant_type": "client_credential",
            "appid": appid,
            "secret": secret
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            if "access_token" in data:
                return data["access_token"]
            else:
                print(f"获取access_token失败: {data.get('errmsg', '未知错误')}")
                return None

        except Exception as e:
            print(f"请求失败: {e}")
            return None

    def validate_wechat_config(self, appid: str, secret: str) -> bool:
        """验证微信公众号配置是否正确"""
        access_token = self.get_access_token(appid, secret)
        return access_token is not None

    def generate_temp_image(self, text: str = "测试图片", title: str = "") -> str:
        """生成临时图片，优先使用现有的demo.jpg，否则创建简单图片"""
        demo_path = "demo.jpg"
        if os.path.exists(demo_path):
            return demo_path

        # 如果demo.jpg不存在，创建一个简单的默认图片
        try:
            from PIL import Image, ImageDraw, ImageFont

            # 创建一个简单的封面图片
            img = Image.new('RGB', (300, 200), color='#4a90e2')
            draw = ImageDraw.Draw(img)

            # 尝试使用默认字体，但避免中文编码问题
            try:
                # 在不同系统上尝试找到字体
                font = ImageFont.load_default()
            except:
                font = None

            # 在图片上绘制文字 - 使用翻译后的标题
            if title:
                text_to_draw = self.translate_to_english(title)
            else:
                text_to_draw = "Cover Image"  # 默认封面文字
            try:
                if font:
                    # 计算文字位置（居中）
                    bbox = draw.textbbox((0, 0), text_to_draw, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                    x = (300 - text_width) // 2
                    y = (200 - text_height) // 2
                    draw.text((x, y), text_to_draw, fill='white', font=font)
                else:
                    # 如果没有字体，绘制简单的形状
                    draw.rectangle([50, 75, 250, 125], fill='white')
            except UnicodeEncodeError:
                # 如果仍有编码问题，直接绘制形状
                draw.rectangle([50, 75, 250, 125], fill='white')
                draw.ellipse([125, 85, 175, 135], fill='#4a90e2')

            # 保存临时图片
            temp_path = "temp_cover.jpg"
            img.save(temp_path, 'JPEG')
            return temp_path

        except ImportError:
            # 如果没有PIL库，创建一个最小的占位符图片
            # 创建一个1x1像素的最小JPEG文件
            temp_path = "temp_cover.jpg"
            with open(temp_path, 'wb') as f:
                # 写入一个最小的JPEG文件头和数据
                minimal_jpeg = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\xaa\xff\xd9'
                f.write(minimal_jpeg)
            return temp_path

    def download_wechat_image(self, access_token: str, media_id: str) -> Optional[str]:
        """从微信服务器下载图片"""
        url = f"{self.base_url}/cgi-bin/media/get"
        params = {
            "access_token": access_token,
            "media_id": media_id
        }

        try:
            response = requests.get(url, params=params, timeout=30)

            if response.status_code == 200:
                # 保存临时文件
                temp_path = f"temp_user_image_{random.randint(1000, 9999)}.jpg"
                with open(temp_path, 'wb') as f:
                    f.write(response.content)
                print(f"✅ 微信图片下载成功: {temp_path}")
                return temp_path
            else:
                print(f"❌ 下载微信图片失败: {response.status_code}")
                return None

        except Exception as e:
            print(f"下载微信图片时发生错误: {e}")
            return None

    def upload_material(self, access_token: str, image_path: str, material_type: str = "image") -> Optional[str]:
        """上传永久素材"""
        url = f"{self.base_url}/cgi-bin/material/add_material"
        params = {
            "access_token": access_token,
            "type": material_type
        }

        try:
            with open(image_path, 'rb') as f:
                files = {
                    'media': (os.path.basename(image_path), f, 'image/png')
                }

                response = requests.post(url, params=params, files=files, timeout=30)
                data = response.json()

                if "media_id" in data:
                    print(f"素材上传成功! media_id: {data['media_id']}")
                    return data["media_id"]
                else:
                    print(f"素材上传失败: {data.get('errmsg', '未知错误')}")
                    return None

        except Exception as e:
            print(f"上传素材时发生错误: {e}")
            return None

    def add_draft(self, access_token: str, title: str, content: str, thumb_media_id: str,
                  author: str = "不存在的画廊", digest: str = "") -> Optional[str]:
        """添加草稿"""
        url = f"{self.base_url}/cgi-bin/draft/add"
        params = {"access_token": access_token}

        # 如果没有提供摘要，则使用内容的前50个字符
        if not digest:
            digest = content[:50] + "..." if len(content) > 50 else content

        data = {
            "articles": [{
                "title": title,
                "author": author,
                "digest": digest,
                "content": content,
                "content_source_url": "",
                "thumb_media_id": thumb_media_id,
                "show_cover_pic": 1,
                "need_open_comment": 0,
                "only_fans_can_comment": 0
            }]
        }

        try:
            response = requests.post(
                url,
                params=params,
                data=json.dumps(data, ensure_ascii=False).encode('utf-8'),
                headers={'Content-Type': 'application/json; charset=utf-8'},
                timeout=30
            )

            result = response.json()

            if "media_id" in result:
                print(f"草稿添加成功! media_id: {result['media_id']}")
                return result["media_id"]
            else:
                print(f"草稿添加失败: {result.get('errmsg', '未知错误')}")
                return None

        except Exception as e:
            print(f"添加草稿时发生错误: {e}")
            return None

    def publish_to_draft(self, appid: str, secret: str, title: str = "测试文章",
                        content: str = "这是一篇测试文章的内容", author: str = "不存在的画廊",
                        thumb_media_id: str = None) -> bool:
        """完整的发布到草稿箱流程"""
        print("🚀 开始发布流程...")

        # 1. 获取access_token
        print("📝 获取访问令牌...")
        access_token = self.get_access_token(appid, secret)
        if not access_token:
            print("❌ 获取access_token失败")
            return False

        # 2. 准备封面素材
        if thumb_media_id:
            # 使用传入的MediaId
            print("🎨 使用用户提供的封面图片...")
            media_id = thumb_media_id
        else:
            # 生成默认封面
            print("🎨 生成默认封面图片...")
            temp_image_path = self.generate_temp_image(f"封面图片 - {title}", title)

            try:
                # 3. 上传素材
                print("📤 上传封面图片...")
                media_id = self.upload_material(access_token, temp_image_path)
                if not media_id:
                    print("❌ 上传素材失败")
                    return False
            finally:
                # 清理临时文件
                if temp_image_path and os.path.exists(temp_image_path) and temp_image_path != "demo.jpg":
                    os.unlink(temp_image_path)

        try:
            # 4. 添加草稿
            print("📄 添加到草稿箱...")
            draft_media_id = self.add_draft(access_token, title, content, media_id, author)
            if not draft_media_id:
                print("❌ 添加草稿失败")
                return False

            print("✅ 发布到草稿箱成功!")
            return True

        finally:
            # 清理临时文件（只清理非用户封面的默认生成文件）
            if not thumb_media_id:  # 只有使用默认封面时才清理
                if 'temp_image_path' in locals() and temp_image_path and os.path.exists(temp_image_path) and temp_image_path != "demo.jpg":
                    os.unlink(temp_image_path)
                    print("🧹 已清理临时文件")

    def send_customer_message(self, access_token: str, openid: str, content: str) -> bool:
        """发送客服消息"""
        url = f"{self.base_url}/cgi-bin/message/custom/send"
        params = {"access_token": access_token}

        data = {
            "touser": openid,
            "msgtype": "text",
            "text": {
                "content": content
            }
        }

        try:
            response = requests.post(
                url,
                params=params,
                data=json.dumps(data, ensure_ascii=False).encode('utf-8'),
                headers={'Content-Type': 'application/json; charset=utf-8'},
                timeout=10
            )
            result = response.json()

            print(f"客服消息API响应: {result}")  # 添加详细日志

            if result.get('errcode') == 0:
                print(f"✅ 客服消息发送成功: {openid}")
                return True
            else:
                error_code = result.get('errcode', '未知')
                error_msg = result.get('errmsg', '未知错误')
                print(f"❌ 客服消息发送失败: 错误码 {error_code}, 错误信息: {error_msg}, 用户: {openid}")

                # 常见错误码说明
                if error_code == 45015:
                    print("提示: 回复时间超过48小时限制，用户需要在48小时内主动发送过消息才能接收客服消息")
                elif error_code == 40001:
                    print("提示: access_token失效或错误")
                elif error_code == 40013:
                    print("提示: 用户拒绝接收消息或openid无效")

                return False

        except Exception as e:
            print(f"发送客服消息时发生错误: {e}")
            return False

    def download_image_from_url(self, image_url: str) -> Optional[str]:
        """
        从URL下载图片到本地临时文件

        Args:
            image_url: 图片URL

        Returns:
            临时文件路径，失败时返回None
        """
        try:
            print(f"📥 开始下载图片: {image_url}")

            # 发送GET请求下载图片
            response = requests.get(image_url, timeout=30)

            if response.status_code == 200:
                # 创建临时文件
                temp_path = f"temp_downloaded_image_{random.randint(1000, 9999)}.jpg"

                with open(temp_path, 'wb') as f:
                    f.write(response.content)

                print(f"✅ 图片下载成功: {temp_path}")
                return temp_path
            else:
                print(f"❌ 图片下载失败 - 状态码: {response.status_code}")
                return None

        except requests.exceptions.Timeout:
            print("❌ 图片下载超时")
            return None
        except requests.exceptions.RequestException as e:
            print(f"❌ 图片下载异常: {e}")
            return None
        except Exception as e:
            print(f"❌ 图片下载发生未知错误: {e}")
            return None

    def upload_images_to_material(self, access_token: str, image_urls: List[str]) -> List[Dict[str, str]]:
        """
        批量上传图片到永久素材库

        Args:
            access_token: 微信访问令牌
            image_urls: 图片URL列表

        Returns:
            上传结果列表，每个元素包含 {'url': str, 'media_id': str, 'success': bool, 'error': str}
        """
        results = []

        for i, image_url in enumerate(image_urls, 1):
            result = {
                'url': image_url,
                'media_id': '',
                'success': False,
                'error': ''
            }

            try:
                print(f"📤 上传第 {i}/{len(image_urls)} 张图片...")

                # 下载图片
                temp_path = self.download_image_from_url(image_url)

                if temp_path:
                    # 上传到永久素材库
                    media_id = self.upload_material(access_token, temp_path)

                    if media_id:
                        result['media_id'] = media_id
                        result['success'] = True
                        print(f"✅ 第 {i} 张图片上传成功: {media_id}")
                    else:
                        result['error'] = "上传到素材库失败"
                        print(f"❌ 第 {i} 张图片上传到素材库失败")

                    # 清理临时文件
                    try:
                        if os.path.exists(temp_path):
                            os.unlink(temp_path)
                    except Exception as e:
                        print(f"⚠️ 清理临时文件失败: {e}")

                else:
                    result['error'] = "图片下载失败"
                    print(f"❌ 第 {i} 张图片下载失败")

            except Exception as e:
                result['error'] = str(e)
                print(f"❌ 第 {i} 张图片处理失败: {e}")

            results.append(result)

        return results

    def format_upload_results(self, results: List[Dict[str, str]], work_id: str) -> str:
        """
        格式化批量上传结果为用户友好的消息

        Args:
            results: 上传结果列表
            work_id: 工作ID

        Returns:
            格式化后的消息字符串
        """
        successful_uploads = [r for r in results if r['success']]
        failed_uploads = [r for r in results if not r['success']]

        message = f"""📸 图图作品上传完成！

🆔 工作ID: {work_id}
📊 上传结果: {len(successful_uploads)}/{len(results)} 成功

"""

        if successful_uploads:
            message += "✅ 上传成功的图片：\n"
            for i, result in enumerate(successful_uploads, 1):
                media_id = result['media_id']
                message += f"🎬 分镜{i}: {media_id}\n"
            message += "\n"

        if failed_uploads:
            message += f"❌ {len(failed_uploads)} 张图片上传失败：\n"
            for i, result in enumerate(failed_uploads, 1):
                error = result.get('error', '未知错误')
                message += f"• 图片{i}: {error}\n"
            message += "\n"

        if successful_uploads:
            message += """💡 使用说明：
• 这些 media_id 可以用于发布文章时作为封面或插图
• 图片已保存到您的微信公众号永久素材库
• 可在公众平台后台「素材管理」中查看

嘿嘿~ 图片上传完成啦！(´∀｀) 🎨✨"""
        else:
            message += "😅 所有图片都上传失败了，请检查网络连接或稍后重试～"

        return message