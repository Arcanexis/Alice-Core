#!/usr/bin/env python3
"""
网页数据抓取工具
支持自定义CSS选择器提取数据
"""
import asyncio
import argparse
import json
from playwright.async_api import async_playwright

async def scrape_data(url, selectors, wait_for=None):
    """抓取网页数据"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()
        
        results = {}
        try:
            print(f"[*] 正在访问: {url}")
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            
            if wait_for:
                print(f"[*] 等待元素: {wait_for}")
                await page.wait_for_selector(wait_for, state="attached", timeout=10000)
            
            for name, config in selectors.items():
                try:
                    css = config['selector']
                    attr = config.get('attribute', 'text')
                    multiple = config.get('multiple', False)
                    
                    # 关键修复：使用 locator.first 处理 single 模式下的多元素情况
                    if multiple:
                        locator = page.locator(css)
                        items = await locator.all()
                        values = []
                        for item in items:
                            if attr == 'text':
                                val = await item.text_content()
                            else:
                                val = await item.get_attribute(attr)
                            if val:
                                values.append(val.strip())
                        results[name] = values
                    else:
                        # 单个元素时，取第一个匹配项
                        locator = page.locator(css).first
                        if attr == 'text':
                            val = await locator.text_content()
                        else:
                            val = await locator.get_attribute(attr)
                        results[name] = val.strip() if val else ""
                    
                    count = len(results[name]) if isinstance(results[name], list) else 1
                    print(f"[+] 提取 {name}: {count} 项")
                    
                except Exception as e:
                    print(f"[-] 提取 {name} 失败: {e}")
                    results[name] = None
            
        except Exception as e:
            print(f"[-] 抓取失败: {e}")
        finally:
            await browser.close()
        
        return results

def main():
    parser = argparse.ArgumentParser(description="网页数据抓取工具")
    parser.add_argument("url", help="目标网址")
    parser.add_argument("--selector", action="append", help="选择器配置，格式: name:css:attr[:multiple]")
    parser.add_argument("--json", action="store_true", help="输出JSON格式")
    parser.add_argument("--wait", help="等待的元素选择器")
    
    args = parser.parse_args()
    
    selectors = {}
    for s in args.selector or []:
        parts = s.split(':')
        name = parts[0]
        css = parts[1]
        attr = parts[2] if len(parts) > 2 else 'text'
        multiple = parts[3].lower() == 'true' if len(parts) > 3 else False
        
        selectors[name] = {
            'selector': css,
            'attribute': attr,
            'multiple': multiple
        }
    
    results = asyncio.run(scrape_data(args.url, selectors, args.wait))
    
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for key, val in results.items():
            print(f"\n{key}:")
            if isinstance(val, list):
                for v in val:
                    print(f"  - {v}")
            else:
                print(f"  {val}")

if __name__ == "__main__":
    main()
