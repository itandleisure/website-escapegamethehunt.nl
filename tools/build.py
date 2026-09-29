"""Inject the shared partials (header, footer, mobile menu) into every page.

Usage:  python tools/build.py

Edit partials/*.html, then run this script. Every index.html in the site gets
the content between its <!-- partial:NAME --> and <!-- /partial:NAME -->
markers replaced, and the menu item for the current page marked as active.
Only the Python standard library is needed.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = 'https://escapegamethehunt.nl'
SKIP_DIRS = {'.git', 'assets', 'partials', 'tools', 'node_modules'}
MARKER = re.compile(r'(<!-- partial:([\w-]+) -->)(.*?)(<!-- /partial:\2 -->)', re.S)
LI_LINK = re.compile(r'<li class="([^"]*)"([^>]*)><a ([^>]*?)href="([^"]*)"')


def load_partials():
    parts = {}
    for fn in os.listdir(os.path.join(ROOT, 'partials')):
        if fn.endswith('.html'):
            with open(os.path.join(ROOT, 'partials', fn), encoding='utf-8') as fh:
                parts[fn[:-5]] = fh.read().strip()
    return parts


def mark_active(html, page_path):
    """Add Flatsome's `active` class to the menu item(s) linking to this page."""
    def sub(m):
        classes, rest, a_attrs, href = m.groups()
        if href == page_path:
            classes += ' active'
            a_attrs = 'aria-current="page" ' + a_attrs
        return '<li class="%s"%s><a %shref="%s"' % (classes, rest, a_attrs, href)
    html = LI_LINK.sub(sub, html)
    # Parent items ("Locaties", "Over") become active when one of their children is.
    out, stack = [], []
    for token in re.split(r'(<li [^>]*>|</li>)', html):
        if token.startswith('<li '):
            stack.append(len(out))
        elif token == '</li>' and stack:
            start = stack.pop()
            if stack and ' active' in out[start]:
                parent = stack[-1]
                if ' active' not in out[parent]:
                    out[parent] = out[parent].replace('class="', 'class="active ', 1)
        out.append(token)
    return ''.join(out)


def build_page(fp, parts):
    rel = os.path.relpath(os.path.dirname(fp), ROOT).replace(os.sep, '/')
    page_path = '/' if rel == '.' else '/' + rel + '/'
    with open(fp, encoding='utf-8') as fh:
        html = fh.read()
    transparent = bool(re.search(r'<header id="header" class="[^"]*\btransparent\b', html))

    def sub(m):
        name = m.group(2)
        if name not in parts:
            return m.group(0)
        body = parts[name]
        if name in ('header', 'mobile-menu'):
            body = mark_active(body, page_path)
        if name == 'header' and transparent:
            body = body.replace('<div class="header-bg-container fill">',
                                '<div class="shade shade-top hide-for-sticky fill"></div>\n'
                                '<div class="header-bg-container fill">', 1)
        return '%s\n%s\n%s' % (m.group(1), body, m.group(4))

    new = MARKER.sub(sub, html)
    if new != html:
        with open(fp, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(new)
        return True
    return False


def write_sitemap(paths):
    """sitemap.xml + robots.txt, listing every page except archive pagination."""
    urls = sorted(p for p in paths if '/page/' not in p)
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    lines += ['  <url><loc>%s%s</loc></url>' % (SITE, p) for p in urls]
    lines.append('</urlset>')
    with open(os.path.join(ROOT, 'sitemap.xml'), 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(lines) + '\n')
    with open(os.path.join(ROOT, 'robots.txt'), 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n' % SITE)


def main():
    parts = load_partials()
    paths = []
    changed = 0
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith('.')]
        if 'index.html' in filenames:
            rel = os.path.relpath(dirpath, ROOT).replace(os.sep, '/')
            paths.append('/' if rel == '.' else '/' + rel + '/')
            changed += build_page(os.path.join(dirpath, 'index.html'), parts)
    write_sitemap(paths)
    print('%d pages, %d updated, sitemap.xml written' % (len(paths), changed))


if __name__ == '__main__':
    main()
