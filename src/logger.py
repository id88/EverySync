import os
import logging
from datetime import datetime
from typing import Optional

class Logger:
    def __init__(self, config: dict):
        """初始化日志管理器"""
        self.config = config
        self.setup_logging()

    def setup_logging(self):
        """设置日志配置"""
        # 确保日志目录存在
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)

        # 配置根日志记录器
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                # 调试日志文件处理器
                logging.FileHandler(
                    os.path.join(log_dir, "debug.log"),
                    encoding='utf-8'
                ),
                # 运行日志文件处理器
                logging.FileHandler(
                    os.path.join(log_dir, "run.log"),
                    encoding='utf-8'
                ),
                # 控制台处理器
                logging.StreamHandler()
            ]
        )

    def log_backup(self, source: str, dest: str, status: str = "开始"):
        """记录备份操作"""
        if os.path.isfile(source):
            size = os.path.getsize(source)
            size_str = self.format_size(size)
            msg = f"[备份{status}] {source} -> {dest} (大小: {size_str})"
        else:
            msg = f"[备份{status}] {source} -> {dest} (目录)"
        
        logging.info(msg)

    def log_error(self, message: str, exc_info: bool = False):
        """记录错误信息"""
        logging.error(message, exc_info=exc_info)

    def log_warning(self, message: str):
        """记录警告信息"""
        logging.warning(message)

    def log_info(self, message: str):
        """记录一般信息"""
        logging.info(message)

    def log_debug(self, message: str):
        """记录调试信息"""
        logging.debug(message)

    @staticmethod
    def format_size(size: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"

    def log_summary(self, total: int, success: int, skip: int, error: int):
        """记录备份统计信息"""
        msg = f"""
备份完成统计:
- 总文件数: {total}
- 成功: {success}
- 跳过: {skip}
- 错误: {error}
"""
        logging.info(msg) 