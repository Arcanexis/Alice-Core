#!/usr/bin/env python3
"""
自动化交互工具
支持点击、输入、滚动、等待等操作
"""
import asyncio
import argparse
import json
from playwright.async_api import async_playwright

async def run_actions(url, actions):
    """执行自动化操作链"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()
        
        results = []
        try:
            print(f"[*] 正在访问: {url}")
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            
            for i, action in enumerate(actions):
                action_type = action.get('type')
                print(f"  [{i+1}] 执行: {action_type}")
                
                try:
                    if action_type == 'click':
                        await page.click(action['selector'], timeout=10000)
                        results.append(f"✓ 点击 {action['selector']}")
                        await page.wait_for_timeout(500)
                    
                    elif action_type == 'fill':
                        await page.fill(action['selector'], action['value'])
                        results.append(f"✓ 输入 {action['value']} 到 {action['selector']}")
                    
                    elif action_type == 'select':
                        await page.select_option(action['selector'], action['value'])
                        results.append(f"✓ 选择 {action['value']}")
                    
                    elif action_type == 'wait':
                        delay = action.get('delay', 1000)
                        await page.wait_for_timeout(delay)
                        results.append(f"✓ 等待 {delay}ms")
                    
                    elif action_type == 'scroll':
                        if 'selector' in action:
                            await page.locator(action['selector']).scroll_into_view_if_needed()
                            results.append(f"✓ 滚动到 {action['selector']}")
                        else:
                            pos = action.get('position', 'bottom')
                            if pos == 'bottom':
                                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                            elif pos == 'top':
                                await page.evaluate("window.scrollTo(0, 0)")
                            results.append(f"✓ 滚动到 {pos}")
                        await page.wait_for_timeout(500)
                    
                    elif action_type == 'screenshot':
                        filename = action.get('filename', f'action_{i}.png')
                        await page.screenshot(path=f"alice_output/{filename}")
                        results.append(f"✓ 截图保存: {filename}")
                    
                    elif action_type == 'evaluate':
                        result = await page.evaluate(action['script'])
                        results.append(f"✓ JS执行结果: {result}")
                    
                    elif action_type == 'wait_for':
                        await page.wait_for_selector(action['selector'], timeout=10000)
                        results.append(f"✓ 等待元素: {action['selector']}")
                    
                    else:
                        results.append(f"✗ 未知操作: {action_type}")
                
                except Exception as e:
                    error_msg = f"✗ 操作失败: {action_type} - {e}"
                    results.append(error_msg)
                    print(f"    {error_msg}")
            
            print(f"\n[+] 完成 {len(results)} 个操作")
            
        except Exception as e:
            print(f"[-] 执行失败: {e}")
        finally:
            await browser.close()
        
        return results

def main():
    parser = argparse.ArgumentParser(description="自动化交互工具")
    parser.add_argument("url", help="目标网址")
    parser.add_argument("--actions", help="JSON格式的操作链")
    parser.add_argument("--file", help="从文件读取操作配置")
    
    args = parser.parse_args()
    
    if args.file:
        with open(args.file, 'r', encoding='utf-8') as f:
            actions = json.load(f)
    else:
        actions = json.loads(args.actions)
    
    results = asyncio.run(run_actions(args.url, actions))
    
    print("\n=== 操作结果 ===")
    for r in results:
        print(r)

if __name__ == "__main__":
    main()
