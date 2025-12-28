import os
import sys
import argparse
import json
from tavily import TavilyClient
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def main():
    parser = argparse.ArgumentParser(description="Tavily Search Tool")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--depth", choices=["basic", "advanced"], default="basic", help="Search depth")
    parser.add_argument("--topic", choices=["general", "news"], default="general", help="Search topic")
    parser.add_argument("--days", type=int, default=3, help="News time range in days")
    parser.add_argument("--max-results", type=int, default=5, help="Maximum results")

    args = parser.parse_args()

    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        print("错误: 未在环境变量或 .env 文件中找到 TAVILY_API_KEY")
        sys.exit(1)

    try:
        client = TavilyClient(api_key=api_key)
        
        # 执行搜索
        response = client.search(
            query=args.query,
            search_depth=args.depth,
            topic=args.topic,
            days=args.days,
            max_results=args.max_results
        )

        # 格式化输出为 Markdown
        print(f"## 搜索查询: {args.query}\n")
        
        if response.get("answer"):
            print(f"> **AI 摘要**: {response['answer']}\n")

        results = response.get("results", [])
        if not results:
            print("未找到相关结果。")
            return

        for i, res in enumerate(results, 1):
            print(f"### {i}. {res.get('title')}")
            print(f"- **URL**: {res.get('url')}")
            if res.get('published_date'):
                print(f"- **日期**: {res.get('published_date')}")
            print(f"- **摘要**: {res.get('content')}\n")

    except Exception as e:
        print(f"搜索过程中发生错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
