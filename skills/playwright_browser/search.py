#!/usr/bin/env python3
"""
Playwright 搜索工具
支持百度搜索，返回结构化结果
"""
import asyncio
import argparse
import json
from playwright.async_api import async_playwright

async def search_baidu(query, max_results=10):
    """使用百度搜索并返回结果"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()
        
        results = []
        try:
            print(f"[*] 正在搜索: {query}")
            await page.goto("https://www.baidu.com", timeout=15000)
            await page.fill('#kw', query)
            await page.click('#su')
            await page.wait_for_timeout(2000)
            
            # 提取搜索结果
            items = page.locator('#content_left > div')
            count = await items.count()
            
            for i in range(min(count, max_results)):
                try:
                    item = items.nth(i)
                    title_elem = item.locator('h3 a').first
                    desc_elem = item.locator('.c-abstract').first
                    
                    title = await title_elem.text_content()
                    url = await title_elem.get_attribute('href')
                    desc = await desc_elem.text_content() if await desc_elem.count() > 0 else ""
                    
                    results.append({
                        'title': title.strip() if title else "",
                        'url': url,
                        'description': desc.strip() if desc else ""
                    })
                except:
                    continue
            
            print(f"[+] 获取到 {len(results)} 条结果")
            
        except Exception as e:
            print(f"[-] 搜索失败: {e}")
        finally:
            await browser.close()
        
        return results

def main():
    parser = argparse.ArgumentParser(description="Playwright 搜索工具")
    parser.add_argument("query", help="搜索关键词")
    parser.add_argument("--max", type=int, default=10, help="最大结果数量")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    
    args = parser.parse_args()
    
    results = asyncio.run(search_baidu(args.query, args.max))
    
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for i, r in enumerate(results, 1):
            print(f"\n{i}. {r['title']}")
            print(f"   {r['url']}")
            if r['description']:
                print(f"   {r['description'][:100]}...")

if __name__ == "__main__":
    main()
