import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Callable
import logging
from file_utils import FileUtils

class ParallelBackup:
    def __init__(self, config: dict, file_utils: FileUtils, logger: Callable):
        """
        初始化并行备份处理器
        
        Args:
            config: 并行处理配置
            file_utils: 文件工具实例
            logger: 日志记录函数
        """
        self.config = config
        self.file_utils = file_utils
        self.logger = logger
        self.max_workers = config['max_workers'] or min(32, (os.cpu_count() or 1) * 4)
        self.small_file_threshold = config['small_file_size_mb'] * 1024 * 1024  # 转换为字节
        self.batch_size = config['batch_size']
        logging.info(f"并行备份初始化完成: 工作线程数={self.max_workers}, 小文件阈值={config['small_file_size_mb']}MB")

    def backup_files(self, files: List[dict], callback: Callable = None) -> tuple:
        """
        并行处理文件备份
        
        Args:
            files: 待备份的文件列表
            callback: 进度回调函数

        Returns:
            tuple: (成功数, 跳过数, 错误数)
        """
        # 分类文件
        small_files = []
        large_files = []
        for file in files:
            if file.get('size', 0) < self.small_file_threshold:
                small_files.append(file)
            else:
                large_files.append(file)

        total_files = len(files)
        processed_count = 0
        success_count = 0
        skip_count = 0
        error_count = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []

            # 处理小文件（批量）
            for i in range(0, len(small_files), self.batch_size):
                batch = small_files[i:i + self.batch_size]
                future = executor.submit(self._backup_small_files_batch, batch)
                futures.append(future)

            # 处理大文件（单独）
            for file in large_files:
                future = executor.submit(self._backup_single_file, file)
                futures.append(future)

            # 等待所有任务完成并处理结果
            for future in as_completed(futures):
                try:
                    batch_success, batch_skip, batch_error = future.result()
                    success_count += batch_success
                    skip_count += batch_skip
                    error_count += batch_error
                    processed_count += batch_success + batch_skip + batch_error
                    
                    if callback:
                        callback(processed_count, total_files)
                except Exception as e:
                    self.logger(f"并行处理任务失败: {str(e)}")
                    error_count += 1

        return success_count, skip_count, error_count

    def _backup_small_files_batch(self, files: List[dict]) -> tuple:
        """处理小文件批次"""
        success = 0
        skip = 0
        error = 0
        
        for file in files:
            try:
                source_path = file['path']
                dest_path = file['dest_path']
                
                if not self.file_utils._need_update(source_path, dest_path):
                    # logging.debug(f"文件无需更新: {source_path}")
                    skip += 1
                    continue
                    
                logging.debug(f"开始备份小文件: {source_path}")
                if self.file_utils.safe_copy(source_path, dest_path):
                    logging.debug(f"小文件备份成功: {source_path}")
                    success += 1
                else:
                    logging.error(f"小文件备份失败: {source_path}")
                    error += 1
            except Exception as e:
                logging.error(f"备份文件失败 {file['path']}: {str(e)}")
                error += 1
                
        return success, skip, error

    def _backup_single_file(self, file: dict) -> tuple:
        """处理单个大文件"""
        try:
            source_path = file['path']
            dest_path = file['dest_path']
            
            if not self.file_utils._need_update(source_path, dest_path):
                return 0, 1, 0
                
            if self.file_utils.safe_copy(source_path, dest_path):
                return 1, 0, 0
            else:
                return 0, 0, 1
        except Exception as e:
            self.logger(f"备份文件失败 {file['path']}: {str(e)}")
            return 0, 0, 1 