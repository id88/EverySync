# EverySync 文件备份工具

EverySync 是一个结合 Everything API，实现快速文件比对和备份的工具，支持增量备份和完整备份。

## 功能特点

- 支持多个驱动器和目录的备份
- 支持增量备份和完整备份
- 自动验证备份文件的完整性
- 详细的日志记录
- 文件过滤和排除规则
- 实时显示备份进度
- 自动处理路径过长问题

## 备份逻辑

### 1. 配置检查
- 从 config.json 加载配置信息
- 验证备份源和目标路径
- 检查驱动器可用性

### 2. 文件扫描
- 使用 Everything SDK 或文件系统遍历获取文件列表
- 根据配置的增量备份天数筛选文件：
  ```python
  if config['backup']['incremental_days'] > 0:
      cutoff_time = datetime.now() - timedelta(days=incremental_days)
      files = [f for f in files if file_modified_time > cutoff_time]
  ```
- 过滤系统文件和特殊目录
- 处理路径长度超过限制的文件

### 3. 文件备份
- 对每个文件执行以下操作：
  1. 检查文件是否需要更新（比较大小和修改时间）
  2. 创建目标目录结构
  3. 复制文件并验证完整性（MD5校验）
  4. 记录备份状态和日志

### 4. 备份验证
- 随机抽样验证备份文件
- 比较源文件和备份文件的：
  - 文件大小
  - MD5值
  - 修改时间

### 5. 错误处理
- 跳过无法访问的文件
- 记录错误信息
- 统计成功、失败和跳过的文件数

## 配置说明

配置文件 (config.json) 示例：
```json
{
    "backup": {
        "sources": {
            "D:": "G:\\D",
            "E:": "G:\\E"
        },
        "exclude_patterns": {
            "directories": [
                "node_modules",
                ".git"
            ],
            "files": [
                "*.tmp",
                "*.log"
            ]
        },
        "file_size_limit": 100,
        "incremental_days": 7,
        "verification_sample_size": 10
    }
}
```

- `sources`: 备份源和目标路径映射
- `exclude_patterns`: 排除规则
- `file_size_limit`: 单个文件大小限制（MB）
- `incremental_days`: 增量备份天数（0表示完整备份）
- `verification_sample_size`: 验证时的抽样数量

## 使用方法

1. 编辑 config.json 配置文件
2. 运行 run.bat 或执行 `python src/main.py`
3. 查看控制台输出和日志文件了解备份状态

## 日志文件

- debug.log: 详细的调试信息
- run.log: 运行时的主要操作记录

## 注意事项

1. 首次运行建议进行完整备份（incremental_days = 0）
2. 定期检查日志文件了解备份状态
3. 建议定期验证备份文件的完整性
4. 路径长度超过240字符的文件将被跳过
5. 系统文件和特殊目录会被自动排除 

## 性能优化建议

### 1. 备份文件索引
为了避免每次都进行全盘扫描，可以实现以下优化：

1. 建立本地数据库（如 SQLite）存储文件信息：
```python
{
    "file_path": "文件路径",
    "size": "文件大小",
    "modified_time": "修改时间",
    "md5": "文件MD5值",
    "last_backup_time": "最后备份时间"
}
```

2. 增量更新策略：
   - 首次运行时建立完整索引
   - 后续运行只扫描修改时间晚于上次备份的文件
   - 定期（如每月）进行一次全量索引更新

3. 分离索引更新和备份操作：
   - 后台任务定期更新文件索引
   - 备份时直接使用索引数据
   - 可以通过文件系统事件监控（如 watchdog）实时更新索引

### 2. 利用 Everything 索引
由于 Everything 已经建立了完整的 NTFS 索引，可以通过以下方式提升效率：

1. 使用 Everything IPC 接口：
```python
# 示例代码
from everything_ipc import Everything

def get_files_from_everything(path: str) -> List[dict]:
    everything = Everything()
    # 使用高级搜索语法
    query = f'path:"{path}\\" !folder: dm:"today..-7days"'
    return everything.query(query)
```

2. 高级搜索语法优化：
   - 使用日期过滤：`dm:"today..-7days"`（最近7天修改）
   - 使用大小过滤：`size:>100mb`
   - 使用路径过滤：`path:"D:\Project\" !path:".git\"`

3. 实时更新集成：
   - 监听 Everything 的 IPC 消息
   - 实时获取文件变更通知
   - 更新本地索引数据库

### 3. 并行处理优化

1. 多线程文件复制：
```python
from concurrent.futures import ThreadPoolExecutor

def parallel_backup(files: List[dict], max_workers: int = 4):
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(backup_file, f) for f in files]
```

2. 分块处理大文件：
   - 将大文件分块并行复制
   - 使用多线程计算MD5值
   - 支持断点续传

3. 优先级队列：
   - 小文件优先处理
   - 最近修改的文件优先
   - 重要目录优先

### 4. 其他优化建议

1. 缓存策略：
   - 缓存文件MD5值
   - 缓存目录结构
   - 使用内存映射文件处理大文件

2. 预处理优化：
   - 预先创建目录结构
   - 批量检查文件可访问性
   - 提前计算空间需求

3. IO优化：
   - 使用更大的缓冲区
   - 合并小文件操作
   - 使用异步IO

4. 存储优化：
   - 压缩备份文件
   - 删除重复文件
   - 智能处理符号链接

## 实现路线图

1. 第一阶段：基础功能
   - [x] 基本的文件复制和验证
   - [x] 增量备份支持
   - [x] 日志记录

2. 第二阶段：性能优化
   - [ ] 实现本地索引数据库
   - [ ] Everything 集成优化
   - [ ] 多线程支持

3. 第三阶段：高级特性
   - [ ] 实时文件监控
   - [ ] 断点续传
   - [ ] 重复文件处理

4. 第四阶段：用户体验
   - [ ] 图形界面
   - [ ] 备份计划管理
   - [ ] 状态监控和报告 