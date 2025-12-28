import os
import sys
import argparse
import fnmatch

def get_ignored_patterns():
    patterns = [".git", "__pycache__", ".venv*", "*.pyc", ".direnv"]
    if os.path.exists(".gitignore"):
        with open(".gitignore", "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.append(line)
    return patterns

def is_ignored(path, patterns):
    base = os.path.basename(path)
    for p in patterns:
        if fnmatch.fnmatch(base, p) or fnmatch.fnmatch(path, p):
            return True
    return False

def list_tree(startpath, max_depth=2):
    patterns = get_ignored_patterns()
    output = []
    startpath = startpath.rstrip(os.sep)
    num_sep = startpath.count(os.sep)
    
    for root, dirs, files in os.walk(startpath):
        # 过滤目录
        dirs[:] = [d for d in dirs if not is_ignored(os.path.join(root, d), patterns)]
        
        level = root.count(os.sep) - num_sep
        if level >= max_depth:
            continue
            
        indent = '  ' * level
        output.append(f"{indent}📁 {os.path.basename(root)}/")
        
        sub_indent = '  ' * (level + 1)
        for f in files:
            if not is_ignored(f, patterns):
                output.append(f"{sub_indent}📄 {f}")
                
    return "\n".join(output)

def search_files(query, startpath="."):
    patterns = get_ignored_patterns()
    results = []
    for root, dirs, files in os.walk(startpath):
        dirs[:] = [d for d in dirs if not is_ignored(os.path.join(root, d), patterns)]
        for f in files:
            if not is_ignored(f, patterns) and query.lower() in f.lower():
                results.append(os.path.join(root, f))
    return results

def safe_read(filepath, chunk_size=5000):
    if not os.path.exists(filepath):
        return f"错误: 文件 {filepath} 不存在。"
    
    # 路径越权检查
    abs_path = os.path.abspath(filepath)
    if not abs_path.startswith(os.getcwd()):
        return "安全性错误: 禁止访问项目外部文件。"

    file_size = os.path.getsize(filepath)
    if file_size > chunk_size:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(chunk_size)
            return (f"--- 文件较大 ({file_size} bytes)，仅显示前 {chunk_size} 字符 ---\n\n"
                    f"{content}\n\n"
                    f"--- 注意: 文件未读完。若需后续内容，请告知具体起始位置 ---")
    else:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()

def main():
    parser = argparse.ArgumentParser(description="Alice File Explorer")
    parser.add_argument("--tree", action="store_true", help="Display project tree")
    parser.add_argument("--depth", type=int, default=2, help="Tree depth")
    parser.add_argument("--search", type=str, help="Fuzzy search file name")
    parser.add_argument("--read", type=str, help="Safely read file content")
    
    args = parser.parse_args()

    if args.tree:
        print("### 项目结构树\n")
        print(list_tree(".", args.depth))
    elif args.search:
        print(f"### 搜索结果: '{args.search}'\n")
        matches = search_files(args.search)
        if matches:
            for m in matches:
                print(f"- {m}")
        else:
            print("未找到匹配文件。")
    elif args.read:
        print(f"### 文件内容: {args.read}\n")
        print(safe_read(args.read))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
