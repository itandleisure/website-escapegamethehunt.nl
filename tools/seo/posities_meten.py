"""Meet per stad op welke Google-positie escapegamethehunt.nl staat.

Gebruik:  python tools/seo/posities_meten.py

Zoekt voor alle 33 steden uit src/data/locations.json op vijf zoekwoorden
(escaperoom, escape room, bedrijfsuitje, teamuitje, vrijgezellenfeest + stad),
mobiel, vanaf het stadscentrum, top 30. Nodig: DATAFORSEO_LOGIN en
DATAFORSEO_PASSWORD als omgevingsvariabelen. Kost ongeveer $1 per meting.

Schrijft tools/seo/metingen/posities-JJJJ-MM-DD.csv en .html. Staat er al een
eerdere meting, dan toont de html per zoekwoord of we gestegen of gedaald zijn.
"""
import base64
import concurrent.futures as cf
import csv
import datetime
import glob
import html
import json
import os
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUTDIR = os.path.join(HERE, 'metingen')
DOMAIN = 'escapegamethehunt.nl'
KEYWORDS = ['escaperoom', 'escape room', 'bedrijfsuitje', 'teamuitje', 'vrijgezellenfeest']
API = 'https://api.dataforseo.com/v3/serp/google/organic/live/advanced'


def search(job):
    kw, loc, auth = job
    body = json.dumps([{'keyword': f"{kw} {loc['name'].lower()}", 'language_code': 'nl',
                        'location_coordinate': f"{loc['lat']:.5f},{loc['lng']:.5f},2000",
                        'device': 'mobile', 'os': 'android', 'depth': 30}]).encode()
    err = ''
    for _ in range(3):
        try:
            req = urllib.request.Request(API, data=body, headers={'Authorization': 'Basic ' + auth,
                                                                   'Content-Type': 'application/json'})
            r = json.load(urllib.request.urlopen(req, timeout=300))
            task = r['tasks'][0]
            items = ((task.get('result') or [{}])[0] or {}).get('items') or []
            organic = [i for i in items if i.get('type') == 'organic']
            ours = next((i for i in organic if DOMAIN in (i.get('domain') or '')), None)
            top3 = ', '.join(i.get('domain', '') for i in organic[:3])
            return kw, loc, (ours or {}).get('rank_group'), (ours or {}).get('url', ''), top3, r.get('cost') or 0
        except Exception as e:  # netwerkfout: nog een keer proberen
            err = str(e)
    return kw, loc, None, 'fout: ' + err, '', 0


def previous():
    files = sorted(glob.glob(os.path.join(OUTDIR, 'posities-*.csv')))
    if not files:
        return {}, ''
    with open(files[-1], encoding='utf-8-sig') as fh:
        rows = list(csv.DictReader(fh, delimiter=';'))
    return {(r['stad'], r['zoekwoord']): r['positie'] for r in rows}, os.path.basename(files[-1])[9:19]


def main():
    auth = base64.b64encode(f"{os.environ['DATAFORSEO_LOGIN']}:{os.environ['DATAFORSEO_PASSWORD']}".encode()).decode()
    with open(os.path.join(ROOT, 'src', 'data', 'locations.json'), encoding='utf-8') as fh:
        locs = json.load(fh)
    old, old_date = previous()
    jobs = [(kw, loc, auth) for loc in locs for kw in KEYWORDS]
    with cf.ThreadPoolExecutor(8) as ex:
        results = list(ex.map(search, jobs))

    today = datetime.date.today().isoformat()
    os.makedirs(OUTDIR, exist_ok=True)
    rows = [{'stad': loc['name'], 'zoekwoord': f"{kw} {loc['name'].lower()}", 'positie': pos or '',
             'vorige': old.get((loc['name'], f"{kw} {loc['name'].lower()}"), ''), 'onze_pagina': url, 'top3': top3}
            for kw, loc, pos, url, top3, _ in results]
    with open(os.path.join(OUTDIR, f'posities-{today}.csv'), 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), delimiter=';')
        w.writeheader()
        w.writerows(rows)

    def cell(pos, prev):
        if not pos:
            return '<td class="no">–</td>'
        cls = 'top' if int(pos) <= 3 else 'ok' if int(pos) <= 10 else 'low'
        arrow = ''
        if prev:
            d = int(prev) - int(pos)
            arrow = f' <small>{"▲" if d > 0 else "▼"}{abs(d)}</small>' if d else ''
        elif old_date:
            arrow = ' <small>nieuw</small>'
        return f'<td class="{cls}">{pos}{arrow}</td>'

    by = {(r['stad'], r['zoekwoord'].split(' ' + r['stad'].lower())[0]): r for r in rows}
    body = ''.join('<tr><th>%s</th>%s</tr>' % (html.escape(loc['name']), ''.join(
        cell(by[(loc['name'], kw)]['positie'], by[(loc['name'], kw)]['vorige']) for kw in KEYWORDS)) for loc in locs)
    found = sum(1 for r in rows if r['positie'])
    page = f'''<!doctype html><meta charset="utf-8"><title>Posities {today}</title>
<style>body{{font:15px system-ui;margin:24px;color:#222}}table{{border-collapse:collapse}}th,td{{padding:6px 12px;border-bottom:1px solid #ddd;text-align:center}}
th{{text-align:left}}.top{{background:#c8f0c8}}.ok{{background:#fff3b0}}.low{{background:#fde0c8}}.no{{color:#aaa}}small{{font-size:11px}}</style>
<h1>Posities escapegamethehunt.nl – {today}</h1>
<p>Mobiel, gezocht vanaf het centrum van elke stad, top 30. Gevonden in {found} van {len(rows)} zoekopdrachten.
{f"Pijltjes vergelijken met de meting van {old_date}." if old_date else "Dit is de eerste meting."}
Groen = top 3, geel = 4–10, oranje = 11–30, streepje = niet in top 30.</p>
<table><tr><th>Stad</th>{"".join(f"<th>{k}</th>" for k in KEYWORDS)}</tr>{body}</table>'''
    with open(os.path.join(OUTDIR, f'posities-{today}.html'), 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(page)
    print(f'klaar: {found}/{len(rows)} gevonden, kosten ${sum(r[5] for r in results):.2f}, zie tools/seo/metingen/')


if __name__ == '__main__':
    main()
