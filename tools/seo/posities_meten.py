"""Meet per stad op welke Google-positie escapegamethehunt.nl staat.

Gebruik:  python tools/seo/posities_meten.py

Zoekt voor alle 33 steden uit src/data/locations.json op vijf zoekwoorden
(escaperoom, escape room, bedrijfsuitje, teamuitje, vrijgezellenfeest + stad),
mobiel, vanaf het stadscentrum, top 30. Nodig: DATAFORSEO_LOGIN en
DATAFORSEO_PASSWORD als omgevingsvariabelen. Kost ongeveer $1 per meting.

Daarnaast de 35 zoekwoorden van de landingspagina's uit
tools/seo/zoekwoorden-landingspaginas.json (landelijk, seizoen, personeelsuitje en
bedrijfsfeest per stad, concurrent-alternatieven). Met stad: vanaf het stadscentrum,
zonder stad: Nederland.

Schrijft tools/seo/metingen/posities-JJJJ-MM-DD.csv en .html (steden) en
landingspaginas-JJJJ-MM-DD.csv. Staat er al een eerdere meting, dan toont de html per
zoekwoord of we gestegen of gedaald zijn.

Controle: is de meting leeg of ongeldig (veel fouten, geen echte sites in de top 3, of
ineens nergens meer gevonden), dan worden er geen bestanden geschreven en stopt het
script met MetingOngeldig. In GitHub Actions mislukt de workflow dan en krijg je mail.

Let op: Google zet op mobiel sinds november 2026 bij elk resultaat een doorverwijslink
(google.com/goto?url=...). DataForSEO geeft dan google.com als domein; het echte domein
staat in 'breadcrumb'. Zie echt_domein().
"""
import base64
import concurrent.futures as cf
import csv
import datetime
import glob
import html
import json
import os
import re
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUTDIR = os.path.join(HERE, 'metingen')
DOMAIN = 'escapegamethehunt.nl'
KEYWORDS = ['escaperoom', 'escape room', 'bedrijfsuitje', 'teamuitje', 'vrijgezellenfeest']
API = 'https://api.dataforseo.com/v3/serp/google/organic/live/advanced'
LANDING = os.path.join(HERE, 'zoekwoorden-landingspaginas.json')
NEDERLAND = 2528  # DataForSEO location_code voor landelijke zoekwoorden


class MetingOngeldig(Exception):
    pass


def echt_domein(item):
    """Domein van een resultaat. Bij een Google-doorverwijslink staat het echte domein in breadcrumb."""
    d = (item.get('domain') or '').lower()
    if d and not re.match(r'^(www\.)?google\.[a-z.]+$', d):
        return d
    m = re.match(r'\s*https?://([^/\s\u203a]+)', item.get('breadcrumb') or '')
    if m:
        return m.group(1).lower()
    return d


def echte_url(item):
    """Bij een Google-doorverwijslink de breadcrumb ('https://site.nl › pad') als adres gebruiken."""
    url = item.get('url') or ''
    if '/goto?' not in url:
        return url
    return re.sub(r'\s*\u203a\s*', '/', (item.get('breadcrumb') or '').strip()) or url


def search(job):
    """job = (zoekwoord, loc of None, auth). Geeft (job-zoekwoord, loc, positie, url, top3, kosten)."""
    kw, loc, auth = job
    task = {'keyword': kw, 'language_code': 'nl', 'device': 'mobile', 'os': 'android', 'depth': 30}
    if loc:
        task['location_coordinate'] = f"{loc['lat']:.5f},{loc['lng']:.5f},2000"
    else:
        task['location_code'] = NEDERLAND
    body = json.dumps([task]).encode()
    err = ''
    for _ in range(3):
        try:
            req = urllib.request.Request(API, data=body, headers={'Authorization': 'Basic ' + auth,
                                                                   'Content-Type': 'application/json'})
            r = json.load(urllib.request.urlopen(req, timeout=300))
            t = (r.get('tasks') or [{}])[0]
            if t.get('status_code') != 20000:  # bijv. 40200 = tegoed op, 40100 = inlog fout
                err = f"DataForSEO {t.get('status_code') or r.get('status_code')}: {t.get('status_message') or r.get('status_message')}"
                if str(t.get('status_code', ''))[:3] in ('401', '402', '403'):
                    break  # opnieuw proberen helpt niet
                continue
            items = ((t.get('result') or [{}])[0] or {}).get('items') or []
            organic = [i for i in items if i.get('type') == 'organic']
            ours = next((i for i in organic if DOMAIN in echt_domein(i)), None)
            top3 = ', '.join(echt_domein(i) for i in organic[:3])
            return kw, loc, (ours or {}).get('rank_group'), echte_url(ours) if ours else '', top3, r.get('cost') or 0
        except Exception as e:  # netwerkfout: nog een keer proberen
            err = str(e)
    return kw, loc, None, 'fout: ' + err, '', 0


