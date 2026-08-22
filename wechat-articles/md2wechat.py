#!/usr/bin/env python3
"""Convert Markdown to WeChat-compatible HTML with inline styles."""

import re
import sys
from pathlib import Path


def md_to_wechat_html(md_text: str) -> str:
    """Convert markdown text to WeChat-compatible HTML with inline styles."""
    lines = md_text.split('\n')
    html_parts = []
    in_list = False
    in_table = False
    in_blockquote = False
    table_rows = []

    i = 0
    while i < len(lines):
        line = lines[i]

        # Image lines
        if line.strip().startswith('!['):
            img_match = re.match(r'!\[([^\]]*)\]\(([^)]+)\)', line.strip())
            if img_match:
                alt = img_match.group(1)
                url = img_match.group(2)
                if url.startswith('http'):
                    # WeChat URL - render as actual image
                    html_parts.append(
                        f'<p style="text-align:center;margin:20px 0;">'
                        f'<img src="{url}" alt="{alt}" style="max-width:100%;border-radius:4px;" /></p>'
                    )
                else:
                    # Local path - show placeholder
                    html_parts.append(
                        f'<p style="text-align:center;color:#888;font-size:14px;padding:20px 0;">'
                        f'[图片：{alt}]</p>'
                    )
            i += 1
            continue

        # Horizontal rule
        if line.strip() == '---':
            html_parts.append('<hr style="border:none;border-top:1px solid #eee;margin:30px 0;">')
            i += 1
            continue

        # Blockquote
        if line.strip().startswith('>'):
            if not in_blockquote:
                in_blockquote = True
                html_parts.append('<blockquote style="border-left:4px solid #1a73e8;margin:20px 0;padding:15px 20px;background:#f8f9fa;color:#333;font-size:15px;line-height:1.8;">')
            content = line.strip().lstrip('>').strip()
            if content:
                content = inline_format(content)
                html_parts.append(f'<p style="margin:8px 0;">{content}</p>')
            i += 1
            continue
        elif in_blockquote:
            in_blockquote = False
            html_parts.append('</blockquote>')

        # Close list if we're not in one anymore
        if in_list and not line.strip().startswith('- ') and not line.strip().startswith('* '):
            html_parts.append('</ul>')
            in_list = False

        # Table
        if '|' in line and line.strip().startswith('|'):
            if not in_table:
                in_table = True
                table_rows = []
            table_rows.append(line)
            i += 1
            continue
        elif in_table:
            in_table = False
            html_parts.append(render_table(table_rows))
            table_rows = []

        # Empty line
        if not line.strip():
            i += 1
            continue

        # H1
        if line.startswith('# '):
            content = inline_format(line[2:].strip())
            html_parts.append(
                f'<h1 style="font-size:24px;font-weight:bold;color:#1a1a1a;'
                f'margin:30px 0 15px;padding-bottom:10px;border-bottom:2px solid #1a73e8;">'
                f'{content}</h1>'
            )
            i += 1
            continue

        # H2
        if line.startswith('## '):
            content = inline_format(line[3:].strip())
            html_parts.append(
                f'<h2 style="font-size:20px;font-weight:bold;color:#1a1a1a;'
                f'margin:28px 0 12px;padding-left:12px;border-left:4px solid #1a73e8;">'
                f'{content}</h2>'
            )
            i += 1
            continue

        # H3
        if line.startswith('### '):
            content = inline_format(line[4:].strip())
            html_parts.append(
                f'<h3 style="font-size:17px;font-weight:bold;color:#333;'
                f'margin:22px 0 10px;">{content}</h3>'
            )
            i += 1
            continue

        # Unordered list
        if line.strip().startswith('- ') or line.strip().startswith('* '):
            item_text = line.strip()[2:].strip()
            # Definition-list pattern: **term**：content → render as <p>, not <li>
            # to avoid WeChat's empty-bullet-after-strong rendering bug
            if re.match(r'\*\*[^*]+\*\*[：:]', item_text):
                if in_list:
                    html_parts.append('</ul>')
                    in_list = False
                content = inline_format(item_text)
                html_parts.append(
                    f'<p style="font-size:15px;line-height:1.8;color:#333;'
                    f'margin:8px 0 8px 0;">{content}</p>'
                )
                i += 1
                continue
            content = inline_format(item_text)
            # If content contains <strong>, WeChat renders a phantom empty bullet before it.
            # Avoid <li> entirely and use a <p> with a manual bullet character.
            if '<strong' in content:
                if in_list:
                    html_parts.append('</ul>')
                    in_list = False
                html_parts.append(
                    f'<p style="font-size:15px;line-height:1.8;color:#333;'
                    f'margin:5px 0 5px 20px;">• {content}</p>'
                )
                i += 1
                continue
            if not in_list:
                in_list = True
                html_parts.append('<ul style="margin:10px 0;padding-left:20px;">')
            html_parts.append(
                f'<li style="font-size:15px;line-height:1.8;color:#333;margin:5px 0;">'
                f'{content}</li>'
            )
            i += 1
            continue

        # Regular paragraph
        content = inline_format(line.strip())
        html_parts.append(
            f'<p style="font-size:15px;line-height:2;color:#333;margin:12px 0;">'
            f'{content}</p>'
        )
        i += 1

    # Close any open tags
    if in_list:
        html_parts.append('</ul>')
    if in_blockquote:
        html_parts.append('</blockquote>')
    if in_table:
        html_parts.append(render_table(table_rows))

    body = '\n'.join(html_parts)
    # Wrap in a container with explicit Chinese font stack
    return (
        '<section style="font-family:-apple-system,BlinkMacSystemFont,'
        '\'PingFang SC\',\'Hiragino Sans GB\',\'Microsoft YaHei\','
        '\'Helvetica Neue\',Arial,sans-serif;'
        'font-size:15px;color:#333;line-height:2;">\n'
        f'{body}\n'
        '</section>'
    )


