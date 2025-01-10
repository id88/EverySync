import os
import sys
import time
import logging
from typing import Optional
from datetime import datetime

from config import Config
from backup import Backup
from drive_monitor import DriveMonitor

def init_logging():
    """初始化日志配置"""
    # 创建logs目录
    os.makedirs('logs', exist_ok=True)
    
    # 生成日志文件名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = f'logs/{timestamp}.log'
    
    # 配置日志格式
    log_format = '%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    # 配置日志
    logging.basicConfig(
        level=logging.DEBUG,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()  # 同时输出到控制台
        ]
    )
    logging.info(f"日志文件: {log_file}")

class BackupManager:
    def __init__(self):
        """初始化备份管理器"""
        self.config = Config()
        self.backup = Backup(self.config)
        self.drive_monitor = DriveMonitor()
        logging.info("备份管理器初始化完成")

    def backup_progress_callback(self, current: int, total: int):
        """备份进度回调"""
        progress = (current / total) * 100 if total > 0 else 0
        print(f"\r备份进度: {progress:.2f}% ({current}/{total})", end='')
        if current == total:
            print()
            logging.info(f"备份完成: {total}/{total}")

    def wait_for_drives(self, timeout: Optional[int] = None) -> bool:
        """等待所有需要的驱动器就绪"""
        backup_sources = self.config.get_backup_sources()
        required_drives = set()
        for source, dest in backup_sources.items():
            if len(source) >= 2 and source[1] == ':':
                required_drives.add(source[:2])
            if len(dest) >= 2 and dest[1] == ':':
                required_drives.add(dest[:2])

        if not required_drives:
            logging.info("没有需要等待的驱动器")
            return True

        logging.info(f"等待驱动器: {', '.join(required_drives)}")
        start_time = time.time()
        
        while True:
            unavailable_drives = [
                drive for drive in required_drives
                if not self.drive_monitor.is_drive_available(drive)
            ]
            
            if not unavailable_drives:
                logging.info("所有驱动器已就绪")
                return True
            
            if timeout is not None and (time.time() - start_time) > timeout:
                logging.error(f"等待驱动器超时: {', '.join(unavailable_drives)}")
                return False
            
            time.sleep(1)

    def run_backup(self) -> bool:
        """执行备份流程"""
        try:
            logging.info("开始备份流程")
            
            if not self.wait_for_drives(timeout=30):
                logging.error("部分驱动器未就绪，备份终止")
                return False
            
            success = self.backup.start_backup(callback=self.backup_progress_callback)
            if not success:
                logging.error("备份执行失败")
                return False
            
            logging.info("备份流程完成")
            return True
            
        except KeyboardInterrupt:
            logging.warning("备份被用户中断")
            return False
        except Exception as e:
            logging.error(f"备份过程出错: {str(e)}", exc_info=True)
            return False

def main():
    """主程序入口"""
    try:
        # 初始化日志配置
        init_logging()
        
        start_time = datetime.now()
        logging.info("=== EverySync 文件备份工具启动 ===")
        logging.info(f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        manager = BackupManager()
        success = manager.run_backup()
        
        end_time = datetime.now()
        duration = end_time - start_time
        logging.info(f"结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logging.info(f"运行时长: {duration}")
        logging.info(f"备份状态: {'成功' if success else '失败'}")
        
        return 0 if success else 1
        
    except Exception as e:
        logging.error(f"程序运行出错: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main()) 