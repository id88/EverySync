import os
import sys
import time
import logging
from typing import Optional
from datetime import datetime

from config import Config
from logger import Logger
from backup import Backup
from drive_monitor import DriveMonitor

class BackupManager:
    def __init__(self):
        """初始化备份管理器"""
        self.config = Config()
        self.logger = Logger(self.config.config)
        self.backup = Backup(self.config, self.logger)
        self.drive_monitor = DriveMonitor()
        
    def backup_progress_callback(self, current: int, total: int):
        """备份进度回调"""
        progress = (current / total) * 100 if total > 0 else 0
        print(f"\r备份进度: {progress:.2f}% ({current}/{total})", end='')
        if current == total:
            print()  # 换行

    def verify_progress_callback(self, current: int, total: int):
        """验证进度回调"""
        progress = (current / total) * 100 if total > 0 else 0
        print(f"\r验证进度: {progress:.2f}% ({current}/{total})", end='')
        if current == total:
            print()  # 换行

    def wait_for_drives(self, timeout: Optional[int] = None) -> bool:
        """等待所有需要的驱动器就绪"""
        backup_sources = self.config.get_backup_sources()
        
        # 获取所有需要的驱动器
        required_drives = set()
        for source, dest in backup_sources.items():
            if len(source) >= 2 and source[1] == ':':
                required_drives.add(source[:2])
            if len(dest) >= 2 and dest[1] == ':':
                required_drives.add(dest[:2])

        if not required_drives:
            return True

        print("等待驱动器就绪...")
        start_time = time.time()
        
        while True:
            # 检查所有驱动器
            unavailable_drives = [
                drive for drive in required_drives
                if not self.drive_monitor.is_drive_available(drive)
            ]
            
            if not unavailable_drives:
                print("所有驱动器已就绪")
                return True
            
            # 显示未就绪的驱动器
            print(f"\r等待驱动器: {', '.join(unavailable_drives)}", end='')
            
            # 检查超时
            if timeout is not None and (time.time() - start_time) > timeout:
                print("\n等待驱动器超时")
                return False
            
            time.sleep(1)

    def run_backup(self) -> bool:
        """执行备份流程"""
        try:
            print("\n开始备份流程...")
            
            # 等待驱动器就绪
            if not self.wait_for_drives(timeout=30):
                print("部分驱动器未就绪，备份终止")
                return False
            
            # 执行备份
            success = self.backup.start_backup(callback=self.backup_progress_callback)
            if not success:
                print("备份失败")
                return False
            
            # 验证备份
            print("\n开始验证备份...")
            if self.backup.verify_backup(callback=self.verify_progress_callback):
                print("备份验证通过")
            else:
                print("备份验证失败")
                return False
            
            return True
            
        except KeyboardInterrupt:
            print("\n备份被用户中断")
            return False
        except Exception as e:
            print(f"\n备份过程出错: {str(e)}")
            logging.error("备份失败", exc_info=True)
            return False

def main():
    """主程序入口"""
    try:
        print("=== EverySync 文件备份工具 ===")
        print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 创建并运行备份管理器
        manager = BackupManager()
        success = manager.run_backup()
        
        print(f"\n结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"备份状态: {'成功' if success else '失败'}")
        
        # 返回状态码
        return 0 if success else 1
        
    except Exception as e:
        print(f"程序运行出错: {str(e)}")
        logging.error("程序异常退出", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main()) 