#!/usr/bin/env python3
"""
页面快照工具
支持截图和PDF导出
"""
import asyncio
import argparse
import os
from playwright.async_api import async_playwright

OUTPUT_DIR = "alice_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

async def take_snapshot(url, output_name, full_page=True, format="png"):
    """获取页面快照"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        try:
            print(f"[*] 正在访问: {url}")
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            
            if format == "png":
                path = os.path.join(OUTPUT_DIR, f"{output_name}.png")
                await page.screenshot(path=path, full_page=full_page)
                print(f"[+] 截图已保存: {path}")
            elif format == "pdf":
                path = os.path.join(OUTPUT_DIR, f"{output_name}.pdf")
                await page.pdf(path=path)
                print(f"[+] PDF已保存: {path}")
            
            # 同时生成一个缩略图
            thumb_path = os.path.join(OUTPUT_DIR, f"{output_name}_thumb.png")
            await page.screenshot(path=thumb_path, full_page=False)
            print(f"[+] 缩略图已保存: {thumb_path}")
            
        except Exception as e:
            print(f"[-] 失败: {e}")
        finally:
            await browser.close()

def main():
    parser = argparse.ArgumentParser(description="页面快照工具")
    parser.add_argument("url", help="目标网址")
    parser.add_argument("--output", default="snapshot", help="输出文件名（不含扩展名）")
    parser.add_argument("--format", choices=["png", "pdf"], default="png", help="输出格式")
    parser.add_argument("--full-page", action="store_true", help="截取完整页面")
    
    args = parser.parse_args()
    asyncio.run(take_snapshot(args.url, args.output, args.full_page, args.format))

if __name__ == "__main__":
    main()
