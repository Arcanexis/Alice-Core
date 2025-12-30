import argparse
import asyncio
import os
import sys
from playwright.async_api import async_playwright

# 确保输出目录存在
OUTPUT_DIR = "alice_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

async def run_browser(url, screenshot_path=None, read_html=False, wait_for=None):
    async with async_playwright() as p:
        # 在容器中通常需要 --no-sandbox
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()
        
        print(f"[*] 正在访问: {url}...")
        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
            
            if wait_for:
                print(f"[*] 等待元素: {wait_for}...")
                await page.wait_for_selector(wait_for, timeout=10000)
            
            if screenshot_path:
                full_path = os.path.join(OUTPUT_DIR, screenshot_path)
                await page.screenshot(path=full_path, full_page=True)
                print(f"[+] 截图已保存至: {full_path}")
            
            if read_html:
                content = await page.content()
                print("\n--- 页面 HTML 预览 (前1000字符) ---")
                print(content[:1000] + "...")
                print("--- 结束 ---")
                
            title = await page.title()
            print(f"[+] 页面标题: {title}")
            
        except Exception as e:
            print(f"[-] 发生错误: {str(e)}")
        finally:
            await browser.close()

def main():
    parser = argparse.ArgumentParser(description="Alice Playwright Browser Tool")
    parser.add_argument("--url", required=True, help="目标网址")
    parser.add_argument("--screenshot", action="store_true", help="是否截图")
    parser.add_argument("--output", default="web_screenshot.png", help="截图文件名")
    parser.add_argument("--read", action="store_true", help="是否读取 HTML 内容")
    parser.add_argument("--wait", help="等待特定的 CSS 选择器加载")

    args = parser.parse_args()

    asyncio.run(run_browser(
        url=args.url,
        screenshot_path=args.output if args.screenshot else None,
        read_html=args.read,
        wait_for=args.wait
    ))

if __name__ == "__main__":
    main()
