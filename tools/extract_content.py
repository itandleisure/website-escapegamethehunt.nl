"""Eenmalig: haal de inhoud uit de oude (WordPress/Flatsome) pagina's en zet die als schone data in src/content/.

Vereist BeautifulSoup (pip install beautifulsoup4). Het bouwscript zelf (tools/build.py) heeft dat niet nodig.
"""
import json
from html import escape as html_escape
import os
import re
import subprocess

from bs4 import BeautifulSoup, NavigableString, Tag

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# De oude pagina's worden overschreven door het nieuwe ontwerp; lees ze daarom uit de laatste commit van de 1-op-1-herbouw.
SOURCE_REF = 'claude/rebuild-site-f1vk4l'


def read_old(rel):
    return subprocess.run(['git', 'show', '%s:%s/index.html' % (SOURCE_REF, rel.replace(os.sep, '/'))], cwd=ROOT,
                          capture_output=True, check=True).stdout.decode('utf-8')


def old_dirs():
    out = subprocess.run(['git', 'ls-tree', '-r', '--name-only', SOURCE_REF], cwd=ROOT, capture_output=True, check=True)
    return sorted(os.path.dirname(f) for f in out.stdout.decode('utf-8').splitlines() if f.endswith('/index.html'))
OUT = os.path.join(ROOT, 'src', 'content')

KEEP_INLINE = {'strong', 'b', 'em', 'i', 'a', 'br'}
SKIP_CLASSES = {'accordion', 'accordion-item', 'box-blog-post', 'post-item', 'city-links'}
BLOCKS = {'h2', 'h3', 'h4', 'h5', 'p', 'ul', 'ol', 'blockquote'}
# Algemene blokken die op de nieuwe site als vaste onderdelen terugkomen (uitleg, prijs, FAQ, formulier, nieuws).
GENERIC = re.compile(r'^(kunnen jullie ontsnappen|durven jullie|hoe werkt$|hoe werkt (de )?gameapp|the hunt [\w\s-]+\?$|'
                     r'wat kost|veelgestelde vragen|boek |nieuws|meer inspiratie|hoe ziet|dit is om je een beeld)', re.I)


def clean_inline(node):
    """Inline-HTML met alleen strong/em/a/br; overige tags worden uitgepakt."""
    out = []
    for c in node.children:
        if isinstance(c, NavigableString):
            out.append(html_escape(str(c), quote=False))
        elif isinstance(c, Tag):
            inner = clean_inline(c)
            name = {'b': 'strong', 'i': 'em'}.get(c.name, c.name)
            if name == 'br':
                out.append('<br>')
            elif name == 'a' and c.get('href'):
                href = c['href']
                ext = href.startswith('http') and 'escapegamethehunt.nl' not in href
                out.append('<a href="%s"%s>%s</a>' % (href, ' rel="noopener" target="_blank"' if ext else '', inner))
            elif name in ('strong', 'em') and inner.strip():
                out.append('<%s>%s</%s>' % (name, inner, name))
            else:
                out.append(inner)
    return re.sub(r'\s+', ' ', ''.join(out))


def text(node):
    return re.sub(r'\s+', ' ', node.get_text(' ', strip=True)).strip()


def blocks(main):
    """Alle tekstblokken in documentvolgorde, zonder formulieren, accordeons en berichtlijsten."""
    skip = lambda el: el.find_parent(['form', 'nav', 'header', 'footer']) or el.find_parent(
        class_=lambda c: c in SKIP_CLASSES or (c or '').startswith(('happyforms', 'ez-toc')))
    for el in main.find_all(list(BLOCKS)):
        if skip(el) or el.find_parent(list(BLOCKS - {'blockquote'})):
            continue
        yield el


def sections(main, drop=None):
    """Blokken als schone HTML; algemene secties (zie GENERIC) vallen weg."""
    html, dropping = [], False
    for el in blocks(main):
        t = text(el)
        if not t:
            continue
        if el.name in ('h2', 'h3', 'h4', 'h5'):
            dropping = bool((drop or GENERIC).match(t))
            if not dropping:
                lvl = 'h2' if el.name == 'h2' else 'h3'
                head = re.sub(r'</?(strong|em)>', '', clean_inline(el)).strip()
                html.append('<%s>%s</%s>' % (lvl, head, lvl))
            continue
        if dropping:
            continue
        if el.name in ('ul', 'ol'):
            items = ''.join('<li>%s</li>' % clean_inline(li).strip() for li in el.find_all('li', recursive=False))
            html.append('<%s>%s</%s>' % (el.name, items, el.name))
        else:
            inner = clean_inline(el).strip()
            if inner and inner != '<br>':
                html.append('<p>%s</p>' % inner)
    return '\n'.join(html)


