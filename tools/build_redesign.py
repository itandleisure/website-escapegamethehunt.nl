"""Tijdelijk: bouwt de pagina's die al naar het nieuwe ontwerp zijn omgezet (homepage en locaties)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render import LOCS, ROOT  # noqa: E402
import pages  # noqa: E402


def write(path, html):
    fp = os.path.join(ROOT, path.strip('/'), 'index.html')
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    with open(fp, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(html)


write('/', pages.home())
for loc in LOCS:
    write(loc['url'], pages.location(loc))
print('homepage +', len(LOCS), 'locatiepagina\'s gebouwd')
