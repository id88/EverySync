# EverySync 文件备份工具

EverySync 是一个结合 Everything API 实现快速文件比对和备份的工具，支持增量备份和完整备份。

## 功能特点

- 支持多个驱动器和目录的备份
- 支持增量备份和完整备份
- 详细的日志记录
- 灵活的文件排除规则配置
- 实时显示备份进度
- 自动处理路径过长问题
- 集成 Everything 搜索工具，快速定位需要备份的文件
- 智能的线程池管理，自动适应系统资源

## 备份逻辑

### 1. 配置检查
- 从 config.json 加载配置信息
- 从 ignore.txt 加载排除规则
- 验证备份源和目标路径
- 检查驱动器可用性

### 2. 文件扫描
- 优先使用 Everything SDK 获取文件列表
- 根据配置的增量备份天数筛选文件
- 应用 ignore.txt 中的排除规则
- 处理路径长度超过限制的文件
- 在 Everything 不可用时回退到文件系统遍历

### 3. 文件备份
- 对每个文件执行以下操作：
  1. 检查文件是否需要更新（比较大小和修改时间）
  2. 创建目标目录结构
  3. 复制文件
  4. 记录备份状态和日志

### 4. 错误处理
- 跳过无法访问的文件
- 记录错误信息
- 统计成功、失败和跳过的文件数

## 配置说明

### 配置文件 (config.json)
```json
{
  "backup": {
    "sources": {
      "D:\\SourcePath": "G:\\BackupPath",  // 源路径: 目标路径
      "E:": "G:\\E\\"                      // 支持驱动器根目录
    },
    "file_size_limit_mb": 100,             // 文件大小限制（MB）
    "incremental_days": 1,                 // 增量备份天数，0表示完整备份
    "parallel": {
      "enabled": true,                     // 是否启用并行处理
      "max_workers": null,                 // 工作线程数，null表示自动设置
      "small_file_size_mb": 10,           // 小文件阈值（MB）
      "batch_size": 100                   // 小文件批处理数量
    }
  },
  "log": {
    "debug_log_path": "logs\\debug.log",   // 调试日志路径
    "run_log_path": "logs\\run.log",       // 运行日志路径
    "lost_log_path": "logs\\lost.log",     // 丢失文件日志路径
    "trace_enabled": false                 // 是否启用跟踪日志
  }
}
```

### 排除规则 (ignore.txt)
```text
# 系统文件和目录
$RECYCLE.BIN
System Volume Information
pagefile.sys

# 开发相关
.git
.svn
node_modules

# 临时文件
*.tmp
*.log
```

## 使用方法

1. 编辑 config.json 配置备份源和目标路径
2. 编辑 ignore.txt 配置排除规则
3. 运行 run.bat 或执行 `python src/main.py`
4. 查看控制台输出和日志文件了解备份状态

## 日志文件

- debug.log: 详细的调试信息
- run.log: 运行时的主要操作记录
- lost.log: 丢失文件的记录

## 注意事项

1. 首次运行建议进行完整备份（incremental_days = 0）
2. 定期检查日志文件了解备份状态
3. 路径长度超过240字符的文件将被跳过

## 依赖项

- Python 3.7+
- Everything 搜索工具（可选，推荐安装）
- Windows 7/10/11

## 性能优化

### 1. 利用 Everything 的 MFT 读取能力

Everything 通过直接读取 NTFS 的 Master File Table (MFT) 来实现快速文件搜索。我们可以利用这一特性来优化文件扫描过程：

1. **优化搜索查询**：
   - 使用 Everything 的高级搜索语法来快速定位需要备份的文件。
   - 示例代码：
     ```python
     def get_files_from_everything(path: str, days: int = 7) -> List[dict]:
         everything = Everything()
         query = f'path:{path} dm:last{days}days'  # 最近N天修改的文件
         return everything.search(query)
     ```

2. **高级搜索语法优化**：
   - 使用日期过滤：`dm:last7days` 或 `dm:prev7days` 或 `dm:past7days`（最近7天修改）
   - 使用大小过滤：`size:>100mb`
   - 使用路径过滤：`path:"D:\Project\" !path:".git\"`
   - 使用文件属性：`!attrib:S !attrib:H`（排除系统和隐藏文件）
   - 使用特定文件类型：`ext:txt`

3. **实时监控文件变化**：
   - 利用 Everything 的 IPC 机制获取文件变更通知。
   - 实时更新本地数据库，减少全盘扫描的需求。

### 2. 建立本地文件索引

为了避免每次都进行全盘扫描，可以建立一个本地数据库（如 SQLite）来存储文件信息：

1. **数据库结构**：
   - 存储文件路径、大小、修改时间、MD5值、最后备份时间和最后检查时间。
   - 示例 SQL 语句：
     ```sql
     CREATE TABLE files (
         path TEXT PRIMARY KEY,
         size INTEGER,
         modified_time INTEGER,
         md5 TEXT,
         last_backup_time INTEGER,
         last_check_time INTEGER
     );
     ```
    - **last_backup_time**：
        - 记录文件最后一次被成功备份的时间
        - 用于增量备份时判断文件是否需要备份
        - 当文件被成功备份后更新此时间戳
    - **last_check_time**：
        - 记录文件最后一次被检查（比对）的时间
        - 用于优化文件比对过程，避免重复检查未变化的文件
        - 即使文件没有被备份，只要进行了比对，就会更新此时间戳


2. **增量更新策略**：
   
   - 首次运行时建立完整索引。
   - 后续运行只扫描修改时间晚于上次备份的文件。
   - 定期（如每月）进行一次全量索引更新。
   
3. **分离索引更新和备份操作**：
   - 后台任务定期更新文件索引。
   - 备份时直接使用索引数据。
   - 可以通过文件系统事件监控（如 watchdog）实时更新索引。

### 3. 并行处理优化

1. **多线程文件复制**：
   - 使用多线程来同时复制多个文件，提高备份速度。
   - 示例代码：
     ```python
     from concurrent.futures import ThreadPoolExecutor
     
     def parallel_backup(files: List[dict], max_workers: int = 4):
         with ThreadPoolExecutor(max_workers=max_workers) as executor:
             futures = [executor.submit(backup_file, f) for f in files]
     ```

2. **分块处理大文件**：
   - 将大文件分块并行复制。
   - 使用多线程计算MD5值。
   - 支持断点续传。

3. **优先级队列**：
   - 小文件优先处理。
   - 最近修改的文件优先。
   - 重要目录优先。

### 4. 其他优化

1. **缓存策略**：
   - 缓存文件MD5值。
   - 缓存目录结构。
   - 使用内存映射文件处理大文件。

2. **预处理优化**：
   - 预先创建目录结构。
   - 批量检查文件可访问性。
   - 提前计算空间需求。

3. **IO优化**：
   - 使用更大的缓冲区。
   - 合并小文件操作。
   - 使用异步IO。

4. **存储优化**：
   - 压缩备份文件。
   - 删除重复文件。
   - 智能处理符号链接。

## 实现路线图

1. 第一阶段：基础功能
   - [x] 基本的文件复制
   - [x] 增量备份和全量备份支持
   - [x] 日志记录
   - [x] Everything API 集成
   - [x] 排除规则支持

2. 第二阶段：性能优化
   - [x] 并行文件复制
   - [ ] 大文件分块处理
   - [ ] 断点续传支持
   - [ ] 重复文件处理

3. 第三阶段：高级特性
   - [ ] 实时文件监控

4. 第四阶段：用户体验
   - [ ] 图形界面
   - [ ] 备份计划管理
   - [ ] 状态监控和报告 