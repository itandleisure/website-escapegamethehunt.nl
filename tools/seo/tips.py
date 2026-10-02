"""Tips per pagina om hoger te komen, op basis van Search Console en de positiemetingen.

Regels (elke tip krijgt een 'potentie' = geschat aantal extra klikken per 28 dagen):
1. Lage CTR voor de positie  -> titel en omschrijving aantrekkelijker maken.
2. Zoekwoord op positie 4-15 met veel vertoningen -> pagina sterker maken op dat zoekwoord
   (in titel/H2/intro, interne links vanuit stadsartikelen, backlink).
3. Twee of meer eigen pagina's op hetzelfde zoekwoord -> kannibalisatie: één pagina kiezen.
4. Veel vertoningen maar positie 20+ -> inhoud uitbreiden en backlinks.
5. Flinke daling in vertoningen t.o.v. de vorige periode -> controleren.
6. Stad zonder enkele positie in de top 30 (DataForSEO) -> lokale backlinks en vermeldingen.
"""
import json, os, re
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SITE = 'https://escapegamethehunt.nl'
# zoekwoorden waar geen tip voor komt: merknamen van anderen en losse algemene woorden
SKIP = re.compile(r'escape hunt|escapehunt|escape the city|clocked ?up|koepel|gevangenis|zwolderspel|sherlocked|prison', re.I)


def bruikbaar(q):
    return len(q.split()) >= 2 and not SKIP.search(q)
CTR = {1: .28, 2: .15, 3: .11, 4: .08, 5: .065, 6: .05, 7: .04, 8: .035, 9: .03, 10: .025}


def exp_ctr(pos):
    return CTR.get(max(1, round(pos)), .015 if pos <= 20 else .005)


def titles():
    out = {}
    for f in os.listdir(os.path.join(ROOT, 'src', 'content', 'pages')):
        d = json.load(open(os.path.join(ROOT, 'src', 'content', 'pages', f), encoding='utf-8'))
        out[d['path']] = d.get('title', '')
    for l in json.load(open(os.path.join(ROOT, 'src', 'data', 'locations.json'), encoding='utf-8')):
        f = os.path.join(ROOT, 'src', 'content', 'locaties', l['slug'] + '.json')
        if os.path.exists(f):
            out[l['url']] = json.load(open(f, encoding='utf-8')).get('title', '')
    return out


def short(u):
    return u.replace(SITE, '') or '/'


def live(path):
    """True als de pagina nu een echte pagina is (geen doorverwijzing of 404)."""
    p = path.split('?')[0].split('#')[0]
    f = os.path.join(ROOT, 'docs', p.strip('/'), 'index.html') if p != '/' else os.path.join(ROOT, 'docs', 'index.html')
    if not os.path.exists(f):
        return False
    return 'http-equiv="refresh"' not in open(f, encoding='utf-8', errors='ignore').read(3000)


