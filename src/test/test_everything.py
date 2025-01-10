import os
from everything import Everything
from datetime import datetime

def format_size(size_in_bytes: int) -> str:
    """格式化文件大小显示"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024.0
    return f"{size_in_bytes:.2f} PB"

def test_everything():
    try:
        print("正在初始化 Everything API...")
        everything = Everything()
        print("Everything API 初始化成功")

        # 测试1: 搜索特定目录下的所有文件
        test_dir = "D:\\Everything"
        print(f"\n测试1: 搜索目录 {test_dir} 下的所有文件")
        try:
            files = everything.search_files_in_directory(test_dir)
            if not files:
                print("未找到任何文件")
            else:
                for i, file in enumerate(files, 1):
                    modified_time = datetime.fromtimestamp(file['modified_time']).strftime('%Y-%m-%d %H:%M:%S')
                    print(f"{i}. 文件: {file['path']}")
                    print(f"   大小: {format_size(file['size'])}")
                    print(f"   修改时间: {modified_time}")
        except Exception as e:
            print(f"搜索目录时出错: {str(e)}")

        # 测试2: 获取特定文件信息
        test_file = "D:\\Everything\\Everything.exe"
        print(f"\n测试2: 获取文件信息 {test_file}")
        file_info = everything.get_file_info(test_file)
        
        if file_info:
            modified_time = datetime.fromtimestamp(file_info['modified_time']).strftime('%Y-%m-%d %H:%M:%S')
            print(f"文件存在:")
            print(f"路径: {file_info['path']}")
            print(f"大小: {format_size(file_info['size'])}")
            print(f"修改时间: {modified_time}")
        else:
            print("文件不存在")

        # 测试3: 搜索最近修改的文件
        print("\n测试3: 搜索最近一天修改的txt文件（最多显示3个）")
        recent_files = everything.search("ext:txt dm:today", max_results=3)
        
        if recent_files:
            for i, file in enumerate(recent_files):
                size_kb = file['size'] / 1024  # 转换为KB
                modified_time = datetime.fromtimestamp(file['modified_time']).strftime('%Y-%m-%d %H:%M:%S')
                print(f"{i+1}. 文件: {file['path']}")
                print(f"   大小: {size_kb:.2f} KB")
                print(f"   修改时间: {modified_time}")
        else:
            print("未找到最近修改的txt文件")

        print("\n所有测试完成!")

    except Exception as e:
        print(f"测试过程中发生错误: {str(e)}")
        import traceback
        print("详细错误信息:")
        print(traceback.format_exc())

if __name__ == "__main__":
    test_everything() 