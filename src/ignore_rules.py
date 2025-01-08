import os
import logging
from typing import List

class IgnoreRules:
    def __init__(self, ignore_file: str = 'config/ignore.txt'):
        """初始化忽略规则管理器"""
        self.ignore_file = ignore_file
        self.rules = self._load_rules()
        
    def _load_rules(self) -> List[str]:
        """加载忽略规则"""
        rules = []
        
        try:
            if not os.path.exists(self.ignore_file):
                self._create_default_rules()
            
            with open(self.ignore_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # 跳过空行和注释
                    if not line or line.startswith('#'):
                        continue
                    rules.append(line)
            
            logging.debug(f"已加载忽略规则: {len(rules)} 条")
            return rules
            
        except Exception as e:
            logging.error(f"加载忽略规则失败: {str(e)}")
            return rules
            
    def _create_default_rules(self):
        """创建默认的忽略规则文件"""
        default_rules = """# 系统文件和目录
$RECYCLE.BIN\
System Volume Information\
pagefile.sys
hiberfil.sys
swapfile.sys

# 开发相关
.git\
.svn\
node_modules\
.idea\
.vscode\
__pycache__\
D:\Anaconda\

# 临时文件
*.tmp
*.temp
*.log
*.bak
~*

# 缓存目录
Temp\
Cache\
"""
        try:
            os.makedirs(os.path.dirname(self.ignore_file), exist_ok=True)
            with open(self.ignore_file, 'w', encoding='utf-8') as f:
                f.write(default_rules)
            logging.debug(f"已创建默认忽略规则文件: {self.ignore_file}")
        except Exception as e:
            logging.error(f"创建默认忽略规则文件失败: {str(e)}")

    def get_everything_query_parts(self) -> List[str]:
        """获取用于 Everything 搜索的查询部分"""
        query_parts = []
        
        for pattern in self.rules:
            # 对于所有规则都使用 !path:
            if '*' in pattern or '?' in pattern:
                query_parts.append(f'!path:{pattern}')
            else:
                query_parts.append(f'!path:"{pattern}"')
        
        return query_parts 