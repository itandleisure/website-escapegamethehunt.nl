"""Bouwt de hele site uit src/data + src/content + de templates in tools/.

Gebruik:  python tools/build.py

Schrijft elke pagina als docs/<pad>/index.html, plus sitemap.xml, robots.txt en 404.html in docs/.
GitHub Pages publiceert alleen de map docs/; src/ en tools/ blijven zo buiten de website.
Alleen standaard-Python nodig. Doorverwijspagina's (meta refresh) worden niet aangeraakt.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pages  # noqa: E402
import pages_more as pm  # noqa: E402
import pages_intent  # noqa: E402
from render import LOCS, OUT, ROOT, SITE  # noqa: E402

NEWS_PER_PAGE = 9
OVERVIEW = {'path': '/escape-game-the-hunt-locaties/', 'title': 'Escape Game The Hunt Locaties - Escape Game The Hunt',
            'description': 'Ontdek alle locaties waar je Escape Game The Hunt kunt spelen. Van stad tot stad: hier vind je jouw volgende escape avontuur op straatniveau!',
            'h1': 'Alle locaties van The Hunt', 'og_image': '', 'robots': '', 'body': ''}
SPECIAL = {'/escape-game-the-hunt-prijzen/': pm.prices, '/contact/': pm.contact, '/veelgestelde-vragen/': pm.faq_page,
           '/escape-game-the-hunt-fotopagina/': pm.photos, '/over-ons/': pm.about}


def write(path, html, written):
    fp = os.path.join(OUT, path.strip('/'), 'index.html') if path != '/' else os.path.join(OUT, 'index.html')
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    with open(fp, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(html)
    written.append((path, 'noindex' in html[:3000]))


def op_maat(p):
    body = p['body'].replace('<h3>Trailer Escape Game The Hunt</h3>', '')
    trailer = ('<section class="section tight paper"><div class="wrap split"><div class="stack"><span class="label">Trailer</span>'
               '<h2>Zo ziet een Hunt eruit</h2><p>Bekijk de trailer en stel je voor dat de opdrachten over jullie eigen groep gaan.</p></div>'
               + pages.VIDEO + '</div></section>')
    return pm.simple(p, body_html=body, extra_after=trailer)


def main():
    written = []
    write('/', pages.home(), written)
    for loc in LOCS:
        write(loc['url'], pages.location(loc), written)
    write(OVERVIEW['path'], pm.locations_overview(OVERVIEW), written)
    write('/bedankt/', pm.thanks(), written)
    with open(os.path.join(OUT, '404.html'), 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(pm.not_found())  # GitHub Pages toont deze pagina bij elk onbekend adres
    write('/teamuitje-bedrijfsuitje/', pages_intent.teamuitje(), written)
    write('/vrijgezellenfeest/', pages_intent.vrijgezellenfeest(), written)

    all_p = pm.all_pages()
    for p in all_p:
        if p['kind'] == 'post':
            html = pm.post(p, all_p)
        elif p['path'] == '/op-maat-gemaakt/':
            html = op_maat(p)
        elif p['path'].startswith('/werken-bij/'):
            photo = '<img src="/assets/uploads/2026/09/the-hunt-spelleider-uitleg-1600.jpg" alt="Een spelleider geeft uitleg aan de groep" width="1600" height="1173">'
            html = pm.simple(p, form=False, body_html=photo + p['body'], extra_after=pm.apply_block())
        else:
            html = SPECIAL.get(p['path'], pm.simple)(p)
        write(p['path'], html, written)

    posts = pm.posts_sorted(all_p)
    total = max(1, math.ceil(len(posts) / NEWS_PER_PAGE))
    for n in range(1, total + 1):
        write('/escape-game-the-hunt-nieuws/' + (f'page/{n}/' if n > 1 else ''),
              pm.news(n, total, posts[(n - 1) * NEWS_PER_PAGE:n * NEWS_PER_PAGE]), written)

    cats = sorted({c for p in posts for c in p['categories']} | set(os.listdir(os.path.join(OUT, 'category'))))
    for slug in cats:
        name = pm.LOC_BY_SLUG[slug]['name'] if slug in pm.LOC_BY_SLUG else slug.replace('-', ' ').title()
        write(f'/category/{slug}/', pm.category(slug, name, [p for p in posts if slug in p['categories']]), written)

    urls = sorted(p for p, noindex in written if not noindex and '/page/' not in p)
    with open(os.path.join(OUT, 'sitemap.xml'), 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        fh.write(''.join('  <url><loc>%s%s</loc></url>\n' % (SITE['url'], u) for u in urls))
        fh.write('</urlset>\n')
    with open(os.path.join(OUT, 'robots.txt'), 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n' % SITE['url'])
    print('%d pagina\'s gebouwd, %d in sitemap.xml, nieuws: %d pagina\'s' % (len(written), len(urls), total))


if __name__ == '__main__':
    main()
