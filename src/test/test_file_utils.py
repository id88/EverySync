import os
import time
from file_utils import FileUtils
import logging

def setup_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def test_file_utils():
    setup_logging()
    
    # 创建测试文件
    test_dir = "test_files"
    os.makedirs(test_dir, exist_ok=True)
    
    # 测试文件路径
    source_file = os.path.join(test_dir, "source.txt")
    dest_file = os.path.join(test_dir, "dest.txt")
    
    try:
        # 创建测试文件
        with open(source_file, "w") as f:
            f.write("This is a test file.")
        
        print("\n1. 测试文件信息获取:")
        file_info = FileUtils.get_file_info(source_file)
        if file_info:
            print(f"文件大小: {FileUtils.format_size(file_info['size'])}")
            print(f"MD5: {file_info['md5']}")
            print(f"修改时间: {time.ctime(file_info['modified_time'])}")
        
        print("\n2. 测试文件复制:")
        if FileUtils.safe_copy(source_file, dest_file):
            print("文件复制成功")
        
        print("\n3. 测试文件比较:")
        is_same, reason = FileUtils.compare_files(source_file, dest_file)
        print(f"文件比较结果: {reason}")
        
        print("\n4. 测试最近修改检查:")
        is_recent = FileUtils.is_file_modified_recently(source_file, 1)
        print(f"文件是否最近被修改: {is_recent}")
        
    finally:
        # 清理测试文件
        if os.path.exists(source_file):
            os.remove(source_file)
        if os.path.exists(dest_file):
            os.remove(dest_file)
        if os.path.exists(test_dir):
            os.rmdir(test_dir)

if __name__ == "__main__":
    test_file_utils() 