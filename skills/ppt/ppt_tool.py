#!/usr/bin/env python3
# skills/ppt/ppt_tool.py
import os
import html
import sys
from string import Template

def generate_presentation(title, slides, output_filename="presentation.html"):
    safe_title = html.escape(title)
    slides_html = ""
    for slide in slides:
        heading = html.escape(slide.get("heading", "")) if slide.get("heading") else ""
        content = html.escape(slide["content"]).replace("\n", "<br>")
        slide_html = f"""
        <div class="slide">
            {f'<h2>{heading}</h2>' if heading else ''}
            <div class="content">{content}</div>
        </div>
        """
        slides_html += slide_html

    html_template = Template("""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>$title</title>
    <style>
        body { margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; background: #f5f5f5; }
        .slide { width: 90vw; height: 90vh; margin: 2vh auto; padding: 30px; background: white; box-shadow: 0 4px 12px rgba(0,0,0,0.1); overflow-y: auto; page-break-after: always; }
        h1 { text-align: center; color: #333; margin-bottom: 40px; }
        h2 { color: #2c6fbb; margin-top: 0; }
        .content { line-height: 1.6; color: #444; }
        @media print { body { background: white; } .slide { box-shadow: none; margin: 0; height: auto; } }
    </style>
</head>
<body>
    <h1>$title</h1>
    $slides_html
</body>
</html>
    """)
    
    full_html = html_template.substitute(title=safe_title, slides_html=slides_html)
    output_path = os.path.join("alice_output", output_filename)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_html)
    return output_path

if __name__ == "__main__":
    # 生成示例幻灯片
    example_slides = [
        {"heading": "PPT 技能已就绪", "content": "✅ 纯 HTML 幻灯片\n✅ 单文件输出\n✅ 无需外部依赖\n✅ 支持打印与分享"},
        {"content": "使用方式：\n1. 调用 generate_presentation()\n2. 或直接运行此脚本生成示例\n\n—— Alice 数字助理"}
    ]
    path = generate_presentation("HTML PPT 演示", example_slides, "ppt_demo.html")
    print(f"✅ 幻灯片已生成: {path}")
