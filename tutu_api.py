#!/usr/bin/env python3
"""
图图API调用模块
用于调用远程图片生成服务
"""
import requests
import json
import logging
import random
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

class TutuAPI:
    def __init__(self):
        self.api_url = "https://tutu.aismrti.com/api/v1/supertutu/creation/workspace"
        self.api_key = "5L2g5aW95LiW55WM5oiR5LiN55-l6YGT55qE5L2g5aW9IA"
        self.headers = {
            'x-api-key': self.api_key,
            'Content-Type': 'application/json'
        }

        # 固定参数
        self.fixed_params = {
            "workspaceId": 2,
            "shotCount": 4,
            "quickMode": True,
            "seed": "123123"
        }

    def create_image(self, title: str, plot: str) -> Optional[Dict]:
        """
        调用图图API创建图片

        Args:
            title: 图片标题
            plot: 图片描述/情节

        Returns:
            API响应结果，成功时返回字典，失败时返回None
        """
        try:
            # 准备请求数据
            data = self.fixed_params.copy()
            data.update({
                "title": title,
                "plot": plot
            })

            logger.info(f"调用图图API - 标题: {title}, 描述: {plot}")
            logger.info(f"请求数据: {json.dumps(data, ensure_ascii=False)}")

            # 发送POST请求
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=data,
                timeout=30
            )

            logger.info(f"API响应状态码: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                logger.info(f"API调用成功: {json.dumps(result, ensure_ascii=False)}")
                return result
            else:
                logger.error(f"API调用失败 - 状态码: {response.status_code}, 响应: {response.text}")
                return None

        except requests.exceptions.Timeout:
            logger.error("API调用超时")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"API调用异常: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"API响应解析失败: {e}")
            return None
        except Exception as e:
            logger.error(f"图图API调用发生未知错误: {e}")
            return None

    def format_api_response(self, result: Dict, title: str, plot: str) -> str:
        """
        格式化API响应为用户友好的消息

        Args:
            result: API响应结果
            title: 原始标题
            plot: 原始描述

        Returns:
            格式化后的消息字符串
        """
        if not result:
            return "❌ 图片生成失败，请稍后重试～"

        # 提取响应信息
        message = result.get('message', '图片生成中...')
        code = result.get('code', 0)
        data = result.get('data', {})

        if code == 200 and data:
            task_id = data.get('id', '')
            status = data.get('status', 'UNKNOWN')

            success_message = f"""✅ {message}

🎨 标题: {title}
📝 描述: {plot}
🔢 生成数量: {self.fixed_params['shotCount']}张
⚡ 快速模式: {'开启' if self.fixed_params['quickMode'] else '关闭'}
📋 任务ID: #{task_id}
🔄 状态: {status}

🔗 请稍等片刻，图片正在生成中...
"""
            return success_message
        else:
            return f"❌ 图片生成请求失败: {message}"

    def get_work_shots(self, work_id: str) -> Optional[Dict]:
        """
        查询指定工作ID的图片分镜

        Args:
            work_id: 工作ID

        Returns:
            API响应结果，成功时返回字典，失败时返回None
        """
        try:
            # 构建查询URL
            query_url = f"https://tutu.aismrti.com/api/v1/supertutu/work/{work_id}/shots"

            headers = {
                'x-api-key': self.api_key
            }

            logger.info(f"查询图图作品分镜 - 工作ID: {work_id}")

            # 发送GET请求
            response = requests.get(
                query_url,
                headers=headers,
                timeout=30
            )

            logger.info(f"查询API响应状态码: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                logger.info(f"查询API调用成功: {json.dumps(result, ensure_ascii=False)}")
                return result
            else:
                logger.error(f"查询API调用失败 - 状态码: {response.status_code}, 响应: {response.text}")
                return None

        except requests.exceptions.Timeout:
            logger.error("查询API调用超时")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"查询API调用异常: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"查询API响应解析失败: {e}")
            return None
        except Exception as e:
            logger.error(f"查询图图API发生未知错误: {e}")
            return None

    def download_image_from_url(self, image_url: str) -> Optional[str]:
        """
        从URL下载图片到本地临时文件

        Args:
            image_url: 图片URL

        Returns:
            临时文件路径，失败时返回None
        """
        try:
            logger.info(f"下载图片: {image_url}")

            # 发送GET请求下载图片
            response = requests.get(image_url, timeout=30)

            if response.status_code == 200:
                # 创建临时文件
                temp_path = f"temp_tutu_image_{random.randint(1000, 9999)}.jpg"

                with open(temp_path, 'wb') as f:
                    f.write(response.content)

                logger.info(f"图片下载成功: {temp_path}")
                return temp_path
            else:
                logger.error(f"图片下载失败 - 状态码: {response.status_code}")
                return None

        except requests.exceptions.Timeout:
            logger.error("图片下载超时")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"图片下载异常: {e}")
            return None
        except Exception as e:
            logger.error(f"图片下载发生未知错误: {e}")
            return None

    def format_shots_response(self, shots_data: List[Dict], work_id: str) -> str:
        """
        格式化分镜数据为用户友好的消息

        Args:
            shots_data: 分镜数据列表
            work_id: 工作ID

        Returns:
            格式化后的消息字符串
        """
        if not shots_data:
            return f"❌ 未找到工作ID {work_id} 的分镜数据"

        # 统计完成状态
        completed_shots = [shot for shot in shots_data if shot.get('status') == 'COMPLETED']
        total_shots = len(shots_data)
        completed_count = len(completed_shots)

        message = f"""📸 图图作品分镜查询结果

🆔 工作ID: #{work_id}
📊 进度: {completed_count}/{total_shots} 已完成

"""

        if completed_count > 0:
            message += "✅ 已完成的分镜：\n"
            for shot in completed_shots:
                shot_index = shot.get('shotIndex', 0)
                image_url = shot.get('imageUrl', '')
                final_prompt = shot.get('finalPrompt', '无描述')

                # 截取描述的前50个字符
                short_prompt = final_prompt[:50] + "..." if len(final_prompt) > 50 else final_prompt

                message += f"🎬 分镜{shot_index}: {short_prompt}\n"
                message += f"🔗 图片: {image_url}\n\n"

        # 检查是否有未完成的分镜
        pending_shots = [shot for shot in shots_data if shot.get('status') != 'COMPLETED']
        if pending_shots:
            message += f"⏳ 还有 {len(pending_shots)} 个分镜正在生成中...\n\n"

        if completed_count > 0:
            message += "✨ 图片生成完成！您可以复制图片链接使用～"
        else:
            message += "⏰ 图片还在生成中，请稍后再查询～"

        return message