def faq(soup):
    items = []
    for it in soup.select('.accordion-item'):
        q, a = it.select_one('.accordion-title span'), it.select_one('.accordion-inner')
        if q and a:
            items.append([text(q), ''.join('<p>%s</p>' % clean_inline(p).strip() for p in a.find_all('p'))])
    h = soup.find(lambda t: t.name == 'h2' and 'Veelgestelde vragen' in t.get_text())
    if not items and h:
        for h3 in h.find_next_siblings('h3'):
            p = h3.find_next_sibling('p')
            items.append([text(h3), '<p>%s</p>' % clean_inline(p).strip()])
    return items


def meta(soup):
    m = lambda **kw: (soup.find('meta', attrs=kw) or {}).get('content', '')
    return {
        'title': text(soup.title),
        'description': m(name='description'),
        'og_image': m(property='og:image').replace('https://escapegamethehunt.nl', ''),
        'robots': m(name='robots'),
        'published': m(property='article:published_time'),
        'modified': m(property='article:modified_time'),
    }


def related_posts(soup):
    out, seen = [], set()
    for box in soup.select('.box-blog-post'):
        a = box.select_one('.post-title a') or box.select_one('a[href]')
        img = box.select_one('img')
        if a and a['href'] not in seen:
            seen.add(a['href'])
            out.append({'title': text(a), 'url': a['href'], 'image': img['src'] if img else ''})
    return out


def location(slug, page):
    soup = BeautifulSoup(read_old('escape-game-the-hunt-locaties/' + page), 'html.parser')
    main = soup.find('main')
    data = meta(soup)
    data.update({'h1': text(main.find('h1')), 'body': sections(main), 'faq': faq(main), 'posts': related_posts(main)})
    return data


# Voor blogs en losse pagina's: alleen formulier-, nieuws- en herhaalblokken weg; inhoudelijke secties blijven.
LIGHT = re.compile(r'^(kunnen jullie ontsnappen|durven jullie|boek |nieuws|contactformulier|meer inspiratie|inhoudsopgave)', re.I)
SKIP_DIRS = {'assets', 'src', 'tools', 'partials', 'category', 'escape-game-the-hunt-locaties', 'escape-game-the-hunt-nieuws', '.git', '.claude'}


def faq_groups(main):
    """Accordeons gegroepeerd onder hun titel (FAQ-pagina)."""
    groups = []
    for acc in main.select('.accordion'):
        t = acc.find_previous(class_='accordion_title')
        items = []
        for it in acc.select('.accordion-item'):
            q, a = it.select_one('.accordion-title span'), it.select_one('.accordion-inner')
            if q and a:
                items.append([text(q), ''.join('<p>%s</p>' % clean_inline(p).strip() for p in a.find_all('p'))])
        if items:
            groups.append([text(t) if t else 'Vragen', items])
    return groups


def generic(rel):
    raw = read_old(rel)
    if 'http-equiv="refresh"' in raw:
        return None
    soup = BeautifulSoup(raw, 'html.parser')
    main = soup.find('main')
    data = meta(soup)
    body_cls = ' '.join(soup.body.get('class', []))
    art = main.find(class_=re.compile(r'\bpost-\d+'))
    data.update({
        'path': '/' + rel.replace(os.sep, '/') + '/',
        'kind': 'post' if 'single-post' in body_cls else 'page',
        'categories': re.findall(r'category-([\w-]+)', ' '.join(art.get('class', [])) if art else ''),
        'h1': text(main.find('h1')) if main.find('h1') else '',
        'body': sections(main, LIGHT),
        'faq_groups': faq_groups(main),
        'images': [{'src': i['src'], 'alt': i.get('alt', '')} for i in main.find_all('img')
                   if i.get('src', '').startswith('/assets/uploads/') and not i.find_parent('form')],
    })
    return data


def main():
    locs = json.load(open(os.path.join(ROOT, 'src', 'data', 'locations.json'), encoding='utf-8'))
    os.makedirs(os.path.join(OUT, 'locaties'), exist_ok=True)
    for loc in locs:
        page = loc['url'].strip('/').split('/')[-1]
        data = location(loc['slug'], page)
        with open(os.path.join(OUT, 'locaties', loc['slug'] + '.json'), 'w', encoding='utf-8', newline='\n') as fh:
            json.dump(data, fh, ensure_ascii=False, indent=1)
        print(loc['slug'], len(data['body']), 'tekens,', len(data['faq']), 'vragen,', len(data['posts']), 'berichten')
    os.makedirs(os.path.join(OUT, 'pages'), exist_ok=True)
    n = 0
    for rel in old_dirs():
        if not rel or rel.split('/')[0] in SKIP_DIRS:
            continue
        data = generic(rel)
        if data:
            name = rel.replace('/', '__') + '.json'
            with open(os.path.join(OUT, 'pages', name), 'w', encoding='utf-8', newline='\n') as fh:
                json.dump(data, fh, ensure_ascii=False, indent=1)
            n += 1
    print(n, "overige pagina's")


if __name__ == '__main__':
    main()
