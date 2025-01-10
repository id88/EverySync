import time
from drive_monitor import DriveMonitor
import logging

def setup_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def drive_status_callback(drive: str, is_available: bool):
    """驱动器状态变化回调函数"""
    status = "可用" if is_available else "不可用"
    print(f"驱动器 {drive} 状态: {status}")

def test_drive_monitor():
    setup_logging()
    monitor = DriveMonitor()
    
    print("\n1. 获取所有驱动器信息:")
    for drive, info in monitor.drives_cache.items():
        print(f"\n驱动器: {drive}")
        print(f"类型: {info['type']}")
        if info['volume_info']:
            print(f"卷标: {info['volume_info']['name']}")
            print(f"文件系统: {info['volume_info']['file_system']}")
        print(f"总空间: {monitor.format_size(info['total_space'])}")
        print(f"可用空间: {monitor.format_size(info['free_space'])}")
        print(f"就绪状态: {'就绪' if info['is_ready'] else '未就绪'}")

    print("\n2. 测试驱动器监控:")
    test_drive = "G:"  # 替换为你要测试的驱动器
    print(f"等待驱动器 {test_drive} 就绪（5秒超时）...")
    is_ready = monitor.wait_for_drive(test_drive, timeout=5, callback=drive_status_callback)
    print(f"驱动器 {test_drive} {'已就绪' if is_ready else '未就绪'}")

    if is_ready:
        print(f"\n3. 获取驱动器 {test_drive} 详细信息:")
        drive_info = monitor.get_drive_info(test_drive)
        if drive_info:
            print(f"类型: {drive_info['type']}")
            if drive_info['volume_info']:
                print(f"卷标: {drive_info['volume_info']['name']}")
                print(f"文件系统: {drive_info['volume_info']['file_system']}")
            print(f"总空间: {monitor.format_size(drive_info['total_space'])}")
            print(f"可用空间: {monitor.format_size(drive_info['free_space'])}")
            print(f"就绪状态: {'就绪' if drive_info['is_ready'] else '未就绪'}")

if __name__ == "__main__":
    test_drive_monitor() 