def make(g, R=None):
    tips = []
    T = titles()
    pages_now = {r['keys'][0]: r for r in g.get('p_nu', [])}
    pages_prev = {r['keys'][0]: r for r in g.get('p_voor', [])}
    # 1. lage CTR
    for u, r in pages_now.items():
        if r['impressions'] >= 150 and r['position'] <= 12:
            exp = exp_ctr(r['position'])
            if r['clicks'] / r['impressions'] < exp * 0.6:
                extra = round(r['impressions'] * exp - r['clicks'])
                tips.append(dict(pagina=short(u), soort='Titel en omschrijving', potentie=extra,
                                 tip=f'Staat gemiddeld op {r["position"]:.1f} met {r["impressions"]} vertoningen, maar de CTR is {r["clicks"]/r["impressions"]*100:.1f}% '
                                     f'(normaal rond {exp*100:.0f}%). Maak de titel en omschrijving uitnodigender: noem de stad, "outdoor", "vanaf 8 personen" en de prijs. '
                                     f'Huidige titel: "{T.get(short(u), "?")}".'))
    # query x pagina
    qp = defaultdict(list)
    for r in g.get('qp_nu', []):
        qp[r['keys'][0]].append(r)
    # 2. zoekwoorden op 4-15
    for q, rows in qp.items():
        best = max(rows, key=lambda r: r['impressions'])
        if 4 <= best['position'] <= 15 and best['impressions'] >= 40 and bruikbaar(q):
            extra = round(best['impressions'] * (exp_ctr(3) - best['clicks'] / best['impressions']))
            u = short(best['keys'][1])
            tips.append(dict(pagina=u, soort='Bijna top 3', potentie=max(extra, 1),
                             tip=f'"{q}" staat op {best["position"]:.1f} ({best["impressions"]} vertoningen). Zet dit zoekwoord letterlijk in de titel of een H2, '
                                 f'noem het in de eerste alinea, link er vanuit de stadsartikelen naartoe met "{q}" als linktekst en zoek één lokale backlink.'))
    # 3. kannibalisatie
    for q, rows in qp.items():
        rows = [r for r in rows if r['impressions'] >= 20 and live(short(r['keys'][1]))]
        if len(rows) >= 2 and sum(r['impressions'] for r in rows) >= 80 and bruikbaar(q):
            rows.sort(key=lambda r: r['position'])
            main, other = short(rows[0]['keys'][1]), ', '.join(short(r['keys'][1]) for r in rows[1:3])
            tips.append(dict(pagina=main, soort='Concurrentie met eigen pagina', potentie=round(sum(r['impressions'] for r in rows) * 0.02),
                             tip=f'Voor "{q}" verschijnen meerdere eigen pagina\'s ({other}). Kies {main} als hoofdpagina: laat de andere pagina\'s ernaar linken '
                                 f'en haal "{q}" daar uit de titel.'))
    # 4. veel vertoningen, positie 20+
    for u, r in pages_now.items():
        if r['impressions'] >= 300 and r['position'] > 20:
            tips.append(dict(pagina=short(u), soort='Te laag voor de vraag', potentie=round(r['impressions'] * 0.02),
                             tip=f'{r["impressions"]} vertoningen op gemiddeld positie {r["position"]:.0f}. Google vindt de pagina relevant maar niet sterk genoeg: '
                                 f'breid de tekst uit met unieke informatie (start, speelveld, foto\'s, ervaringen van groepen) en zoek 2 à 3 backlinks.'))
    # 5. daling
    for u, r in pages_prev.items():
        n = pages_now.get(u)
        if r['impressions'] >= 200 and (not n or n['impressions'] < r['impressions'] * 0.6):
            now = n['impressions'] if n else 0
            tips.append(dict(pagina=short(u), soort='Daling', potentie=round((r['impressions'] - now) * 0.03),
                             tip=f'Vertoningen gedaald van {r["impressions"]} naar {now}. Controleer in Search Console of de pagina nog geïndexeerd is '
                                 f'en of er een doorverwijzing of een nieuwe pagina voor in de plaats is gekomen.'))
    # 6. steden zonder top 30
    if R:
        last = R[sorted(R)[-1]]
        locs = {l['name']: l['url'] for l in json.load(open(os.path.join(ROOT, 'src', 'data', 'locations.json'), encoding='utf-8'))}
        for stad in sorted({s for s, _ in last}):
            if not any(v for (s, _), v in last.items() if s == stad):
                tips.append(dict(pagina=locs.get(stad, stad), soort='Niet zichtbaar in ' + stad, potentie=3,
                                 tip=f'{stad} staat op geen enkel zoekwoord in de top 30. Zorg voor lokale vermeldingen: een Google Bedrijfsprofiel voor deze stad, '
                                     f'een vermelding op uitjessites in de regio en een link vanaf een lokale partner (horeca, VVV).'))
    # één tip per pagina+soort, hoogste potentie eerst
    seen, out = set(), []
    for t in sorted(tips, key=lambda t: -t['potentie']):
        k = (t['pagina'], t['soort'])
        if t['soort'] != 'Daling' and not live(t['pagina']):
            continue
        if k not in seen:
            seen.add(k); out.append(t)
    done_f = os.path.join(HERE, 'tips_gedaan.json')
    done = {(d['pagina'], d['soort']): d for d in json.load(open(done_f, encoding='utf-8'))} if os.path.exists(done_f) else {}
    for t in out:
        d = done.get((t['pagina'], t['soort']))
        t['gedaan'] = d
    return out
