#!/usr/bin/env python3
"""Build a PDF from a markdown sheet: pipe tables -> HTML tables, pandoc, headless Chromium.
Usage: python3 build.py <source.md> <out.pdf> <css>"""
import re, html, subprocess, sys, os

src_path, out_pdf, css = sys.argv[1], sys.argv[2], sys.argv[3]
src = open(src_path).read()

def cells(line):
    parts = re.split(r'(?<!\\)\|', line.strip().strip('|'))
    return [p.replace('\\|', '|').strip() for p in parts]

def inline(md):
    out, i = [], 0
    for m in re.finditer(r'``(.+?)``|`([^`]+)`|\*\*(.+?)\*\*|\*(.+?)\*', md):
        out.append(html.escape(md[i:m.start()]))
        if m.group(1) or m.group(2):
            out.append('<code>' + html.escape((m.group(1) or m.group(2)).strip()) + '</code>')
        elif m.group(3):
            out.append('<strong>' + html.escape(m.group(3)) + '</strong>')
        else:
            out.append('<em>' + html.escape(m.group(4)) + '</em>')
        i = m.end()
    out.append(html.escape(md[i:]))
    return ''.join(out)

def table_to_html(block):
    rows = [r for r in block.strip().split('\n') if not re.match(r'^\|\s*-', r)]
    first = cells(rows[0])
    is_answer = len(first) == 2 and first[0] == 'Kind'
    h = ['<table class="ans">' if is_answer else '<table>']
    body = rows
    if not is_answer:
        h.append('<thead><tr>' + ''.join(f'<th>{inline(c)}</th>' for c in first) + '</tr></thead>')
        body = rows[1:]
    h.append('<tbody>')
    for r in body:
        cs = cells(r)
        if is_answer:
            h.append(f'<tr><th>{inline(cs[0])}</th><td>{inline(cs[1])}</td></tr>')
        else:
            h.append('<tr>' + ''.join(f'<td>{inline(c)}</td>' for c in cs) + '</tr>')
    h += ['</tbody>', '</table>']
    return '\n'.join(h)

out = re.sub(r'(?:^\|.*\n?)+', lambda m: table_to_html(m.group(0)) + '\n', src, flags=re.M)
build_md = '_build.md'
open(build_md, 'w').write(out)
subprocess.run(['pandoc', build_md, '-f', 'markdown-markdown_in_html_blocks', '-s', '--css=' + css,
                '--embed-resources', '-o', '_build.html'], check=True)
subprocess.run(['/opt/pw-browsers/chromium-1194/chrome-linux/chrome', '--headless', '--no-sandbox',
                '--disable-gpu', '--no-pdf-header-footer',
                f'--print-to-pdf={os.path.abspath(out_pdf)}',
                'file://' + os.path.abspath('_build.html')],
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
os.remove(build_md); os.remove('_build.html')
pages = subprocess.run(['pdfinfo', out_pdf], capture_output=True, text=True).stdout
print(out_pdf, [l for l in pages.splitlines() if l.startswith('Pages')][0])
