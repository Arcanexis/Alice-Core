---
name: playwright_browser
description: 基于 Playwright 的高级网页浏览器技能。支持无头模式下的动态网页抓取、点击/输入模拟、自动化截图。
---

# Playwright 浏览器技能

此技能允许 Alice 在容器沙盒内操作一个真实的 Chromium 浏览器，用于处理复杂的网页任务。

## 核心功能
- **动态抓取**: 获取由 JavaScript 渲染后的完整页面 HTML。
- **自动化操作**: 模拟点击、表单输入、页面滚动。
- **网页截图**: 将当前页面保存为 PNG 图片，输出至 `alice_output/`。
- **等待机制**: 支持等待特定元素加载，应对异步加载页面。

## 使用方法
通过 `python skills/playwright_browser/browser_tool.py` 调用。

### 示例指令
```bash
# 抓取网页并截图
python skills/playwright_browser/browser_tool.py --url "https://www.google.com" --screenshot --output "google_search.png"

# 抓取动态内容
python skills/playwright_browser/browser_tool.py --url "https://news.ycombinator.com" --read
```

## 注意事项
- 浏览器在容器内以 **Headless (无头)** 模式运行。
- 截图将保存在 `alice_output/` 目录下。
- 请合理使用，遵守目标网站的 `robots.txt` 协议。
