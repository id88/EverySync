import ctypes
from ctypes import wintypes
import os
from typing import List, Optional
from datetime import datetime, timezone

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
        # Everything_SetSearch
        self.everything_dll.Everything_SetSearchW.argtypes = [wintypes.LPCWSTR]
        self.everything_dll.Everything_SetSearchW.restype = None

        # Everything_SetRequestFlags
        self.everything_dll.Everything_SetRequestFlags.argtypes = [wintypes.DWORD]
        self.everything_dll.Everything_SetRequestFlags.restype = None

        # Everything_GetResultFullPathName
        self.everything_dll.Everything_GetResultFullPathNameW.argtypes = [
            wintypes.DWORD,
            wintypes.LPWSTR,
            wintypes.DWORD
        ]
        self.everything_dll.Everything_GetResultFullPathNameW.restype = wintypes.DWORD

        # Everything_Query
        self.everything_dll.Everything_QueryW.argtypes = [wintypes.BOOL]
        self.everything_dll.Everything_QueryW.restype = wintypes.BOOL

        # Everything_GetNumResults
        self.everything_dll.Everything_GetNumResults.argtypes = []
        self.everything_dll.Everything_GetNumResults.restype = wintypes.DWORD

        # Everything_GetResultSize
        self.everything_dll.Everything_GetResultSize.argtypes = [wintypes.DWORD]
        self.everything_dll.Everything_GetResultSize.restype = wintypes.LARGE_INTEGER

        # Everything_GetResultDateModified
        self.everything_dll.Everything_GetResultDateModified.argtypes = [wintypes.DWORD]
        self.everything_dll.Everything_GetResultDateModified.restype = wintypes.LARGE_INTEGER

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

        # Everything_SetMatchPath
        self.everything_dll.Everything_SetMatchPath.argtypes = [wintypes.BOOL]
        self.everything_dll.Everything_SetMatchPath.restype = None

        # Everything_SetMatchCase
        self.everything_dll.Everything_SetMatchCase.argtypes = [wintypes.BOOL]
        self.everything_dll.Everything_SetMatchCase.restype = None

        # Everything_SetMatchWholeWord
        self.everything_dll.Everything_SetMatchWholeWord.argtypes = [wintypes.BOOL]
        self.everything_dll.Everything_SetMatchWholeWord.restype = None

    def _windows_date_to_unix_timestamp(self, windows_time: int) -> int:
        """将Windows文件时间转换为Unix时间戳"""
        if windows_time == 0:
            return 0
        # Windows文件时间是从1601年1月1日开始的100纳秒间隔数
        # Unix时间戳是从1970年1月1日开始的秒数
        # 需要减去11644473600秒（1601年到1970年的秒数）
        return int((windows_time / 10000000) - 11644473600)

    def search(self, query: str, max_results: int = 1000) -> List[dict]:
        """执行搜索并返回结果"""
        try:
            # 重置之前的搜索状态
            self.everything_dll.Everything_Reset()
            
            # 设置搜索选项
            self.everything_dll.Everything_SetMatchPath(True)
            self.everything_dll.Everything_SetMatchCase(False)
            self.everything_dll.Everything_SetMatchWholeWord(False)
            
            # 设置请求标志
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
            
            # 检查数据库是否已加载
            if not self.everything_dll.Everything_IsDBLoaded():
                raise RuntimeError("Everything 数据库未加载")

            # 设置搜索字符串
            self.everything_dll.Everything_SetSearchW(query)

            # 执行搜索
            if not self.everything_dll.Everything_QueryW(True):
                error = self.everything_dll.Everything_GetLastError()
                raise RuntimeError(f"Everything 搜索失败，错误代码：{error}")

            # 获取结果数量
            num_results = min(self.everything_dll.Everything_GetNumResults(), max_results)
            results = []

            # 获取搜索结果
            for i in range(num_results):
                try:
                    # 获取完整路径
                    path_buffer = ctypes.create_unicode_buffer(260)  # MAX_PATH
                    path_length = self.everything_dll.Everything_GetResultFullPathNameW(i, path_buffer, 260)
                    if path_length == 0:
                        continue

                    file_path = path_buffer.value
                    if not os.path.exists(file_path):
                        continue

                    # 获取文件大小和修改时间
                    try:
                        size = os.path.getsize(file_path)
                        modified_time = int(os.path.getmtime(file_path))
                    except (OSError, IOError) as e:
                        print(f"警告：无法获取文件信息 {file_path}: {str(e)}")
                        continue

                    results.append({
                        'path': file_path,
                        'size': size,
                        'modified_time': modified_time
                    })
                except Exception as e:
                    print(f"警告：处理搜索结果 {i} 时出错：{str(e)}")
                    continue

            return results
            
        except Exception as e:
            raise RuntimeError(f"搜索过程中发生错误: {str(e)}")
        finally:
            # 清理搜索状态
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

    def __del__(self):
        """清理 Everything SDK 资源"""
        if hasattr(self, 'everything_dll'):
            self.everything_dll.Everything_Reset() 