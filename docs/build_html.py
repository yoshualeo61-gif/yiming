#!/usr/bin/env python3
"""Merge README.zh-CN.md + docs/0*.md into one self-contained docs/指南.html.
Needs `pip install markdown-it-py` (or `markdown`) only to rebuild; the HTML is shipped."""
import base64, re
from pathlib import Path
try:
    from markdown_it import MarkdownIt          # CommonMark, renders like GitHub
    _md = MarkdownIt('commonmark').enable('table')
    render = _md.render
except ImportError:
    import markdown
    render = lambda t: markdown.markdown(t, extensions=['tables', 'fenced_code'])

HERE = Path(__file__).resolve().parent
parts = [HERE.parent / 'README.zh-CN.md'] + sorted(HERE.glob('0*.md'))
anchor = {p.name: f'part{i}' for i, p in enumerate(parts)}


def fix(md, src):
    # links between docs -> in-page anchors
    def link(m):
        target = Path(m.group(2)).name
        return f'[{m.group(1)}](#{anchor[target]})' if target in anchor else m.group(0)
    md = re.sub(r'\[([^\]]+)\]\(([^)]+\.md)\)', link, md)
    # images -> embedded data URIs so the page is self-contained
    def img(m):
        p = (src.parent / m.group(2)).resolve()
        if p.suffix.lower() != '.png' or not p.exists():
            return ''
        return f'![{m.group(1)}](data:image/png;base64,{base64.b64encode(p.read_bytes()).decode()})'
    return re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', img, md)


body, toc = [], []
for i, p in enumerate(parts):
    md = fix(p.read_text(encoding='utf-8'), p)
    title = md.splitlines()[0].lstrip('# ').strip()
    toc.append(f'<li><a href="#part{i}">{title}</a></li>')
    html = render(md)
    body.append(f'<section id="part{i}">{html}</section>')

CSS = """
:root{--paper:#f5f6f3;--ink:#1f2328;--muted:#5d646c;--rule:#d5d9dd;--accent:#1d6b74;--code:#eceee9}
@media (prefers-color-scheme:dark){:root{--paper:#16191c;--ink:#e6e8ea;--muted:#9aa3ab;--rule:#2c3238;--accent:#6cc3cc;--code:#20252a}}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font-family:"Noto Serif SC","Source Han Serif SC","Songti SC","SimSun",serif;font-size:17px;line-height:1.9}
main{max-width:46em;margin:0 auto;padding:2.5rem 1.25rem 5rem}
nav{border-bottom:1px solid var(--rule);padding-bottom:1rem;margin-bottom:2rem;font-size:.9rem}
nav ol{margin:.3rem 0 0;padding-left:1.4rem}
h1{font-size:1.6rem;line-height:1.4;margin:2.5rem 0 1rem;padding-top:1rem;border-top:3px solid var(--accent)}
section:first-of-type h1{border-top:none;padding-top:0;margin-top:0}
h2{font-size:1.2rem;margin:2rem 0 .6rem}h3{font-size:1.02rem;margin:1.5rem 0 .4rem}
a{color:var(--accent)}
code{background:var(--code);padding:.1em .35em;font-size:.85em;border-radius:3px;font-family:"SF Mono",Menlo,Consolas,monospace}
pre{background:var(--code);padding:.8rem 1rem;overflow-x:auto;line-height:1.5;border-radius:4px}
pre code{padding:0;background:none}
table{border-collapse:collapse;width:100%;font-size:.88rem;line-height:1.6;display:block;overflow-x:auto}
th,td{border-bottom:1px solid var(--rule);padding:.35em .7em .35em 0;text-align:left;vertical-align:top}
th{font-weight:600}
img{max-width:100%;border:1px solid var(--rule);margin:.5rem 0}
blockquote{margin:1rem 0;padding:.2rem 1rem;border-left:3px solid var(--accent);color:var(--muted)}
hr{border:none;border-top:1px solid var(--rule);margin:2rem 0}
"""
page = (f'<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<title>异名 yiming 指南</title><style>{CSS}</style></head><body><main>'
        f'<nav><b>目录</b><ol>{"".join(toc)}</ol></nav>{"".join(body)}</main></body></html>')
(HERE / '指南.html').write_text(page, encoding='utf-8')
print('->', HERE / '指南.html')
