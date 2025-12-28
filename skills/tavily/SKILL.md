---
name: tavily
description: 使用 Tavily API 进行互联网搜索。当需要获取实时新闻、技术资料或搜索特定的在线信息时使用该技能。
---

# Tavily 搜索技能

此技能允许 Alice 使用 Tavily API 获取高质量的搜索结果。

## 核心功能

- **智能搜索**: 针对 AI Agent 优化的搜索算法。
- **深度搜索**: 支持高级搜索深度，获取更详尽的信息。
- **新闻模式**: 专门用于查找最新的新闻报道。

## 使用方法

在终端运行以下命令：

```bash
# 基础搜索
python skills/tavily/tavily_search.py "搜索关键词"

# 深度搜索
python skills/tavily/tavily_search.py "搜索关键词" --depth advanced

# 搜索最近的新闻
python skills/tavily/tavily_search.py "热点事件" --topic news --days 3
```

## 依赖要求

1. 安装 Python 包: `pip install tavily-python`
2. 环境变量: 需要在 `.env` 中配置 `TAVILY_API_KEY`。

## 参数说明

- `query`: 搜索关键词（必填）。
- `--depth`: 搜索深度，可选 `basic`（默认）或 `advanced`。
- `--topic`: 搜索主题，可选 `general`（默认）或 `news`。
- `--days`: 搜索新闻的时间范围（天），默认 3。
- `--max-results`: 返回结果数量，默认 5。

## 技术细节

该脚本会将 Tavily 的 JSON 结果简化为易于阅读的 Markdown 格式，包含标题、链接和内容摘要。
