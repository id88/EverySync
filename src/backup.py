import os
import time
import logging
from typing import List, Dict, Optional, Callable
from datetime import datetime, timedelta

from config import Config
from everything import Everything
from file_utils import FileUtils
from drive_monitor import DriveMonitor
from ignore_rules import IgnoreRules
from parallel_backup import ParallelBackup

class Backup:
    def __init__(self, config: Config):
        """
        初始化备份管理器
        
        Args:
            config: 配置管理器实例
        """
        self.config = config
        self.everything = Everything()
        self.drive_monitor = DriveMonitor()
        self.file_utils = FileUtils()
        self.ignore_rules = IgnoreRules()
        
        # 检查 Everything 可用性并保存状态
        self.everything_available = self._check_everything_available()
        
        self.parallel_backup = ParallelBackup(
            config.get_parallel_config(),
            self.file_utils
        )

    def _check_everything_available(self) -> bool:
        """检查 Everything 是否可用"""
        try:
            is_available = self.everything.is_available()
            logging.debug(f"Everything 可用性检查结果: {'可用' if is_available else '不可用'}")
            return is_available
        except Exception as e:
            logging.error(f"检查 Everything 可用性时出错: {str(e)}")
            return False

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
                    logging.error(f"源路径不可用: {source_path}")
                    continue

                # 确保目标目录存在
                try:
                    os.makedirs(dest_path, exist_ok=True)
                except Exception as e:
                    logging.error(f"创建目标目录失败 {dest_path}: {str(e)}")
                    continue

                # 检查目标目录是否可写
                if not os.access(dest_path, os.W_OK):
                    logging.error(f"目标目录无写入权限: {dest_path}")
                    continue

                # 执行备份
                self._backup_drive(source_path, dest_path, callback)

            return True
        except Exception as e:
            logging.error(f"备份过程出错: {str(e)}", exc_info=True)
            return False

    def _normalize_drive_path(self, path: str) -> str:
        """
        标准化路径格式，对驱动器路径特殊处理
        
        Args:
            path: 原始路径

        Returns:
            str: 标准化后的路径
        """
        if len(path) >= 2 and path[1] == ':':
            # 如果是驱动器路径（如 "D:"），确保以反斜杠结尾
            return os.path.normpath(path.rstrip('\\')) + '\\'
        else:
            # 非驱动器路径使用绝对路径
            return os.path.abspath(path)

    def _get_relative_path(self, file_path: str, source_path: str) -> str:
        """
        获取相对路径
        
        Args:
            file_path: 文件完整路径
            source_path: 源目录路径

        Returns:
            str: 相对路径
        """
        if len(source_path) == 3 and source_path[1] == ':':  # 如 "D:\"
            # 从第四个字符开始截取，跳过驱动器部分
            return file_path[3:]
        else:
            return os.path.relpath(file_path, source_path)

    def _backup_drive(self, source_path: str, dest_path: str, callback: Callable = None) -> None:
        """执行单个目录或驱动器的备份"""
        try:
            # 标准化路径
            source_path = self._normalize_drive_path(source_path)
            dest_path = os.path.abspath(dest_path)
            
            logging.info(f"开始获取需要备份的文件列表: {source_path}")

            # 获取需要备份的文件列表
            files = self._get_files_to_backup(source_path)
            
            if not files:
                logging.info(f"没有文件需要备份: {source_path}")
                return
                
            # 添加目标路径信息
            for file in files:
                rel_path = self._get_relative_path(file['path'], source_path)
                file['dest_path'] = os.path.join(dest_path, rel_path)

            # 使用并行处理进行备份
            parallel_config = self.config.get_parallel_config()
            if parallel_config['enabled']:
                logging.debug("并行备份的状态: 启用")
                success, skip, error = self.parallel_backup.backup_files(files, callback)
            else:
                logging.debug("并行备份的状态: 禁用")
                # 原有的串行处理逻辑
                success, skip, error = self._backup_files_serial(files, callback)

            # 记录备份统计信息
            logging.info(f"备份统计 - 总数: {len(files)}, 成功: {success}, 跳过: {skip}, 错误: {error}")

        except Exception as e:
            logging.error(f"备份失败 {source_path}: {str(e)}", exc_info=True)

    def _get_files_to_backup(self, source_path: str) -> List[dict]:
        """获取需要备份的文件列表"""
        try:
            # 获取配置信息
            incremental_days = self.config.get_incremental_days()
            file_size_limit = self.config.get_file_size_limit()
            
            # 使用已保存的 Everything 可用性状态
            if self.everything_available:
                logging.debug("准备使用 Everything API 搜索文件")
                
                try:
                    # 使用标准化的路径
                    source_path = self._normalize_drive_path(source_path)
                    
                    # 构建基本查询
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
                    logging.debug(f"Everything 查询语句: {query}")

                    # 执行搜索
                    try:
                        files = self.everything.search(query)
                        return files
                        
                    except Exception as e:
                        logging.error(f"Everything 搜索执行失败: {str(e)}", exc_info=True)
                        return self._fallback_file_scan(source_path, incremental_days, file_size_limit)
                        
                except Exception as e:
                    logging.error(f"构建 Everything 查询失败: {str(e)}", exc_info=True)
                    return self._fallback_file_scan(source_path, incremental_days, file_size_limit)
            else:
                logging.debug("Everything 不可用，切换到文件系统遍历")
                return self._fallback_file_scan(source_path, incremental_days, file_size_limit)
                
        except Exception as e:
            logging.error(f"获取文件列表失败: {str(e)}", exc_info=True)
            return []

    def _backup_files_serial(self, files: List[dict], callback: Callable = None) -> tuple:
        """串行处理文件备份"""
        success_count = 0
        skip_count = 0
        error_count = 0
        processed_files = 0
        total_files = len(files)

        for file_info in files:
            try:
                source_file = file_info['path']
                dest_file = file_info['dest_path']

                # 如果是目录，创建目录但不复制
                if os.path.isdir(source_file):
                    os.makedirs(dest_file, exist_ok=True)
                    logging.debug(f"创建目录: {dest_file}")
                    continue

                # 检查文件大小限制
                try:
                    file_size_mb = os.path.getsize(source_file) / (1024 * 1024)
                    if file_size_mb > self.config.get_file_size_limit():
                        logging.error(f"文件超过大小限制 ({file_size_mb:.2f}MB): {source_file}")
                        skip_count += 1
                        continue
                except OSError:
                    logging.error(f"无法获取文件大小: {source_file}")
                    error_count += 1
                    continue

                # 检查是否需要更新
                if self.file_utils._need_update(source_file, dest_file):
                    # 确保目标目录存在
                    os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                    
                    # 执行备份
                    logging.info(f"备份开始: {source_file} -> {dest_file}")
                    if self.file_utils.safe_copy(source_file, dest_file):
                        logging.info(f"备份完成: {source_file} -> {dest_file}")
                        success_count += 1
                    else:
                        logging.error(f"文件备份失败: {source_file}")
                        error_count += 1
                else:
                    # logging.debug(f"文件无需更新: {source_file}")
                    skip_count += 1

            except Exception as e:
                logging.error(f"处理文件失败 {source_file}: {str(e)}")
                error_count += 1
            finally:
                processed_files += 1
                if callback:
                    callback(processed_files, total_files)

        return success_count, skip_count, error_count

    def _fallback_file_scan(self, source_path: str, incremental_days: int, file_size_limit: int) -> List[dict]:
        """当 Everything 搜索失败时的回退文件扫描方法"""
        logging.info("正在使用文件系统遍历")
        files = []
        
        for root, dirs, filenames in os.walk(source_path):
            # 检查路径长度
            if len(root) > 240:
                logging.warning(f"跳过路径过长的目录: {root}")
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
                    logging.error(f"无法获取文件信息 {file_path}: {str(e)}")
                    continue
                    
        return files 