"""
配置管理模块
用于管理微信公众号的配置信息
"""
import json
import os
from typing import Dict, Optional

class ConfigManager:
    def __init__(self, config_file: str = "wx_config.json"):
        self.config_file = config_file
        self.config_data = self._load_config()
        # 用户状态管理（临时存储，重启后清空）
        self.user_states = {}
        # 已处理的图片MediaId（避免重复处理）
        self.processed_media_ids = set()

    def _load_config(self) -> Dict:
        """加载配置文件"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _save_config(self):
        """保存配置到文件"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config_data, f, ensure_ascii=False, indent=2)

    def save_wx_config(self, name: str, appid: str, secret: str, token: str = None) -> bool:
        """保存微信公众号配置"""
        try:
            config = {
                "appid": appid,
                "secret": secret
            }
            if token:
                config["token"] = token

            self.config_data[name] = config
            self._save_config()
            return True
        except Exception as e:
            print(f"保存配置失败: {e}")
            return False

    def get_wx_config(self, name: str) -> Optional[Dict[str, str]]:
        """获取微信公众号配置"""
        return self.config_data.get(name)

    def list_configs(self) -> Dict:
        """列出所有配置"""
        return self.config_data

    def delete_config(self, name: str) -> bool:
        """删除配置"""
        if name in self.config_data:
            del self.config_data[name]
            self._save_config()
            return True
        return False

    # 用户隔离配置方法
    def save_user_config(self, user_id: str, nickname: str, appid: str, secret: str) -> bool:
        """保存用户专属配置"""
        try:
            # 确保用户配置目录存在
            if 'user_configs' not in self.config_data:
                self.config_data['user_configs'] = {}
            if user_id not in self.config_data['user_configs']:
                self.config_data['user_configs'][user_id] = {}

            config = {
                "appid": appid,
                "secret": secret
            }

            self.config_data['user_configs'][user_id][nickname] = config
            self._save_config()
            return True
        except Exception as e:
            print(f"保存用户配置失败: {e}")
            return False

    def get_user_config(self, user_id: str, nickname: str) -> Optional[Dict[str, str]]:
        """获取用户专属配置"""
        user_configs = self.config_data.get('user_configs', {})
        user_data = user_configs.get(user_id, {})
        return user_data.get(nickname)

    def list_user_configs(self, user_id: str) -> Dict:
        """列出用户的所有配置"""
        user_configs = self.config_data.get('user_configs', {})
        return user_configs.get(user_id, {})

    def delete_user_config(self, user_id: str, nickname: str) -> bool:
        """删除用户配置"""
        if 'user_configs' in self.config_data and user_id in self.config_data['user_configs']:
            user_data = self.config_data['user_configs'][user_id]
            if nickname in user_data:
                del user_data[nickname]
                self._save_config()
                return True
        return False

    def check_user_permission(self, user_id: str, nickname: str) -> bool:
        """检查用户是否有权限使用指定的配置"""
        user_configs = self.config_data.get('user_configs', {})
        user_data = user_configs.get(user_id, {})
        return nickname in user_data

    def get_user_config_count(self, user_id: str) -> int:
        """获取用户的配置数量"""
        user_configs = self.config_data.get('user_configs', {})
        user_data = user_configs.get(user_id, {})
        return len(user_data)

    # 用户状态管理方法
    def set_user_state(self, user_id: str, state: str, data: Dict = None) -> None:
        """设置用户状态"""
        self.user_states[user_id] = {
            'state': state,
            'data': data or {},
            'timestamp': __import__('time').time()
        }

    def get_user_state(self, user_id: str) -> Optional[Dict]:
        """获取用户状态"""
        if user_id in self.user_states:
            # 检查状态是否过期（5分钟后过期）
            current_time = __import__('time').time()
            if current_time - self.user_states[user_id].get('timestamp', 0) > 300:
                del self.user_states[user_id]
                return None
            return self.user_states[user_id]
        return None

    def clear_user_state(self, user_id: str) -> None:
        """清除用户状态"""
        if user_id in self.user_states:
            del self.user_states[user_id]

    def is_media_processed(self, media_id: str) -> bool:
        """检查MediaId是否已被处理"""
        return media_id in self.processed_media_ids

    def mark_media_processed(self, media_id: str) -> None:
        """标记MediaId为已处理"""
        self.processed_media_ids.add(media_id)
        # 限制集合大小，避免内存泄漏
        if len(self.processed_media_ids) > 1000:
            # 清理一半旧的记录
            old_ids = list(self.processed_media_ids)[:500]
            for old_id in old_ids:
                self.processed_media_ids.discard(old_id)