def controleer(results, vorige_gevonden=None):
    """Gooit MetingOngeldig als de meting niet te vertrouwen is. Geeft anders een lijst waarschuwingen."""
    n = len(results)
    fouten = [r for r in results if str(r[3]).startswith('fout')]
    zonder_top3 = [r for r in results if not str(r[3]).startswith('fout') and not r[4].strip()]
    google = [r for r in results if r[4] and all(re.match(r'^(www\.)?google\.', d.strip()) for d in r[4].split(','))]
    gevonden = sum(1 for r in results if r[2])
    problemen = []
    if not n:
        problemen.append('er zijn geen zoekopdrachten uitgevoerd')
    if len(fouten) > n * 0.1:
        problemen.append(f'{len(fouten)} van {n} zoekopdrachten gaven een fout, bijvoorbeeld: {fouten[0][3][:200]}')
    if len(zonder_top3) > n * 0.2:
        problemen.append(f'{len(zonder_top3)} van {n} zoekopdrachten gaven geen enkel zoekresultaat')
    if len(google) > n * 0.2:
        problemen.append(f'bij {len(google)} van {n} zoekopdrachten bestaat de top 3 alleen uit google.com '
                         '(Google of DataForSEO heeft het formaat van de resultaten veranderd)')
    if vorige_gevonden and vorige_gevonden >= 5 and gevonden == 0:
        problemen.append(f'escapegamethehunt.nl is nergens gevonden, terwijl dat de vorige keer {vorige_gevonden} keer was')
    if problemen:
        raise MetingOngeldig('Positiemeting ongeldig, niets opgeslagen: ' + '; '.join(problemen))
    return [f'{len(fouten)} zoekopdrachten gaven een fout'] if fouten else []


def previous():
    files = sorted(glob.glob(os.path.join(OUTDIR, 'posities-*.csv')))
    if not files:
        return {}, ''
    with open(files[-1], encoding='utf-8-sig') as fh:
        rows = list(csv.DictReader(fh, delimiter=';'))
    return {(r['stad'], r['zoekwoord']): r['positie'] for r in rows}, os.path.basename(files[-1])[9:19]


def previous_landing():
    files = sorted(glob.glob(os.path.join(OUTDIR, 'landingspaginas-*.csv')))
    if not files:
        return {}
    with open(files[-1], encoding='utf-8-sig') as fh:
        return {r['zoekwoord']: r['positie'] for r in csv.DictReader(fh, delimiter=';')}


def main():
    auth = base64.b64encode(f"{os.environ['DATAFORSEO_LOGIN']}:{os.environ['DATAFORSEO_PASSWORD']}".encode()).decode()
    with open(os.path.join(ROOT, 'src', 'data', 'locations.json'), encoding='utf-8') as fh:
        locs = json.load(fh)
    old, old_date = previous()
    by_name = {l['name']: l for l in locs}
    with open(LANDING, encoding='utf-8') as fh:
        landing = json.load(fh)
    jobs = [(f"{kw} {loc['name'].lower()}", loc, auth) for loc in locs for kw in KEYWORDS]
    ljobs = [(x['zoekwoord'], by_name.get(x['stad']), auth) for x in landing]
    with cf.ThreadPoolExecutor(8) as ex:
        allres = list(ex.map(search, jobs + ljobs))
    results, lresults = allres[:len(jobs)], allres[len(jobs):]
    # zelfde vorm als vroeger: (kw zonder stad, loc, ...)
    results = [(kw[:-len(loc['name']) - 1], loc, *rest) for kw, loc, *rest in results]
    vorige_gevonden = sum(1 for v in old.values() if v) if old else None
    waarschuwingen = controleer(results + lresults, vorige_gevonden)

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

    lold = previous_landing()
    lrows = [{'groep': x['groep'], 'zoekwoord': x['zoekwoord'], 'stad': x['stad'], 'doelpagina': x['doelpagina'],
              'positie': pos or '', 'vorige': lold.get(x['zoekwoord'], ''), 'onze_pagina': url, 'top3': top3}
             for x, (_, _, pos, url, top3, _) in zip(landing, lresults)]
    with open(os.path.join(OUTDIR, f'landingspaginas-{today}.csv'), 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(lrows[0]), delimiter=';')
        w.writeheader()
        w.writerows(lrows)
    lfound = sum(1 for r in lrows if r['positie'])
    for x in waarschuwingen:
        print('Let op:', x)
    print(f'klaar: steden {found}/{len(rows)} gevonden, landingspagina\'s {lfound}/{len(lrows)} gevonden, '
          f'kosten ${sum(r[5] for r in allres):.2f}, zie tools/seo/metingen/')


if __name__ == '__main__':
    main()