def inline_format(text: str) -> str:
    """Apply inline formatting: bold, italic, links, code."""
    # Bold: **text**
    text = re.sub(
        r'\*\*([^*]+)\*\*',
        r'<strong style="color:#1a1a1a;">\1</strong>',
        text
    )
    # Italic: *text* (but not inside bold)
    text = re.sub(
        r'(?<!\*)\*([^*]+)\*(?!\*)',
        r'<em>\1</em>',
        text
    )
    # Inline code: `text`
    text = re.sub(
        r'`([^`]+)`',
        r'<code style="background:#f0f0f0;padding:2px 6px;border-radius:3px;font-size:13px;color:#c7254e;">\1</code>',
        text
    )
    # Links: [text](url)
    text = re.sub(
        r'\[([^\]]+)\]\(([^)]+)\)',
        r'<a style="color:#1a73e8;text-decoration:none;" href="\2">\1</a>',
        text
    )
    return text


def render_table(rows: list) -> str:
    """Render a markdown table as WeChat-compatible HTML table."""
    if len(rows) < 2:
        return ''

    html = '<table style="width:100%;border-collapse:collapse;margin:15px 0;font-size:14px;">'

    for idx, row in enumerate(rows):
        cells = [c.strip() for c in row.strip().strip('|').split('|')]

        # Skip separator row (---|---|---)
        if all(re.match(r'^[-:]+$', c) for c in cells):
            continue

        if idx == 0:
            html += '<thead><tr>'
            for cell in cells:
                cell = inline_format(cell)
                html += (
                    f'<th style="border:1px solid #ddd;padding:8px 12px;'
                    f'background:#f5f5f5;font-weight:bold;text-align:left;">{cell}</th>'
                )
            html += '</tr></thead><tbody>'
        else:
            html += '<tr>'
            for cell in cells:
                cell = inline_format(cell)
                html += f'<td style="border:1px solid #ddd;padding:8px 12px;">{cell}</td>'
            html += '</tr>'

    html += '</tbody></table>'
    return html


def convert_file(input_path: str, output_path: str = None):
    """Convert a markdown file to WeChat HTML."""
    md_text = Path(input_path).read_text(encoding='utf-8')
    html = md_to_wechat_html(md_text)

    if output_path is None:
        output_path = str(Path(input_path).with_suffix('.html'))

    Path(output_path).write_text(html, encoding='utf-8')
    print(f"Converted: {input_path} -> {output_path}", file=sys.stderr)
    return html


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python md2wechat.py <input.md> [output.html]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    convert_file(input_file, output_file)
