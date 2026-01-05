import os
import time
import re

class SnapshotManager:
    """
    Alice 的快照索引管理器
    负责扫描核心文件并生成内存快照摘要，以节省上下文空间。
    """
    def __init__(self, core_paths=None):
        self.core_paths = core_paths or [
            "prompts/alice.md",
            "skills"
        ]
        self.snapshots = {}
        self.skills = {} # 技能注册表
        self.skill_content_cache = {} # 技能文件内容缓存 {path: {"content": str, "mtime": float}}
        self.refresh()

    def _get_summary(self, path):
        """生成极简摘要：文件名、大小、最后修改时间、以及前两行内容"""
        if not os.path.exists(path):
            return None
        
        try:
            mtime = time.ctime(os.path.getmtime(path))
            size = os.path.getsize(path)
            
            summary = f"[文件: {path}, 大小: {size} bytes, 修改时间: {mtime}]"
            
            if os.path.isfile(path) and path.endswith(".md"):
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # 针对 SKILL.md 提取 description 并注册技能
                if path.endswith("SKILL.md"):
                    # 提取 YAML 块
                    yaml_match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
                    yaml_content = yaml_match.group(1) if yaml_match else ""
                    
                    # 解析 description 用于快照
                    desc_match = re.search(r'description:\s*(.*)', yaml_content) if yaml_content else re.search(r'description:\s*(.*)', content)
                    desc = desc_match.group(1).strip() if desc_match else "无描述"
                    
                    summary += f" 功能: {desc}"
                    
                    # 注册到技能表 (使用目录名作为 key)
                    skill_name = os.path.basename(os.path.dirname(path))
                    self.skills[skill_name] = {
                        "name": skill_name,
                        "description": desc,
                        "yaml": yaml_content,
                        "path": path
                    }
                else:
                    lines = content.splitlines()[:2]
                    first_content = " | ".join([l.strip() for l in lines if l.strip()])
                    if first_content:
                        summary += f" 预览: {first_content}..."
            elif os.path.isdir(path):
                items = os.listdir(path)
                summary += f" 包含项: {', '.join(items[:5])}{'...' if len(items) > 5 else ''}"
                
            return summary
        except Exception as e:
            return f"[路径: {path}, 状态: 无法读取 ({str(e)})]"

    def refresh(self):
        """刷新所有快照和技能注册表"""
        new_snapshots = {}
        self.skills = {} # 重置注册表
        for path in self.core_paths:
            if os.path.isfile(path):
                new_snapshots[path] = self._get_summary(path)
            elif os.path.isdir(path):
                # 记录目录快照，并深入一层记录关键技能
                new_snapshots[path] = self._get_summary(path)
                if os.path.exists(path):
                    for item in sorted(os.listdir(path)):
                        item_path = os.path.join(path, item)
                        if os.path.isdir(item_path):
                            skill_md = os.path.join(item_path, "SKILL.md")
                            if os.path.exists(skill_md):
                                new_snapshots[skill_md] = self._get_summary(skill_md)
        self.snapshots = new_snapshots

    def get_index_text(self):
        """生成注入上下文的索引文本"""
        if not self.snapshots:
            return "暂无快照数据。"

        lines = ["你目前拥有以下文件/目录的最新内存快照摘要："]
        for path, summary in self.snapshots.items():
            lines.append(f"- {summary}")
        lines.append("\n**提示**：如果你需要获取上述文件的详细内容（例如具体的任务进度、过往记忆或技能用法），请直接调用相应的工具（如 `cat` 或 `file_explorer`）读取全文。快照仅供快速定位参考。")
        return "\n".join(lines)

    def read_skill_file(self, relative_path):
        """
        带 mtime 验证的技能文件缓存读取

        因为 skills/ 目录是绑定挂载到容器的，宿主机和容器共享同一个物理文件。
        通过 mtime 检测可以确保缓存一致性：
        - 容器修改文件 → mtime 变化 → 下次读取时缓存失效
        - 宿主机修改文件 → mtime 变化 → 缓存失效

        性能提升：100-300ms (docker exec) → <10ms (缓存命中)
        """
        full_path = os.path.join("skills", relative_path)

        # 获取当前文件的修改时间
        try:
            current_mtime = os.path.getmtime(full_path)
        except FileNotFoundError:
            return None
        except Exception as e:
            return f"[读取文件失败: {str(e)}]"

        # 检查缓存是否有效
        cached = self.skill_content_cache.get(full_path)
        if cached and cached["mtime"] == current_mtime:
            # 缓存命中且 mtime 未变，直接返回
            return cached["content"]

        # 缓存失效或未命中，从磁盘重新加载
        try:
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # 更新缓存
            self.skill_content_cache[full_path] = {
                "content": content,
                "mtime": current_mtime
            }
            return content
        except Exception as e:
            return f"[读取文件失败: {str(e)}]"
