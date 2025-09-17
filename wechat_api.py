"""
微信公众号API模块
实现公众号绑定验证、素材上传和草稿箱发布功能
"""
import requests
import json
import os
import tempfile
import random
from typing import Optional, Dict, Any
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

class WeChatAPI:
    def __init__(self):
        self.base_url = "https://api.weixin.qq.com"

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

    def generate_temp_image(self, text: str = "测试图片") -> str:
        """生成临时测试图片"""
        # 创建一个简单的测试图片
        width, height = 800, 600
        image = Image.new('RGB', (width, height), color='lightblue')
        draw = ImageDraw.Draw(image)

        # 尝试使用系统字体，如果没有就使用默认字体
        try:
            font = ImageFont.truetype("arial.ttf", 36)
        except:
            font = ImageFont.load_default()

        # 添加随机颜色
        colors = ['red', 'green', 'blue', 'orange', 'purple', 'brown']
        color = random.choice(colors)

        # 添加文字
        draw.text((50, 50), text, fill=color, font=font)
        draw.text((50, 150), f"随机数: {random.randint(1000, 9999)}", fill='black', font=font)

        # 保存到临时文件
        temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        image.save(temp_file.name, 'PNG')
        temp_file.close()

        return temp_file.name

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
                  author: str = "测试作者", digest: str = "") -> Optional[str]:
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
                        content: str = "这是一篇测试文章的内容") -> bool:
        """完整的发布到草稿箱流程"""
        print("🚀 开始发布流程...")

        # 1. 获取access_token
        print("📝 获取访问令牌...")
        access_token = self.get_access_token(appid, secret)
        if not access_token:
            print("❌ 获取access_token失败")
            return False

        # 2. 生成临时图片
        print("🎨 生成临时测试图片...")
        temp_image_path = self.generate_temp_image(f"封面图片 - {title}")

        try:
            # 3. 上传素材
            print("📤 上传封面图片...")
            media_id = self.upload_material(access_token, temp_image_path)
            if not media_id:
                print("❌ 上传素材失败")
                return False

            # 4. 添加草稿
            print("📄 添加到草稿箱...")
            draft_media_id = self.add_draft(access_token, title, content, media_id)
            if not draft_media_id:
                print("❌ 添加草稿失败")
                return False

            print("✅ 发布到草稿箱成功!")
            return True

        finally:
            # 清理临时文件
            if os.path.exists(temp_image_path):
                os.unlink(temp_image_path)
                print("🧹 已清理临时文件")