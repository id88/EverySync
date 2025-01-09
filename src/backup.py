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
from ignore_rules import IgnoreRules

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
        self.ignore_rules = IgnoreRules()

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
            # self.logger.log_info("正在获取文件列表...")
            files = self._get_files_to_backup(source_path)
            total_files = len(files)
            self.logger.log_info(f"找到 {total_files} 个文件需要处理")

            processed_files = 0
            success_count = 0
            skip_count = 0
            error_count = 0

            # 处理每个文件
            for file_info in files:
                source_file = file_info['path']
                
                try:
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

    def _get_files_to_backup(self, source_path: str) -> List[dict]:
        """获取需要备份的文件列表"""
        try:
            # 获取配置信息
            incremental_days = self.config.get_incremental_days()
            file_size_limit = self.config.get_file_size_limit()
            
            self.logger.log_debug(f"""
开始文件扫描:
- 源路径: {source_path}
- 增量备份天数: {incremental_days}
- 文件大小限制: {file_size_limit} MB
""")
            
            # 检查是否可以使用 Everything
            # self.logger.log_debug("检查 Everything 可用性...")
            everything_available = self.everything.is_available()
            self.logger.log_debug(f"Everything 可用性检查结果: {'可用' if everything_available else '不可用'}")
            
            # 如果源路径是驱动器且 Everything 可用，使用 Everything 搜索
            if (len(source_path.rstrip('\\')) == 2 and source_path[1] == ':' and everything_available):
                self.logger.log_debug("使用 Everything API 搜索文件")
                
                try:
                    # 构建基本查询
                    source_path = os.path.normpath(source_path)
                    query_parts = [f'{source_path}']
                    
                    # 添加增量备份条件
                    if incremental_days > 0:
                        query_parts.append(f'dm:prev{incremental_days}days')
                    
                    # 添加文件大小限制
                    if file_size_limit > 0:
                        size_bytes = file_size_limit * 1024 * 1024
                        query_parts.append(f'size:<{size_bytes}')
                    
                    # 添加忽略规则
                    query_parts.extend(self.ignore_rules.get_everything_query_parts())
                    
                    # 组合查询语句
                    query = ' '.join(query_parts)
                    self.logger.log_debug(f"Everything 搜索查询: {query}")

                    # 执行搜索
                    try:
                        files = self.everything.search(query)
                        self.logger.log_debug(f"Everything 搜索返回 {len(files)} 个结果")
                        return files
                        
                    except Exception as e:
                        self.logger.log_error(f"Everything 搜索执行失败: {str(e)}", exc_info=True)
                        self.logger.log_debug("切换到备用扫描方法")
                        return self._fallback_file_scan(source_path, incremental_days, file_size_limit)
                        
                except Exception as e:
                    self.logger.log_error(f"构建 Everything 查询失败: {str(e)}", exc_info=True)
                    return self._fallback_file_scan(source_path, incremental_days, file_size_limit)
            else:
                reason = '不是驱动器根目录' if len(source_path.rstrip('\\')) != 2 else 'Everything 不可用'
                self.logger.log_debug(f"使用文件系统遍历 (原因: {reason})")
                return self._fallback_file_scan(source_path, incremental_days, file_size_limit)
                
        except Exception as e:
            self.logger.log_error(f"获取文件列表失败: {str(e)}", exc_info=True)
            return []

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

    def _fallback_file_scan(self, source_path: str, incremental_days: int, file_size_limit: int) -> List[dict]:
        """当 Everything 搜索失败时的回退文件扫描方法"""
        self.logger.log_info("使用文件系统遍历作为回退方案")
        files = []
        
        for root, dirs, filenames in os.walk(source_path):
            # 检查路径长度
            if len(root) > 240:
                self.logger.log_warning(f"跳过路径过长的目录: {root}")
                dirs.clear()
                continue
            
            # 检查目录是否应该被排除
            should_skip_dir = False
            for pattern in self.ignore_rules.rules:
                if '*' not in pattern:  # 对于不包含通配符的规则
                    if pattern.lower() in root.lower():
                        should_skip_dir = True
                        # print(f"跳过排除目录: {root} (匹配规则: {pattern})")
                        break
            
            if should_skip_dir:
                dirs.clear()  # 清空目录列表，跳过此目录的子目录
                continue
            
            # 处理文件
            for filename in filenames:
                file_path = os.path.join(root, filename)
                # print(f"正在检查 {file_path}")
                
                try:
                    # 基本检查
                    if len(file_path) > 240:
                        continue
                    
                    # 检查文件是否应该被排除
                    should_skip_file = False
                    for pattern in self.ignore_rules.rules:
                        if '*' in pattern:  # 处理通配符规则
                            import fnmatch
                            if fnmatch.fnmatch(filename.lower(), pattern.lower()):
                                should_skip_file = True
                                # print(f"跳过排除文件: {file_path} (匹配规则: {pattern})")
                                break
                        else:  # 处理普通规则
                            if pattern.lower() in file_path.lower():
                                should_skip_file = True
                                # print(f"跳过排除文件: {file_path} (匹配规则: {pattern})")
                                break
                    
                    if should_skip_file:
                        continue
                    
                    # 获取文件信息
                    file_size = os.path.getsize(file_path)
                    modified_time = int(os.path.getmtime(file_path))
                    
                    # 应用过滤条件
                    if file_size > file_size_limit * 1024 * 1024:
                        continue
                        
                    if incremental_days > 0:
                        cutoff_time = time.time() - (incremental_days * 24 * 3600)
                        if modified_time < cutoff_time:
                            continue
                            
                    files.append({
                        'path': file_path,
                        'size': file_size,
                        'modified_time': modified_time
                    })
                    # print(f"获取到文件信息 {file_path}，{file_size}，{modified_time} ")
                    
                except (OSError, IOError) as e:
                    self.logger.log_error(f"无法获取文件信息 {file_path}: {str(e)}")
                    continue
                    
        return files 