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

    def save_wx_config(self, name: str, appid: str, secret: str) -> bool:
        """保存微信公众号配置"""
        try:
            self.config_data[name] = {
                "appid": appid,
                "secret": secret
            }
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