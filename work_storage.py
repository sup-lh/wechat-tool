#!/usr/bin/env python3
"""
WorkStorage - 图图作品本地存储管理
管理WorkID到图片URLs的映射关系
"""
import json
import os
import time
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class WorkStorage:
    def __init__(self, storage_file: str = "tutu_works.json"):
        self.storage_file = storage_file
        self.data = self._load_data()

    def _load_data(self) -> Dict:
        """从文件加载数据"""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {}
        except Exception as e:
            logger.error(f"加载存储文件失败: {e}")
            return {}

    def _save_data(self) -> bool:
        """保存数据到文件"""
        try:
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            logger.info(f"数据已保存到 {self.storage_file}")
            return True
        except Exception as e:
            logger.error(f"保存存储文件失败: {e}")
            return False

    def save_work(self, work_id: str, title: str, shots_data: List[Dict]) -> bool:
        """
        保存工作数据

        Args:
            work_id: 工作ID
            title: 图片标题
            shots_data: 分镜数据列表

        Returns:
            保存是否成功
        """
        try:
            # 提取完成的分镜数据
            completed_shots = [shot for shot in shots_data if shot.get('status') == 'COMPLETED']

            if not completed_shots:
                logger.warning(f"工作 {work_id} 没有完成的分镜")
                return False

            # 构建存储数据
            work_data = {
                "title": title,
                "status": "COMPLETED",
                "created_at": datetime.now().isoformat(),
                "image_urls": [],
                "shot_descriptions": [],
                "shot_count": len(completed_shots)
            }

            # 提取图片URLs和描述
            for shot in completed_shots:
                image_url = shot.get('imageUrl', '')
                description = shot.get('finalPrompt', f"分镜{shot.get('shotIndex', 0)}")

                if image_url:
                    work_data["image_urls"].append(image_url)
                    work_data["shot_descriptions"].append(description)

            # 保存到内存
            self.data[work_id] = work_data

            # 保存到文件
            success = self._save_data()

            if success:
                logger.info(f"工作 {work_id} 已保存，包含 {len(work_data['image_urls'])} 张图片")

            return success

        except Exception as e:
            logger.error(f"保存工作数据失败: {e}")
            return False

    def get_work(self, work_id: str) -> Optional[Dict]:
        """
        获取工作数据

        Args:
            work_id: 工作ID

        Returns:
            工作数据字典，不存在时返回None
        """
        return self.data.get(work_id)

    def work_exists(self, work_id: str) -> bool:
        """检查工作是否存在"""
        return work_id in self.data

    def get_image_urls(self, work_id: str) -> List[str]:
        """获取工作的图片URLs"""
        work_data = self.get_work(work_id)
        if work_data:
            return work_data.get('image_urls', [])
        return []

    def get_shot_descriptions(self, work_id: str) -> List[str]:
        """获取工作的分镜描述"""
        work_data = self.get_work(work_id)
        if work_data:
            return work_data.get('shot_descriptions', [])
        return []

    def list_works(self) -> Dict[str, Dict]:
        """列出所有工作"""
        return self.data.copy()

    def clean_expired_works(self, days: int = 7) -> int:
        """
        清理过期的工作数据

        Args:
            days: 保留天数，默认7天

        Returns:
            清理的数量
        """
        try:
            cutoff_time = datetime.now() - timedelta(days=days)
            expired_works = []

            for work_id, work_data in self.data.items():
                created_at_str = work_data.get('created_at', '')
                try:
                    created_at = datetime.fromisoformat(created_at_str)
                    if created_at < cutoff_time:
                        expired_works.append(work_id)
                except ValueError:
                    # 如果时间格式有问题，也删除
                    expired_works.append(work_id)

            # 删除过期数据
            for work_id in expired_works:
                del self.data[work_id]

            if expired_works:
                self._save_data()
                logger.info(f"清理了 {len(expired_works)} 个过期工作")

            return len(expired_works)

        except Exception as e:
            logger.error(f"清理过期工作失败: {e}")
            return 0

    def delete_work(self, work_id: str) -> bool:
        """删除指定工作"""
        if work_id in self.data:
            del self.data[work_id]
            success = self._save_data()
            if success:
                logger.info(f"工作 {work_id} 已删除")
            return success
        return False

    def mark_as_published(self, work_id: str, user_id: str, nickname: str, title: str, author: str,
                         publish_result: Dict = None) -> bool:
        """
        标记工作为已发布，包含详细的发布结果

        Args:
            work_id: 工作ID
            user_id: 用户ID
            nickname: 公众号昵称
            title: 草稿标题
            author: 作者
            publish_result: 发布结果详情

        Returns:
            操作是否成功
        """
        try:
            if work_id not in self.data:
                return False

            # 初始化发布记录
            if 'published_records' not in self.data[work_id]:
                self.data[work_id]['published_records'] = []

            # 添加发布记录，包含详细信息
            publish_record = {
                "user_id": user_id,
                "nickname": nickname,
                "title": title,
                "author": author,
                "published_at": datetime.now().isoformat(),
                "result": publish_result or {}
            }

            self.data[work_id]['published_records'].append(publish_record)

            success = self._save_data()
            if success:
                logger.info(f"工作 {work_id} 发布记录已保存，用户: {user_id}, 标题: {title}")

            return success

        except Exception as e:
            logger.error(f"标记发布记录失败: {e}")
            return False

    def is_published(self, work_id: str, user_id: str, nickname: str, title: str) -> bool:
        """
        检查工作是否已经发布过（同用户同昵称同标题）

        Args:
            work_id: 工作ID
            user_id: 用户ID
            nickname: 公众号昵称
            title: 草稿标题

        Returns:
            是否已发布过
        """
        try:
            work_data = self.data.get(work_id)
            if not work_data:
                return False

            published_records = work_data.get('published_records', [])

            # 检查是否有相同的发布记录
            for record in published_records:
                if (record.get('user_id') == user_id and
                    record.get('nickname') == nickname and
                    record.get('title') == title):
                    return True

            return False

        except Exception as e:
            logger.error(f"检查发布记录失败: {e}")
            return False

    def get_published_records(self, work_id: str) -> List[Dict]:
        """获取工作的发布记录"""
        work_data = self.data.get(work_id)
        if work_data:
            return work_data.get('published_records', [])
        return []

    def get_storage_stats(self) -> Dict[str, int]:
        """获取存储统计信息"""
        total_works = len(self.data)
        total_images = sum(len(work.get('image_urls', [])) for work in self.data.values())

        return {
            "total_works": total_works,
            "total_images": total_images,
            "storage_file_size": os.path.getsize(self.storage_file) if os.path.exists(self.storage_file) else 0
        }