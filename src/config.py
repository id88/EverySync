import os
import json
from typing import Dict, Any

class Config:
    DEFAULT_CONFIG = {
        'backup': {
            'sources': {},  # 备份源和目标路径映射
            'exclude_patterns': {  # 排除规则
                'directories': [],  # 要排除的目录
                'files': []  # 要排除的文件
            },
            'file_size_limit': 100,  # 文件大小限制（MB）
            'incremental_days': 0,  # 增量备份天数，0表示完整备份
            'verification_sample_size': 2  # 验证时的样本大小
        },
        'log': {
            'level': 'DEBUG',
            'format': '%(asctime)s - %(levelname)s - %(message)s'
        }
    }

    def __init__(self, config_file: str = 'config/config.json'):
        """初始化配置管理器"""
        self.config_file = config_file
        self.config = self.load_config()

    def load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # 合并默认配置
                return self._merge_config(self.DEFAULT_CONFIG, config)
            else:
                # 如果配置文件不存在，创建默认配置
                os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(self.DEFAULT_CONFIG, f, indent=4, ensure_ascii=False)
                return self.DEFAULT_CONFIG
        except Exception as e:
            print(f"加载配置文件失败: {str(e)}")
            return self.DEFAULT_CONFIG

    def _merge_config(self, default: Dict, custom: Dict) -> Dict:
        """合并配置"""
        result = default.copy()
        for key, value in custom.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        return result

    def save_config(self) -> bool:
        """保存配置到文件"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"保存配置文件失败: {str(e)}")
            return False

    def get_backup_sources(self) -> Dict[str, str]:
        """获取备份源和目标路径映射"""
        return self.config['backup']['sources']

    def get_exclude_patterns(self) -> Dict[str, list]:
        """获取排除规则"""
        return self.config['backup']['exclude_patterns']

    def get_file_size_limit(self) -> int:
        """获取文件大小限制（MB）"""
        return self.config['backup']['file_size_limit']

    def get_incremental_days(self) -> int:
        """获取增量备份天数"""
        return self.config['backup']['incremental_days']

    def get_verification_sample_size(self) -> int:
        """获取验证样本大小"""
        return self.config['backup']['verification_sample_size'] 