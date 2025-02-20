import os
import json
from typing import Dict, Any
import logging

class Config:
    DEFAULT_CONFIG = {
        'backup': {
            'sources': {},  # 备份源和目标路径映射
            'file_size_limit_mb': 100,  # 文件大小限制（MB）
            'incremental_days': 0,  # 增量备份天数，0表示完整备份
            'parallel': {
                'enabled': True,  # 是否启用并行处理
                'max_workers': None,  # None表示自动设置
                'small_file_size_mb': 10,  # 小文件阈值（MB）
                'batch_size': 100  # 小文件批处理数量
            }
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
                logging.debug(f"找到配置文件: {self.config_file}")
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logging.debug("成功读取配置文件")
                
                # 合并默认配置
                merged_config = self._merge_config(self.DEFAULT_CONFIG, config)
                logging.debug("配置合并完成")
                return merged_config
            else:
                logging.debug(f"配置文件不存在，创建默认配置: {self.config_file}")
                os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(self.DEFAULT_CONFIG, f, indent=4, ensure_ascii=False)
                logging.debug("默认配置文件创建成功")
                return self.DEFAULT_CONFIG
        except Exception as e:
            logging.error(f"加载配置文件失败: {str(e)}", exc_info=True)
            return self.DEFAULT_CONFIG

    def _merge_config(self, default: Dict, custom: Dict) -> Dict:
        """
        递归合并配置
        
        Args:
            default: 默认配置
            custom: 自定义配置

        Returns:
            Dict: 合并后的配置
        """
        result = default.copy()
        for key, value in custom.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
                if isinstance(value, dict):
                    logging.debug(f"更新配置项 {key}: {json.dumps(value, ensure_ascii=False)}")
                else:
                    logging.debug(f"更新配置项 {key}: {value}")
        logging.debug(f"合并后的配置: {json.dumps(result, indent=2, ensure_ascii=False)}")
        return result

    def _validate_config(self, config: Dict) -> bool:
        """验证配置有效性"""
        try:
            # 验证必需的配置项
            if 'backup' not in config:
                logging.error("缺少 'backup' 配置项")
                return False
            
            backup_config = config['backup']
            
            # 验证备份源配置
            if 'sources' not in backup_config or not isinstance(backup_config['sources'], dict):
                logging.error("备份源配置无效")
                return False
            
            # 验证文件大小限制
            size_limit = backup_config.get('file_size_limit_mb', 100)
            if not isinstance(size_limit, (int, float)) or size_limit <= 0:
                logging.error(f"文件大小限制无效: {size_limit}")
                return False
            
            # 验证增量备份天数
            inc_days = backup_config.get('incremental_days', 0)
            if not isinstance(inc_days, int) or inc_days < 0:
                logging.error(f"增量备份天数无效: {inc_days}")
                return False
            
            # 验证并行处理配置
            parallel = backup_config.get('parallel', {})
            if not isinstance(parallel, dict):
                logging.error("并行处理配置无效")
                return False
            
            return True
        except Exception as e:
            logging.error(f"配置验证失败: {str(e)}")
            return False

    def save_config(self) -> bool:
        """保存配置到文件"""
        try:
            # 验证配置有效性
            if not self._validate_config(self.config):
                return False
            
            # 创建备份
            backup_file = f"{self.config_file}.bak"
            if os.path.exists(self.config_file):
                try:
                    import shutil
                    shutil.copy2(self.config_file, backup_file)
                    logging.debug(f"创建配置文件备份: {backup_file}")
                except Exception as e:
                    logging.warning(f"创建配置备份失败: {str(e)}")
            
            # 保存新配置
            logging.debug(f"开始保存配置到文件: {self.config_file}")
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            try:
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(self.config, f, indent=4, ensure_ascii=False)
                logging.debug("配置保存成功")
                return True
            except Exception as e:
                # 保存失败，尝试恢复备份
                if os.path.exists(backup_file):
                    try:
                        import shutil
                        shutil.copy2(backup_file, self.config_file)
                        logging.info("已恢复配置文件备份")
                    except Exception as restore_error:
                        logging.error(f"恢复配置备份失败: {str(restore_error)}")
                logging.error(f"保存配置文件失败: {str(e)}")
                return False
            
        except Exception as e:
            logging.error(f"保存配置过程出错: {str(e)}", exc_info=True)
            return False

    def get_backup_sources(self) -> Dict[str, str]:
        """获取备份源和目标路径映射"""
        sources = self.config['backup']['sources']
        logging.debug(f"获取到备份源: {json.dumps(sources, ensure_ascii=False)}")
        return sources

    def get_file_size_limit(self) -> int:
        """获取文件大小限制（MB）"""
        limit = self.config['backup'].get('file_size_limit_mb', 100)
        logging.debug(f"获取到文件大小限制: {limit}MB")
        return limit

    def get_incremental_days(self) -> int:
        """获取增量备份天数"""
        days = self.config['backup'].get('incremental_days', 0)
        logging.debug(f"获取到增量备份天数: {days}")
        return days

    def get_parallel_config(self) -> dict:
        """获取并行处理配置"""
        parallel_config = self.config['backup'].get('parallel', self.DEFAULT_CONFIG['backup']['parallel'])
        logging.debug(f"获取到并行处理配置: {json.dumps(parallel_config, ensure_ascii=False)}")
        return parallel_config
 