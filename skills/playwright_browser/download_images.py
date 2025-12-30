#!/usr/bin/env python3
"""
图片批量下载工具
自动提取网页中的所有图片并下载到指定目录
"""
import asyncio
import argparse
import os
import urllib.parse
from pathlib import Path
from playwright.async_api import async_playwright

OUTPUT_DIR = "alice_output"

async def download_images(url, output_dir="images", max_images=20):
    """提取并下载网页中的所有图片"""
    output_path = os.path.join(OUTPUT_DIR, output_dir)
    os.makedirs(output_path, exist_ok=True)
    
    downloaded = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        try:
            print(f"[*] 正在访问: {url}")
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            
            # 提取所有图片的 src
            images = await page.eval_on_selector_all('img', '''els => els.map(img => ({
                src: img.src,
                alt: img.alt || img.title || 'image'
            }))''')
            
            print(f"[+] 发现 {len(images)} 张图片")
            
            # 下载图片
            for i, img in enumerate(images[:max_images], 1):
                try:
                    src = img['src']
                    if not src or src.startswith('data:'):
                        continue
                    
                    # 获取图片内容
                    response = await context.request.get(src)
                    if response.status == 200:
                        # 生成文件名
                        ext = os.path.splitext(src)[1] or '.png'
                        # 从 alt 生成文件名，清理非法字符
                        safe_name = ''.join(c for c in img['alt'] if c.isalnum() or c in (' ', '-', '_')).strip()
                        if not safe_name:
                            safe_name = f"image_{i}"
                        filename = f"{safe_name}{ext}"
                        filepath = os.path.join(output_path, filename)
                        
                        # 保存文件
                        with open(filepath, 'wb') as f:
                            f.write(await response.body())
                        
                        downloaded.append(filename)
                        print(f"  [{i}/{len(images)}] ✓ 下载: {filename}")
                    else:
                        print(f"  [{i}/{len(images)}] ✗ 失败: {src[:50]}...")
                
                except Exception as e:
                    print(f"  [{i}/{len(images)}] ✗ 错误: {str(e)[:50]}")
                    continue
            
        except Exception as e:
            print(f"[-] 失败: {e}")
        finally:
            await browser.close()
    
    print(f"\n[+] 成功下载 {len(downloaded)} 张图片到: {output_path}")
    return downloaded

def main():
    parser = argparse.ArgumentParser(description="网页图片批量下载工具")
    parser.add_argument("url", help="目标网址")
    parser.add_argument("--output-dir", default="images", help="输出目录（相对于 alice_output/）")
    parser.add_argument("--max", type=int, default=20, help="最大下载数量")
    
    args = parser.parse_args()
    
    asyncio.run(download_images(args.url, args.output_dir, args.max))

if __name__ == "__main__":
    main()
