#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 charts/{zh,en}/*.svg 转成 charts/pdf/{zh,en}/*.pdf，供 LaTeX 引用。

为什么用 headless Chrome 而不是 cairosvg：
  cairosvg 拿不到 emoji 与 ✓ → ① ⚠ 等符号的字体，会静默渲染成豆腐块（▯）。
  2026-08 之前仓库里的图表 PDF 就是这么生成的，导致发布的 PDF 版全书
  有上百处豆腐块（网页版因为浏览器直接渲染 SVG，不受影响）。
  Chrome 有完整字体栈（含彩色 emoji），且输出仍是矢量。

用法：
  python3 tools/build_chart_pdfs.py            # 全量重建
  python3 tools/build_chart_pdfs.py zh/foo.svg # 只建一张
"""
import re, sys, os, glob, time, shutil, tempfile, subprocess

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def dims(svg_text):
    m = re.search(r'viewBox="\s*[\d.+-]+\s+[\d.+-]+\s+([\d.]+)\s+([\d.]+)', svg_text)
    if m:
        return float(m.group(1)), float(m.group(2))
    w = re.search(r'\bwidth="([\d.]+)', svg_text)
    h = re.search(r'\bheight="([\d.]+)', svg_text)
    return (float(w.group(1)), float(h.group(1))) if w and h else (1200.0, 800.0)


def convert(svg_path, pdf_path):
    svg = open(svg_path, encoding='utf-8').read()
    w, h = dims(svg)
    svg = re.sub(r'<\?xml[^>]*\?>', '', svg).strip()
    html = (f'<!doctype html><html><head><meta charset="utf-8"><style>'
            f'@page{{size:{w/96:.6f}in {h/96:.6f}in;margin:0}}'
            f'html,body{{margin:0;padding:0;background:transparent}}'
            f'svg{{display:block;width:{w}px;height:{h}px}}'
            f'</style></head><body>{svg}</body></html>')
    tmpd = tempfile.mkdtemp()
    try:
        hp = os.path.join(tmpd, 'p.html')
        open(hp, 'w', encoding='utf-8').write(html)
        out = os.path.join(tmpd, 'o.pdf')
        r = subprocess.run(
            [CHROME, '--headless=new', '--disable-gpu', '--no-sandbox',
             '--no-pdf-header-footer', '--run-all-compositor-stages-before-draw',
             '--virtual-time-budget=8000', f'--print-to-pdf={out}', f'file://{hp}'],
            capture_output=True, timeout=120)
        if not os.path.exists(out):
            return False, (r.stderr.decode()[-200:] or 'chrome produced no output')
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
        shutil.copy(out, pdf_path)
        return True, f'{w:.0f}x{h:.0f}'
    finally:
        shutil.rmtree(tmpd, ignore_errors=True)


# cairosvg 渲染不出来、会变成豆腐块的字符区段。新画图时应避免，
# 或确认只用本脚本（Chrome）出 PDF。
RISKY = [(0x2460, 0x24FF), (0x2190, 0x21FF), (0x2600, 0x27BF),
         (0x1F000, 0x1FAFF), (0x00A7, 0x00A7), (0xFF5C, 0xFF5C)]


def audit(svg_path):
    txt = ' '.join(re.findall(r'>([^<>]*)<', open(svg_path, encoding='utf-8').read()))
    return sorted({c for c in txt if any(a <= ord(c) <= b for a, b in RISKY)})


def main():
    os.chdir(ROOT)
    targets = sys.argv[1:]
    if targets:
        pairs = [(f'charts/{t}', f'charts/pdf/{t[:-4]}.pdf') for t in targets]
    else:
        pairs = [(p, f'charts/pdf/{lang}/{os.path.basename(p)[:-4]}.pdf')
                 for lang in ('zh', 'en') for p in sorted(glob.glob(f'charts/{lang}/*.svg'))]
    ok = fail = 0
    t0 = time.time()
    for svg, pdf in pairs:
        good, info = convert(svg, pdf)
        if good:
            ok += 1
        else:
            fail += 1
            print(f'  FAIL {svg}: {info}')
    print(f'{ok} 张成功，{fail} 张失败，用时 {time.time()-t0:.0f}s')
    if fail:
        sys.exit(1)


if __name__ == '__main__':
    main()
