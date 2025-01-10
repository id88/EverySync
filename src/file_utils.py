import os
import hashlib
import shutil
from typing import Optional, Tuple
from datetime import datetime
import logging

class FileUtils:
    BUFFER_SIZE = 8192  # 8KB buffer size for file operations

    @staticmethod
    def calculate_md5(file_path: str) -> Optional[str]:
        """
        计算文件的MD5值
        
        Args:
            file_path: 文件路径

        Returns:
            str: MD5哈希值，如果出错则返回None
        """
        try:
            md5_hash = hashlib.md5()
            with open(file_path, 'rb') as f:
                while True:
                    data = f.read(FileUtils.BUFFER_SIZE)
                    if not data:
                        break
                    md5_hash.update(data)
            return md5_hash.hexdigest()
        except Exception as e:
            logging.error(f"计算MD5失败 {file_path}: {str(e)}")
            return None

    @staticmethod
    def compare_files(source_path: str, dest_path: str) -> Tuple[bool, str]:
        """
        比较两个文件是否相同
        
        Args:
            source_path: 源文件路径
            dest_path: 目标文件路径

        Returns:
            Tuple[bool, str]: (是否相同, 不同的原因)
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(source_path):
                return False, "源文件不存在"
            if not os.path.exists(dest_path):
                return False, "目标文件不存在"

            # 比较文件大小
            source_size = os.path.getsize(source_path)
            dest_size = os.path.getsize(dest_path)
            if source_size != dest_size:
                return False, "文件大小不一致"

            # 比较MD5值
            source_md5 = FileUtils.calculate_md5(source_path)
            dest_md5 = FileUtils.calculate_md5(dest_path)
            if source_md5 is None or dest_md5 is None:
                return False, "MD5计算失败"
            if source_md5 != dest_md5:
                return False, "MD5值不一致"

            return True, "文件完全相同"
        except Exception as e:
            logging.error(f"比较文件失败: {str(e)}")
            return False, f"比较过程出错: {str(e)}"

    @staticmethod
    def safe_copy(source_path: str, dest_path: str, overwrite: bool = True) -> bool:
        """安全地复制文件"""
        try:
            # 检查路径长度
            if len(source_path) > 240 or len(dest_path) > 240:
                logging.error(f"路径过长: {source_path} -> {dest_path}")
                return False

            # 如果是目录，直接创建
            if os.path.isdir(source_path):
                os.makedirs(dest_path, exist_ok=True)
                return True

            # 确保目标目录存在
            dest_dir = os.path.dirname(dest_path)
            os.makedirs(dest_dir, exist_ok=True)

            # 如果目标文件已存在且不允许覆盖
            if os.path.exists(dest_path) and not overwrite:
                logging.warning(f"目标文件已存在且不允许覆盖: {dest_path}")
                return False

            try:
                # 复制文件
                shutil.copy2(source_path, dest_path)
                logging.info(f"文件复制成功: {source_path} -> {dest_path}")
                
                # 验证文件大小
                if os.path.getsize(source_path) != os.path.getsize(dest_path):
                    logging.error(f"文件大小验证失败: {source_path}")
                    if os.path.exists(dest_path):
                        os.remove(dest_path)
                    return False
                    
                # 验证文件内容
                source_md5 = FileUtils.calculate_md5(source_path)
                dest_md5 = FileUtils.calculate_md5(dest_path)
                
                if source_md5 is None or dest_md5 is None:
                    logging.error(f"MD5计算失败: {source_path}")
                    if os.path.exists(dest_path):
                        os.remove(dest_path)
                    return False
                    
                if source_md5 != dest_md5:
                    logging.error(f"MD5验证失败: {source_path}")
                    if os.path.exists(dest_path):
                        os.remove(dest_path)
                    return False
                    
                return True
                
            except PermissionError:
                logging.error(f"无权限访问文件: {source_path}")
                return False
            except OSError as e:
                logging.error(f"复制文件失败 {source_path}: {str(e)}")
                return False

        except Exception as e:
            logging.error(f"复制文件失败 {source_path} -> {dest_path}: {str(e)}")
            return False

    @staticmethod
    def get_file_info(file_path: str) -> Optional[dict]:
        """
        获取文件信息
        
        Args:
            file_path: 文件路径

        Returns:
            Optional[dict]: 包含文件信息的字典，如果出错则返回None
        """
        try:
            stat = os.stat(file_path)
            return {
                'size': stat.st_size,
                'modified_time': int(stat.st_mtime),
                'created_time': int(stat.st_ctime),
                'accessed_time': int(stat.st_atime),
                'md5': FileUtils.calculate_md5(file_path)
            }
        except Exception as e:
            logging.error(f"获取文件信息失败 {file_path}: {str(e)}")
            return None

    @staticmethod
    def is_file_modified_recently(file_path: str, days: int) -> bool:
        """
        检查文件是否在最近指定天数内被修改
        
        Args:
            file_path: 文件路径
            days: 天数

        Returns:
            bool: 是否最近被修改
        """
        try:
            modified_time = os.path.getmtime(file_path)
            current_time = datetime.now().timestamp()
            return (current_time - modified_time) <= (days * 24 * 3600)
        except Exception as e:
            logging.error(f"检查文件修改时间失败 {file_path}: {str(e)}")
            return False

    @staticmethod
    def format_size(size_in_bytes: int) -> str:
        """
        格式化文件大小显示
        
        Args:
            size_in_bytes: 文件大小（字节）

        Returns:
            str: 格式化后的大小字符串
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_in_bytes < 1024.0:
                return f"{size_in_bytes:.2f} {unit}"
            size_in_bytes /= 1024.0
        return f"{size_in_bytes:.2f} PB" 

    def _need_update(self, source_path: str, dest_path: str) -> bool:
        """检查文件是否需要更新"""
        try:
            # 如果目标文件不存在，需要更新
            if not os.path.exists(dest_path):
                return True

            # 获取源文件和目标文件信息
            source_info = self.get_file_info(source_path)
            dest_info = self.get_file_info(dest_path)

            if not source_info or not dest_info:
                return True

            # 比较文件大小和修改时间
            if source_info['size'] != dest_info['size']:
                return True

            if source_info['modified_time'] > dest_info['modified_time']:
                return True

            # 可选：比较MD5
            if source_info['md5'] != dest_info['md5']:
                return True

            return False
        except Exception as e:
            logging.error(f"检查文件更新失败: {str(e)}")
            return True 