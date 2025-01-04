import os
import time
import string
import logging
import win32api
import win32file
from typing import Optional, List, Dict, Callable

class DriveMonitor:
    def __init__(self):
        """初始化驱动器监控器"""
        self.drives_cache: Dict[str, dict] = {}  # 缓存驱动器信息
        self.update_drives_cache()

    def update_drives_cache(self) -> None:
        """更新驱动器缓存信息"""
        try:
            drives = self._get_all_drives()
            self.drives_cache = {
                drive: self._get_drive_info(drive)
                for drive in drives
            }
        except Exception as e:
            logging.error(f"更新驱动器缓存失败: {str(e)}")

    def _get_all_drives(self) -> List[str]:
        """获取所有可用的驱动器列表"""
        try:
            drives = []
            bitmask = win32api.GetLogicalDrives()
            for letter in string.ascii_uppercase:
                if bitmask & 1:
                    drives.append(f"{letter}:")
                bitmask >>= 1
            return drives
        except Exception as e:
            logging.error(f"获取驱动器列表失败: {str(e)}")
            return []

    def _get_drive_info(self, drive: str) -> dict:
        """获取驱动器详细信息"""
        try:
            drive_type = win32file.GetDriveType(drive + "\\")
            volume_info = None
            free_space = None
            total_space = None

            try:
                volume_name, volume_serial, max_component_length, flags, fs_name = \
                    win32api.GetVolumeInformation(drive + "\\")
                volume_info = {
                    'name': volume_name,
                    'serial': volume_serial,
                    'file_system': fs_name
                }
            except:
                volume_info = None

            try:
                free_bytes, total_bytes, total_free_bytes = \
                    win32api.GetDiskFreeSpaceEx(drive + "\\")
                free_space = free_bytes
                total_space = total_bytes
            except:
                free_space = None
                total_space = None

            return {
                'type': drive_type,
                'volume_info': volume_info,
                'free_space': free_space,
                'total_space': total_space,
                'is_ready': self._is_drive_ready(drive)
            }
        except Exception as e:
            logging.error(f"获取驱动器信息失败 {drive}: {str(e)}")
            return {
                'type': None,
                'volume_info': None,
                'free_space': None,
                'total_space': None,
                'is_ready': False
            }

    def _is_drive_ready(self, drive: str) -> bool:
        """检查驱动器是否就绪"""
        try:
            # 尝试获取驱动器根目录
            os.listdir(drive + "\\")
            return True
        except:
            return False

    def is_drive_available(self, path: str) -> bool:
        """
        检查指定路径是否可用
        
        Args:
            path: 路径（可以是驱动器如 "G:" 或普通目录）

        Returns:
            bool: 路径是否可用
        """
        try:
            # 如果是驱动器路径
            if len(path) == 2 and path[1] == ':':
                self.update_drives_cache()
                path = path.upper().rstrip("\\")
                return (
                    path in self.drives_cache and
                    self.drives_cache[path]['is_ready']
                )
            else:
                # 如果是普通目录路径，直接检查是否存在且可访问
                return os.path.exists(path) and os.access(path, os.R_OK)
        except Exception as e:
            logging.error(f"检查路径可用性失败 {path}: {str(e)}")
            return False

    def wait_for_drive(self, drive: str, timeout: int = None, callback: Callable = None) -> bool:
        """
        等待驱动器就绪
        
        Args:
            drive: 驱动器路径（如 "G:"）
            timeout: 超时时间（秒），None表示永久等待
            callback: 状态变化回调函数

        Returns:
            bool: 驱动器是否就绪
        """
        drive = drive.upper().rstrip("\\")
        start_time = time.time()
        
        while True:
            is_available = self.is_drive_available(drive)
            
            if callback:
                callback(drive, is_available)
            
            if is_available:
                return True
                
            if timeout is not None and (time.time() - start_time) > timeout:
                return False
                
            time.sleep(1)  # 等待1秒后重试

    def get_drive_info(self, drive: str) -> Optional[dict]:
        """
        获取驱动器信息
        
        Args:
            drive: 驱动器路径（如 "G:"）

        Returns:
            Optional[dict]: 驱动器信息字典，如果驱动器不可用则返回None
        """
        try:
            self.update_drives_cache()
            drive = drive.upper().rstrip("\\")
            return self.drives_cache.get(drive)
        except Exception as e:
            logging.error(f"获取驱动器信息失败 {drive}: {str(e)}")
            return None

    def format_size(self, size: int) -> str:
        """格式化显示容量大小"""
        if size is None:
            return "未知"
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB" 