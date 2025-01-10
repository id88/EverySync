import os
import time
from backup import Backup
from config import Config
from logger import Logger
import logging
import shutil
import stat

def setup_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def backup_progress_callback(current: int, total: int):
    """备份进度回调函数"""
    progress = (current / total) * 100 if total > 0 else 0
    print(f"备份进度: {progress:.2f}% ({current}/{total})")

def verify_progress_callback(current: int, total: int):
    """验证进度回调函数"""
    progress = (current / total) * 100 if total > 0 else 0
    print(f"验证进度: {progress:.2f}% ({current}/{total})")

def create_test_files(test_dir: str):
    """创建测试文件和目录"""
    # 创建测试目录结构
    os.makedirs(test_dir, exist_ok=True)
    
    # 创建测试文件
    files = {
        'test1.txt': 'This is test file 1',
        'test2.txt': 'This is test file 2',
        'docs/doc1.md': '# Test Document 1',
        'docs/doc2.md': '# Test Document 2',
        'images/img1.txt': 'Simulated image 1',
        'images/img2.txt': 'Simulated image 2'
    }
    
    for file_path, content in files.items():
        full_path = os.path.join(test_dir, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    return files.keys()

def safe_remove_dir(dir_path: str):
    """安全地删除目录及其内容"""
    if not os.path.exists(dir_path):
        return

    def handle_error(func, path, exc_info):
        """处理删除错误"""
        print(f"删除失败 {path}: {exc_info[1]}")
        if os.path.isfile(path):
            try:
                os.chmod(path, stat.S_IWRITE)
                os.unlink(path)
            except:
                pass
        elif os.path.isdir(path):
            try:
                os.chmod(path, stat.S_IWRITE)
                os.rmdir(path)
            except:
                pass

    shutil.rmtree(dir_path, onerror=handle_error)

def test_backup():
    """测试备份功能"""
    setup_logging()
    
    # 创建测试目录
    test_source = "test_source"
    test_dest = "test_dest"
    
    try:
        # 创建测试配置
        config = {
            'backup': {
                'sources': {test_source: test_dest},
                'file_size_limit_mb': 100,
                'incremental_days': 0,
                'verification_sample_size': 2
            },
            'log': {
                'level': 'DEBUG'
            }
        }
        
        # 清理之前的测试文件
        for dir_path in [test_source, test_dest]:
            safe_remove_dir(dir_path)
        
        # 创建测试文件
        print("\n1. 创建测试文件:")
        test_files = create_test_files(test_source)
        print(f"创建了 {len(test_files)} 个测试文件")
        
        logger = Logger(config['log'])
        backup_manager = Backup(config['backup'], logger)
        
        print("\n2. 开始备份:")
        success = backup_manager.start_backup(callback=backup_progress_callback)
        print(f"备份{'成功' if success else '失败'}")
        
        if success:
            print("\n3. 验证备份:")
            is_valid = backup_manager.verify_backup(callback=verify_progress_callback)
            print(f"验证{'通过' if is_valid else '失败'}")
            
            if is_valid:
                print("\n4. 比较源目录和备份目录:")
                for file_path in test_files:
                    source_file = os.path.join(test_source, file_path)
                    dest_file = os.path.join(test_dest, file_path)
                    
                    if not os.path.exists(dest_file):
                        print(f"错误: 文件未备份 - {file_path}")
                        continue
                        
                    source_size = os.path.getsize(source_file)
                    dest_size = os.path.getsize(dest_file)
                    print(f"文件: {file_path}")
                    print(f"  源文件大小: {source_size} bytes")
                    print(f"  备份大小: {dest_size} bytes")
                    print(f"  状态: {'一致' if source_size == dest_size else '不一致'}")
    
    finally:
        # 清理测试文件
        print("\n5. 清理测试文件")
        for dir_path in [test_source, test_dest]:
            safe_remove_dir(dir_path)

if __name__ == "__main__":
    test_backup() 