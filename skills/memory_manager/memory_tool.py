import sys
import os
import argparse
from datetime import datetime

def add_memory(content, target="stm", stm_path="memory/short_term_memory.md", ltm_path="memory/alice_memory.md"):
    """
    向记忆文件追加内容。支持短期记忆(stm)和长期记忆(ltm)。
    """
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")
    
    target_path = stm_path if target == "stm" else ltm_path
    
    # 确保目录存在
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    
    # 逻辑分发
    if target == "stm":
        _add_stm(target_path, content, date_str, time_str)
    else:
        _add_ltm(target_path, content, date_str)

def _add_stm(path, content, date_str, time_str):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write("# Alice 的短期记忆 (最近 7 天)\n")
            f.write("这是 Alice 的短期 memory 空间，以“时间-事件-行动”格式记录最近 7 天的有价值交互。\n\n")

    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    has_date_header = any(line.strip() == f"## {date_str}" for line in lines)
    
    with open(path, "a", encoding="utf-8") as f:
        if not has_date_header:
            f.write(f"\n## {date_str}\n")
        
        clean_content = content.strip()
        if not clean_content.startswith("- ["):
            f.write(f"- [{time_str}] {clean_content}\n")
        else:
            f.write(f"{clean_content}\n")
    print(f"已成功更新短期记忆 ({path})")

def _add_ltm(path, content, date_str):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write("# Alice 的长期记忆\n这是 Alice 的个人记忆空间，用于存储用户信息、偏好和重要事实。\n")

    with open(path, "r", encoding="utf-8") as f:
        full_text = f.read()

    # 尝试寻找“## 经验教训”章节
    lessons_header = "## 经验教训"
    entry = f"- [{date_str}] {content.strip()}\n"

    if lessons_header in full_text:
        # 在该章节下追加
        parts = full_text.split(lessons_header)
        # parts[0] 是标题前，parts[1] 是标题后
        new_content = parts[0] + lessons_header + "\n" + entry + parts[1].lstrip()
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
    else:
        # 如果没有该章节，追加到末尾
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"\n{lessons_header}\n{entry}")
    
    print(f"已成功更新长期记忆经验教训 ({path})")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Alice 记忆管理工具")
    parser.add_argument("content", help="要记录的记忆内容")
    parser.add_argument("--target", choices=["stm", "ltm"], default="stm", help="目标记忆库: stm (短期) 或 ltm (长期)")
    
    args = parser.parse_args()
    
    try:
        add_memory(args.content, target=args.target)
    except Exception as e:
        print(f"更新记忆失败: {e}")
        sys.exit(1)
