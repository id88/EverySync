import ctypes
from ctypes import wintypes
import os
from typing import List, Optional
from datetime import datetime, timezone
import time
import logging

class Everything:
    # Everything SDK 常量定义
    EVERYTHING_OK = 0
    EVERYTHING_ERROR_MEMORY = 1
    EVERYTHING_ERROR_IPC = 2
    EVERYTHING_ERROR_REGISTERCLASSEX = 3
    EVERYTHING_ERROR_CREATEWINDOW = 4
    EVERYTHING_ERROR_CREATETHREAD = 5
    EVERYTHING_ERROR_INVALIDINDEX = 6
    EVERYTHING_ERROR_INVALIDCALL = 7

    # Everything SDK 搜索标志
    EVERYTHING_REQUEST_FILE_NAME = 0x00000001
    EVERYTHING_REQUEST_PATH = 0x00000002
    EVERYTHING_REQUEST_FULL_PATH_AND_FILE_NAME = 0x00000004
    EVERYTHING_REQUEST_SIZE = 0x00000008
    EVERYTHING_REQUEST_DATE_MODIFIED = 0x00000010
    EVERYTHING_REQUEST_DATE_CREATED = 0x00000020
    EVERYTHING_REQUEST_DATE_ACCESSED = 0x00000040
    EVERYTHING_REQUEST_ATTRIBUTES = 0x00000080
    EVERYTHING_REQUEST_FILE_LIST_FILE_NAME = 0x00000100
    EVERYTHING_REQUEST_RUN_COUNT = 0x00000200
    EVERYTHING_REQUEST_DATE_RUN = 0x00000400
    EVERYTHING_REQUEST_DATE_RECENTLY_CHANGED = 0x00000800
    EVERYTHING_REQUEST_HIGHLIGHTED_FILE_NAME = 0x00001000
    EVERYTHING_REQUEST_HIGHLIGHTED_PATH = 0x00002000
    EVERYTHING_REQUEST_HIGHLIGHTED_FULL_PATH_AND_FILE_NAME = 0x00004000

    # 排序常量
    EVERYTHING_SORT_NAME_ASCENDING = 1
    EVERYTHING_SORT_NAME_DESCENDING = 2
    EVERYTHING_SORT_PATH_ASCENDING = 3
    EVERYTHING_SORT_PATH_DESCENDING = 4
    EVERYTHING_SORT_SIZE_ASCENDING = 5
    EVERYTHING_SORT_SIZE_DESCENDING = 6
    EVERYTHING_SORT_DATE_MODIFIED_ASCENDING = 7
    EVERYTHING_SORT_DATE_MODIFIED_DESCENDING = 8
    EVERYTHING_SORT_DATE_CREATED_ASCENDING = 9
    EVERYTHING_SORT_DATE_CREATED_DESCENDING = 10
    EVERYTHING_SORT_DATE_ACCESSED_ASCENDING = 11
    EVERYTHING_SORT_DATE_ACCESSED_DESCENDING = 12

    def __init__(self):
        # 获取项目根目录
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        dll_path = os.path.join(current_dir, 'sdk', 'dll', 'Everything64.dll')
        
        # 加载 Everything SDK
        try:
            self.everything_dll = ctypes.WinDLL(dll_path)
        except Exception as e:
            raise RuntimeError(f"无法加载 Everything64.dll，文件路径: {dll_path}") from e

        # 初始化函数原型
        self._init_functions()
        
        # 初始化 Everything
        if not self.everything_dll.Everything_GetLastError() == self.EVERYTHING_OK:
            raise RuntimeError("Everything 服务未运行")
            
        # 重置 Everything 搜索状态
        self.everything_dll.Everything_Reset()
        
        # 设置默认搜索标志
        request_flags = (
            self.EVERYTHING_REQUEST_FILE_NAME |
            self.EVERYTHING_REQUEST_PATH |
            self.EVERYTHING_REQUEST_SIZE |
            self.EVERYTHING_REQUEST_DATE_MODIFIED |
            self.EVERYTHING_REQUEST_DATE_CREATED |
            self.EVERYTHING_REQUEST_DATE_ACCESSED |
            self.EVERYTHING_REQUEST_ATTRIBUTES
        )
        self.everything_dll.Everything_SetRequestFlags(request_flags)

    def _init_functions(self):
        """初始化 Everything SDK 函数"""
        try:
            # Everything_SetSearch (Unicode version)
            self.everything_dll.Everything_SetSearchW.argtypes = [wintypes.LPCWSTR]
            self.everything_dll.Everything_SetSearchW.restype = None

            # Everything_Query
            self.everything_dll.Everything_QueryW.argtypes = [wintypes.BOOL]
            self.everything_dll.Everything_QueryW.restype = wintypes.BOOL

            # Everything_GetNumResults
            self.everything_dll.Everything_GetNumResults.argtypes = []
            self.everything_dll.Everything_GetNumResults.restype = wintypes.DWORD

            # Everything_GetResultFullPathName
            self.everything_dll.Everything_GetResultFullPathNameW.argtypes = [
                wintypes.DWORD,
                wintypes.LPWSTR,
                wintypes.DWORD
            ]
            self.everything_dll.Everything_GetResultFullPathNameW.restype = wintypes.DWORD

            # Everything_GetLastError
            self.everything_dll.Everything_GetLastError.argtypes = []
            self.everything_dll.Everything_GetLastError.restype = wintypes.DWORD

            # Everything_Reset
            self.everything_dll.Everything_Reset.argtypes = []
            self.everything_dll.Everything_Reset.restype = None

            # Everything_IsDBLoaded
            self.everything_dll.Everything_IsDBLoaded.argtypes = []
            self.everything_dll.Everything_IsDBLoaded.restype = wintypes.BOOL

            # Everything_SetSort
            self.everything_dll.Everything_SetSort.argtypes = [wintypes.DWORD]
            self.everything_dll.Everything_SetSort.restype = None

            # Everything_SetRequestFlags
            self.everything_dll.Everything_SetRequestFlags.argtypes = [wintypes.DWORD]
            self.everything_dll.Everything_SetRequestFlags.restype = None

            logging.debug("Everything SDK 函数初始化成功")
            
        except AttributeError as e:
            raise RuntimeError(f"Everything SDK 函数初始化失败: {str(e)}")

    def _windows_date_to_unix_timestamp(self, windows_time: int) -> int:
        """将Windows文件时间转换为Unix时间戳"""
        if windows_time == 0:
            return 0
        # Windows文件时间是从1601年1月1日开始的100纳秒间隔数
        # Unix时间戳是从1970年1月1日开始的秒数
        # 需要减去11644473600秒（1601年到1970年的秒数）
        return int((windows_time / 10000000) - 11644473600)

    def search(self, query: str, max_results: int = 100, timeout: int = 30) -> List[dict]:
        """执行搜索并返回结果"""
        try:
            # 检查 Everything 服务
            if not self.everything_dll.Everything_IsDBLoaded():
                logging.error("Everything 数据库未加载")
                return []
            
            # 重置搜索状态
            self.everything_dll.Everything_Reset()
            logging.debug("重置搜索状态完成")
            
            # 设置搜索选项
            self.everything_dll.Everything_SetMatchPath(True)
            self.everything_dll.Everything_SetMatchCase(False)
            self.everything_dll.Everything_SetMatchWholeWord(False)
            
            # 设置排序（按修改时间降序）
            self.everything_dll.Everything_SetSort(self.EVERYTHING_SORT_DATE_MODIFIED_DESCENDING)
            logging.debug("搜索选项设置完成")
            
            # 设置请求标志
            request_flags = (
                self.EVERYTHING_REQUEST_FILE_NAME |
                self.EVERYTHING_REQUEST_PATH |
                self.EVERYTHING_REQUEST_SIZE |
                self.EVERYTHING_REQUEST_DATE_MODIFIED
            )
            self.everything_dll.Everything_SetRequestFlags(request_flags)
            
            # 设置搜索字符串
            self.everything_dll.Everything_SetSearchW(query)
            logging.debug(f"设置搜索字符串完成")
            
            # 执行搜索（带超时）
            start_time = time.time()
            logging.debug(f"开始执行搜索")
            search_success = False
            while not search_success:
                search_success = self.everything_dll.Everything_QueryW(True)
                if not search_success:
                    error_code = self.everything_dll.Everything_GetLastError()
                    logging.debug(f"使用 Everything 搜索失败，错误代码: {error_code}")
                    if time.time() - start_time > timeout:
                        logging.error("Everything 搜索超时")
                        return []
                    time.sleep(0.1)
            
            logging.debug("搜索执行完成")
            
            # 获取结果
            num_results = self.everything_dll.Everything_GetNumResults()
            logging.debug(f"搜索返回结果数量: {num_results}")
            
            if num_results == 0:
                return []
            
            num_results = min(num_results, max_results)
            results = []
            
            for i in range(num_results):
                try:
                    path_buffer = ctypes.create_unicode_buffer(260)
                    path_length = self.everything_dll.Everything_GetResultFullPathNameW(i, path_buffer, 260)
                    
                    if path_length > 0:
                        file_path = path_buffer.value
                        # logging.trace(f"处理搜索结果 {i}: {file_path}")
                        
                        if os.path.exists(file_path):
                            if os.path.isfile(file_path):
                                try:
                                    file_size = os.path.getsize(file_path)
                                    modified_time = int(os.path.getmtime(file_path))
                                    
                                    results.append({
                                        'path': file_path,
                                        'size': file_size,
                                        'modified_time': modified_time
                                    })
                                    # logging.debug(f"添加文件: {file_path}, 大小: {file_size}, 修改时间: {modified_time}")
                                except (OSError, IOError) as e:
                                    logging.warning(f"无法获取文件信息 {file_path}: {str(e)}")
                                    continue
                            else:
                                logging.debug(f"跳过目录: {file_path}")
                        else:
                            logging.debug(f"文件不存在: {file_path}")
                    else:
                        logging.debug(f"无法获取结果 {i} 的路径")
                        
                except Exception as e:
                    logging.warning(f"处理搜索结果 {i} 失败: {str(e)}")
                    continue
            
            logging.debug(f"已成功处理 {len(results)} 个文件")
            return results
            
        except Exception as e:
            logging.error(f"Everything 搜索失败: {str(e)}", exc_info=True)
            return []
        finally:
            self.everything_dll.Everything_Reset()

    def search_files_in_directory(self, directory: str, pattern: str = "*") -> List[dict]:
        """搜索指定目录下的文件"""
        # 确保目录路径以反斜杠结尾
        directory = os.path.normpath(directory)
        if not directory.endswith('\\'):
            directory += '\\'
            
        # 构建搜索查询
        query = f'path:"{directory}"'
        if pattern != "*":
            query += f' {pattern}'
            
        return self.search(query)

    def get_file_info(self, file_path: str) -> Optional[dict]:
        """获取指定文件的信息"""
        # 规范化文件路径
        file_path = os.path.normpath(file_path)
        results = self.search(f'file:"{file_path}"', max_results=1)
        return results[0] if results else None

    def is_available(self) -> bool:
        """检查 Everything 是否可用"""
        try:
            logging.debug("开始检查 Everything 可用性...")
            
            # 等待数据库加载，最多等待15秒
            start_time = time.time()
            timeout = 15  # 15秒超时
            
            while True:
                # 检查数据库状态
                logging.debug("检查 Everything 数据库状态...")
                if self.everything_dll.Everything_IsDBLoaded():
                    logging.debug("Everything 数据库已加载完成")
                    break
                    
                # 检查是否超时
                if time.time() - start_time > timeout:
                    error_code = self.everything_dll.Everything_GetLastError()
                    error_message = {
                        self.EVERYTHING_OK: "数据库正在加载中",
                        self.EVERYTHING_ERROR_IPC: "Everything 搜索客户端未在后台运行",
                        self.EVERYTHING_ERROR_MEMORY: "内存分配失败",
                        self.EVERYTHING_ERROR_REGISTERCLASSEX: "注册窗口类失败",
                        self.EVERYTHING_ERROR_CREATEWINDOW: "创建窗口失败",
                        self.EVERYTHING_ERROR_CREATETHREAD: "创建线程失败",
                        self.EVERYTHING_ERROR_INVALIDINDEX: "无效的索引",
                        self.EVERYTHING_ERROR_INVALIDCALL: "无效的调用"
                    }.get(error_code, f"未知错误 (代码: {error_code})")
                    
                    logging.debug(f"Everything 数据库加载超时: {error_message}")
                    return False
                
                # 等待1s后重试
                time.sleep(1)
                logging.debug("等待 Everything 数据库加载...")
            
            # 执行测试搜索
            try:
                # 重置搜索状态
                self.everything_dll.Everything_Reset()
                logging.debug("重置搜索状态完成")
                
                # 设置请求标志（最小化请求数据）
                request_flags = self.EVERYTHING_REQUEST_FILE_NAME
                self.everything_dll.Everything_SetRequestFlags(request_flags)
                logging.debug("设置请求标志完成")
                
                # 执行搜索，设置超时
                start_time = time.time()
                logging.debug("开始执行搜索")
                while True:
                    if self.everything_dll.Everything_QueryW(True):
                        break
                        
                    if time.time() - start_time > 5:  # 5秒超时
                        logging.debug("搜索测试超时")
                        return False
                        
                    time.sleep(0.1)
                
                # 检查是否能获取结果
                num_results = self.everything_dll.Everything_GetNumResults()
                logging.debug(f"Everything 测试搜索成功，结果数: {num_results}")
                return True
                
            except AttributeError as e:
                logging.debug(f"Everything SDK 函数调用失败: {str(e)}")
                return False
                
        except Exception as e:
            logging.debug(f"Everything 可用性检查失败: {str(e)}")
            return False
        finally:
            # 清理搜索状态
            try:
                self.everything_dll.Everything_Reset()
                logging.debug("Everything 搜索状态已重置")
            except:
                logging.debug("Everything 搜索状态重置失败")
                pass

    def __del__(self):
        """清理 Everything SDK 资源"""
        if hasattr(self, 'everything_dll'):
            self.everything_dll.Everything_Reset() 
            logging.debug("Everything 搜索状态已重置")