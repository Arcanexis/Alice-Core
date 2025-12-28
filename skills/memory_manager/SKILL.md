---
name: memory_manager
description: 专门用于管理 Alice 的记忆（短期与长期）。支持记录日常任务进度以及沉淀“经验教训”以实现自我进化。
---

# 记忆管理工具 (Memory Manager)

此技能提供了一个简化的接口，让 Alice 能够轻松地维护其短期记忆 (STM) 和长期记忆 (LTM)。

## 核心功能

- **短期记忆管理 (默认)**: 自动处理日期标题和时间戳。
- **长期记忆管理 (`--target ltm`)**: 特别支持向 LTM 的“经验教训”章节追加内容，用于记录错误反思。
- **自动化格式**: 确保记录符合 Markdown 规范。

## 使用方法

### 1. 记录日常进展 (STM)
```bash
python skills/memory_manager/memory_tool.py "**事件**: 完成了网页抓取 | **行动**: 使用 fetch 提取了目标页面的核心数据"
```

### 2. 记录经验教训 (LTM)
当你意识到自己犯了错或找到了更好的方法时，请务必记录：
```bash
python skills/memory_manager/memory_tool.py "之前尝试用 cat 修改大文件导致了超时，应优先使用 sed 或 python 脚本处理大文件。" --target ltm
```

## 推荐时机

- **STM**: 完成任务步骤、捕获用户偏好、重要时间节点。
- **LTM**: **意识到错误时**、被用户纠正时、发现更高效的解决方案时、沉淀长期有效的事实时。
