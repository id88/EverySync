import os
import time
import logging
from typing import List, Dict, Optional, Callable
from datetime import datetime, timedelta

from config import Config
from logger import Logger
from everything import Everything
from file_utils import FileUtils
from drive_monitor import DriveMonitor

class Backup:
    def __init__(self, config: Config, logger: Logger):
        """
        初始化备份管理器
        
        Args:
            config: 配置管理器实例
            logger: 日志管理器实例
        """
        self.config = config
        self.logger = logger
        self.everything = Everything()
        self.drive_monitor = DriveMonitor()
        self.file_utils = FileUtils()

    def start_backup(self, callback: Callable = None) -> bool:
        """
        开始备份流程
        
        Args:
            callback: 进度回调函数

        Returns:
            bool: 备份是否成功
        """
        try:
            # 获取备份源和目标路径
            backup_sources = self.config.get_backup_sources()
            
            # 检查每个备份源
            for source_path, dest_path in backup_sources.items():
                # 检查源路径是否可用
                if not self.drive_monitor.is_drive_available(source_path):
                    self.logger.log_error(f"源路径不可用: {source_path}")
                    continue

                # 确保目标目录存在
                try:
                    os.makedirs(dest_path, exist_ok=True)
                except Exception as e:
                    self.logger.log_error(f"创建目标目录失败 {dest_path}: {str(e)}")
                    continue

                # 检查目标目录是否可写
                if not os.access(dest_path, os.W_OK):
                    self.logger.log_error(f"目标目录无写入权限: {dest_path}")
                    continue

                # 执行备份
                self._backup_drive(source_path, dest_path, callback)

            return True
        except Exception as e:
            self.logger.log_error(f"备份过程出错: {str(e)}", exc_info=True)
            return False

    def _backup_drive(self, source_path: str, dest_path: str, callback: Callable = None) -> None:
        """执行单个目录或驱动器的备份"""
        try:
            # 获取完整路径
            source_path = os.path.abspath(source_path)
            dest_path = os.path.abspath(dest_path)
            
            self.logger.log_info(f"开始备份 {source_path} 到 {dest_path}")

            # 获取需要备份的文件列表
            self.logger.log_info("正在获取文件列表...")
            files = self._get_files_to_backup(source_path)
            total_files = len(files)
            self.logger.log_info(f"找到 {total_files} 个文件需要处理")

            processed_files = 0
            success_count = 0
            skip_count = 0
            error_count = 0

            try:
                # 获取排除规则
                exclude_patterns = self.config.get_exclude_patterns()
            except Exception as e:
                self.logger.log_error(f"获取排除规则失败: {str(e)}")
                exclude_patterns = {'directories': [], 'files': []}

            # 处理每个文件
            for file_info in files:
                source_file = file_info['path']
                
                try:
                    # 检查是否应该排除
                    if self._should_exclude(source_file, exclude_patterns):
                        self.logger.log_debug(f"跳过排除文件: {source_file}")
                        skip_count += 1
                        continue

                    # 跳过系统文件和特殊目录
                    if self._is_system_path(source_file):
                        self.logger.log_debug(f"跳过系统文件: {source_file}")
                        skip_count += 1
                        continue

                    # 获取相对路径
                    rel_path = os.path.relpath(source_file, source_path)
                    dest_file = os.path.join(dest_path, rel_path)

                    # 确保路径是绝对路径
                    source_file = os.path.abspath(source_file)
                    dest_file = os.path.abspath(dest_file)

                    # 如果是目录，创建目录但不复制
                    if os.path.isdir(source_file):
                        os.makedirs(dest_file, exist_ok=True)
                        self.logger.log_debug(f"创建目录: {dest_file}")
                        continue

                    # 检查文件大小限制
                    try:
                        file_size_mb = os.path.getsize(source_file) / (1024 * 1024)
                        if file_size_mb > self.config.get_file_size_limit():
                            self.logger.log_error(f"文件超过大小限制 ({file_size_mb:.2f}MB): {source_file}")
                            skip_count += 1
                            continue
                    except OSError:
                        self.logger.log_error(f"无法获取文件大小: {source_file}")
                        error_count += 1
                        continue

                    # 检查是否需要更新
                    if self._need_update(source_file, dest_file):
                        # 确保目标目录存在
                        os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                        
                        # 执行备份
                        self.logger.log_backup(source_file, dest_file, "开始")
                        if self.file_utils.safe_copy(source_file, dest_file):
                            self.logger.log_backup(source_file, dest_file, "完成")
                            success_count += 1
                        else:
                            self.logger.log_error(f"文件备份失败: {source_file}")
                            error_count += 1
                    else:
                        self.logger.log_debug(f"文件无需更新: {source_file}")
                        skip_count += 1

                except PermissionError:
                    self.logger.log_error(f"无权限访问: {source_file}")
                    error_count += 1
                    continue
                except OSError as e:
                    self.logger.log_error(f"处理文件时出错 {source_file}: {str(e)}")
                    error_count += 1
                    continue
                except Exception as e:
                    self.logger.log_error(f"处理文件时出现未知错误 {source_file}: {str(e)}")
                    error_count += 1
                    continue
                finally:
                    processed_files += 1
                    if callback:
                        callback(processed_files, total_files)

            # 记录备份统计信息
            self.logger.log_summary(
                total=total_files,
                success=success_count,
                skip=skip_count,
                error=error_count
            )

        except Exception as e:
            self.logger.log_error(f"备份失败 {source_path}: {str(e)}", exc_info=True)

    def _is_system_path(self, path: str) -> bool:
        """检查是否是系统路径或特殊目录"""
        system_paths = [
            '$RECYCLE.BIN',
            'System Volume Information',
            'pagefile.sys',
            'hiberfil.sys',
            'swapfile.sys',
            '.git',
            '.github',
            'node_modules',
            '__pycache__',
            '.pytest_cache',
            '.vscode',
            '.idea'
        ]
        
        path_lower = path.lower()
        return any(sp.lower() in path_lower for sp in system_paths)

    def _get_files_to_backup(self, source_path: str) -> List[dict]:
        """获取需要备份的文件列表"""
        try:
            files = []
            
            # 如果源路径是驱动器，使用 Everything 搜索
            if len(source_path) == 2 and source_path[1] == ':':
                query = f'path:"{source_path}\\"'
                files = self.everything.search(query)
            else:
                # 否则使用普通文件系统遍历
                for root, dirs, filenames in os.walk(source_path):
                    # 检查路径长度
                    if len(root) > 240:  # 留出一些余量给文件名
                        self.logger.log_warning(f"跳过路径过长的目录: {root}")
                        dirs.clear()  # 停止遍历此目录的子目录
                        continue

                    # 添加目录
                    for dir_name in dirs[:]:  # 使用切片创建副本以便修改
                        dir_path = os.path.join(root, dir_name)
                        if len(dir_path) > 240:
                            self.logger.log_warning(f"跳过路径过长的目录: {dir_path}")
                            dirs.remove(dir_name)  # 从遍历列表中移除
                            continue
                        files.append({
                            'path': dir_path,
                            'size': 0,
                            'modified_time': int(os.path.getmtime(dir_path))
                        })
                    
                    # 添加文件
                    for filename in filenames:
                        file_path = os.path.join(root, filename)
                        if len(file_path) > 240:
                            self.logger.log_warning(f"跳过路径过长的文件: {file_path}")
                            continue
                        try:
                            files.append({
                                'path': file_path,
                                'size': os.path.getsize(file_path),
                                'modified_time': int(os.path.getmtime(file_path))
                            })
                        except (OSError, IOError) as e:
                            self.logger.log_error(f"无法获取文件信息 {file_path}: {str(e)}")
                            continue
            
            # 过滤掉系统路径和路径过长的文件
            files = [
                f for f in files 
                if not self._is_system_path(f['path']) and len(f['path']) <= 240
            ]
            
            # 如果配置了增量备份，只返回最近修改的文件
            if self.config.get_incremental_days() > 0:
                cutoff_time = datetime.now() - timedelta(days=self.config.get_incremental_days())
                files = [
                    f for f in files
                    if datetime.fromtimestamp(f['modified_time']) > cutoff_time
                ]

            return files
        except Exception as e:
            self.logger.log_error(f"获取文件列表失败: {str(e)}")
            return []

    def _should_exclude(self, file_path: str, exclude_patterns: dict) -> bool:
        """检查文件是否应该被排除"""
        try:
            # 检查目录排除规则
            for dir_pattern in exclude_patterns['directories']:
                if dir_pattern.lower() in file_path.lower():
                    return True

            # 检查文件排除规则
            file_name = os.path.basename(file_path)
            for file_pattern in exclude_patterns['files']:
                if self._match_pattern(file_name, file_pattern):
                    return True

            return False
        except Exception as e:
            self.logger.log_error(f"检查排除规则失败: {str(e)}")
            return False

    def _match_pattern(self, file_name: str, pattern: str) -> bool:
        """检查文件名是否匹配模式"""
        try:
            # 将通配符模式转换为正则表达式
            import fnmatch
            return fnmatch.fnmatch(file_name.lower(), pattern.lower())
        except Exception as e:
            self.logger.log_error(f"匹配模式失败: {str(e)}")
            return False

    def _need_update(self, source_path: str, dest_path: str) -> bool:
        """检查文件是否需要更新"""
        try:
            # 如果目标文件不存在，需要更新
            if not os.path.exists(dest_path):
                return True

            # 获取源文件和目标文件信息
            source_info = self.file_utils.get_file_info(source_path)
            dest_info = self.file_utils.get_file_info(dest_path)

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
            self.logger.log_error(f"检查文件更新失败: {str(e)}")
            return True

    def verify_backup(self, callback: Callable = None) -> bool:
        """
        验证备份的完整性
        
        Args:
            callback: 进度回调函数

        Returns:
            bool: 验证是否通过
        """
        try:
            backup_sources = self.config.get_backup_sources()
            sample_size = self.config.get_verification_sample_size()
            
            for source_drive, dest_path in backup_sources.items():
                # 获取所有文件
                files = self.everything.search_files_in_directory(source_drive)
                
                # 随机选择样本
                import random
                sample_files = random.sample(files, min(sample_size, len(files)))
                
                # 验证每个样本文件
                for i, file_info in enumerate(sample_files):
                    source_path = file_info['path']
                    rel_path = os.path.relpath(source_path, source_drive)
                    dest_file_path = os.path.join(dest_path, rel_path)
                    
                    # 比较文件
                    is_same, reason = self.file_utils.compare_files(source_path, dest_file_path)
                    if not is_same:
                        self.logger.log_error(f"文件验证失败: {source_path} - {reason}")
                        return False
                    
                    if callback:
                        callback(i + 1, len(sample_files))

            return True
        except Exception as e:
            self.logger.log_error(f"验证备份失败: {str(e)}")
            return False 