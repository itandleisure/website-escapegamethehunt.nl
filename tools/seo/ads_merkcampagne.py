"""Google Ads-campagnes voor Escape Game The Hunt, als importbestand voor Google Ads Editor.

Gebruik:  python tools/seo/ads_merkcampagne.py
Maakt twee campagnes, elk met één advertentiegroep per stad, USP: live Hunters.
  - "The Hunt - Merk":   the hunt <stad>, escape game the hunt <stad>, ...
  - "The Hunt - Hunted": hunted <stad>, hunted spel, zelf hunted spelen (mensen die Hunted zelf willen spelen).
    "Hunted" is een tv-merk: het staat alleen in de zoekwoorden, niet in de advertentieteksten.
Schrijft tools/seo/ads/merkcampagne/merkcampagne-google-ads-editor.csv (Google Ads Editor: Account > Importeren >
Uit bestand) en een leesbaar overzicht merkcampagne-overzicht.xlsx. Alles staat op Gepauzeerd, eerst nakijken.
"""
import csv, json, os
from openpyxl import Workbook
from openpyxl.styles import Font

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(HERE, 'ads', 'merkcampagne')
SITE = 'https://escapegamethehunt.nl'
LOCS = json.load(open(os.path.join(ROOT, 'src', 'data', 'locations.json'), encoding='utf-8'))

NEG_BASIS = ['film', 'movie', 'netflix', 'trailer', 'imdb', 'cast', 'showdown', 'ps4', 'ps5', 'xbox', 'steam',
             'download', 'torrent', 'escape hunt', 'vacature', 'werken bij', 'serie', 'boek']
NEG_HUNTED = NEG_BASIS + ['kijken', 'npo', 'videoland', 'seizoen', 'aflevering', 'deelnemers', 'aanmelden',
                          'meedoen', 'uitzending', 'avrotros', 'kijkcijfers', 'vip']
# hogere plafonds waar concurrenten op onze naam bieden (cityadventures.nl op "the hunt amersfoort")
CPC_STAD = {'The Hunt - Merk': {'Amersfoort': '1.00', 'Zwolle': '0.90'}}


def kop_merk(stad):
    return [(f'The Hunt {stad}', '1'), ('Escape Game The Hunt', ''), ('Ontsnap aan Live Hunters', ''),
            ('Echte Hunters Jagen op Jullie', ''), (f'Outdoor Escape in {stad}', ''), ('90 Minuten Pure Spanning', ''),
            ('Live Hunters op Jullie Hielen', ''), ('Teamuitje met Live Hunters', ''), (f'Vrijgezellenfeest {stad}', ''),
            (f'Bedrijfsuitje {stad}', ''), ('Officiële Site The Hunt', ''), ('Vanaf 8 tot 200 Personen', ''),
            ('Puzzelen, Rennen, Ontsnappen', ''), ('Vrijblijvend Aanvragen', ''), ('De Stad Is Jullie Speelveld', '')]


def kop_hunted(stad):
    return [(f'Zelf Opgejaagd in {stad}', '1'), ('Ontsnap aan Live Hunters', ''), ('Echte Hunters Jagen op Jullie', ''),
            ('Speel Het Zelf: The Hunt', ''), ('Escape Game The Hunt', ''), ('90 Minuten Opgejaagd Worden', ''),
            ('Live Hunters op Jullie Hielen', ''), (f'Outdoor Escape in {stad}', ''), ('Teamuitje met Live Hunters', ''),
            (f'Vrijgezellenfeest {stad}', ''), ('Vanaf 8 tot 200 Personen', ''), ('Puzzelen, Rennen, Ontsnappen', ''),
            ('Blijf Uit Handen van Hunters', ''), ('Vrijblijvend Aanvragen', ''), ('De Stad Is Jullie Speelveld', '')]


def beschr(stad):
    return [f'Ontsnap 90 minuten aan echte live Hunters in {stad}. Puzzelen, rennen en samenwerken!',
            'Geen kamer maar de hele stad als speelveld. Live Hunters zitten jullie op de hielen.',
            'Ideaal als teamuitje, bedrijfsuitje of vrijgezellenfeest. Van 8 tot 200 personen.',
            'Dé escape game met live Hunters. Vraag vrijblijvend een datum aan voor jullie groep.']


def algemeen(koppen, h1):
    k = koppen('Nederland'); k[0] = (h1, '1')
    return [x if 'Nederland' not in x[0] else ({'Outdoor Escape in Nederland': 'Outdoor Escape Game',
            'Vrijgezellenfeest Nederland': 'Vrijgezellenfeest The Hunt', 'Bedrijfsuitje Nederland': 'Bedrijfsuitje The Hunt'
            }[x[0]], '') for x in k]


CAMPAGNES = [
    {'naam': 'The Hunt - Merk', 'budget': '5.00', 'cpc': '0.60', 'neg': NEG_BASIS, 'koppen': kop_merk,
     'algemeen': ('The Hunt - Algemeen', ['escape game the hunt', 'the hunt escape game', 'escapegamethehunt',
                  'the hunt escape room', 'the hunt city game', 'the hunt outdoor escape'], 'The Hunt Escape Game'),
     'stad_kw': lambda s: [f'the hunt {s}', f'escape game the hunt {s}', f'the hunt escape {s}', f'the hunt escaperoom {s}']},
    {'naam': 'The Hunt - Hunted', 'budget': '3.00', 'cpc': '0.80', 'neg': NEG_HUNTED, 'koppen': kop_hunted,
     'algemeen': ('Hunted spelen - Algemeen', ['hunted spel', 'hunted spelen', 'zelf hunted spelen', 'hunted spel spelen',
                  'hunted uitje', 'hunted teamuitje', 'hunted bedrijfsuitje', 'hunted vrijgezellenfeest'],
                  'Speel Het Zelf: The Hunt'),
     'stad_kw': lambda s: [f'hunted {s}', f'hunted spel {s}', f'hunted spelen {s}']},
]

COLS = ['Campaign', 'Campaign Type', 'Campaign Status', 'Budget', 'Budget type', 'Bid Strategy Type', 'Networks',
        'Languages', 'Location', 'Ad Group', 'Ad Group Status', 'Max CPC', 'Keyword', 'Criterion Type', 'Status',
        'Ad type', 'Final URL', 'Path 1', 'Path 2'] + \
       [c for i in range(1, 16) for c in (f'Headline {i}', f'Headline {i} position')] + \
       [f'Description {i}' for i in range(1, 5)]


def groepen(c):
    naam, kws, h1 = c['algemeen']
    g = [(naam, SITE + '/', 'The-Hunt', '', kws, None, algemeen(c['koppen'], h1), beschr('jouw stad'))]
    for l in LOCS:
        g.append((f"{'The Hunt' if c['naam'].endswith('Merk') else 'Hunted'} {l['name']}", SITE + l['url'], 'The-Hunt',
                  l['slug'][:15], c['stad_kw'](l['name'].lower()), l['name'], c['koppen'](l['name']), beschr(l['name'])))
    return g


def main():
    os.makedirs(OUT, exist_ok=True)
    rows, fouten, overzicht = [], [], []
    for c in CAMPAGNES:
        C = c['naam']
        rows.append({'Campaign': C, 'Campaign Type': 'Search', 'Campaign Status': 'Paused', 'Budget': c['budget'],
                     'Budget type': 'Daily', 'Bid Strategy Type': 'Manual CPC', 'Networks': 'Google search',
                     'Languages': 'nl', 'Location': 'Netherlands'})
        rows += [{'Campaign': C, 'Keyword': n, 'Criterion Type': 'Campaign negative phrase'} for n in c['neg']]
        for naam, url, p1, p2, kws, stad, H, D in groepen(c):
            cpc = CPC_STAD.get(C, {}).get(stad, c['cpc'])
            rows.append({'Campaign': C, 'Ad Group': naam, 'Ad Group Status': 'Enabled', 'Max CPC': cpc})
            rows += [{'Campaign': C, 'Ad Group': naam, 'Keyword': k, 'Criterion Type': mt, 'Status': 'Enabled'}
                     for k in kws for mt in ('Exact', 'Phrase')]
            ad = {'Campaign': C, 'Ad Group': naam, 'Ad type': 'Responsive search ad', 'Status': 'Enabled',
                  'Final URL': url, 'Path 1': p1, 'Path 2': p2}
            for i, (h, pos) in enumerate(H, 1):
                if len(h) > 30: fouten.append(f'{naam}: kop te lang ({len(h)}): {h}')
                if 'hunted' in h.lower(): fouten.append(f'{naam}: merknaam Hunted in advertentietekst: {h}')
                ad[f'Headline {i}'] = h
                if pos: ad[f'Headline {i} position'] = pos
            for i, d in enumerate(D, 1):
                if len(d) > 90: fouten.append(f'{naam}: beschrijving te lang ({len(d)}): {d}')
                ad[f'Description {i}'] = d
            rows.append(ad)
            overzicht.append([C, naam, cpc, url, ', '.join(kws)] + [h for h, _ in H] + D)
    if fouten:
        raise SystemExit('\n'.join(fouten))

    with open(os.path.join(OUT, 'merkcampagne-google-ads-editor.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=COLS); w.writeheader(); w.writerows(rows)

    wb = Workbook(); ws = wb.active; ws.title = 'Advertenties'
    ws.append(['Campagne', 'Advertentiegroep', 'Max. bod (€)', 'Landingspagina', 'Zoekwoorden (exact + woordgroep)'] +
              [f'Kop {i}' for i in range(1, 16)] + [f'Beschrijving {i}' for i in range(1, 5)])
    for r in overzicht: ws.append(r)
    ws2 = wb.create_sheet('Instellingen')
    ws2.append(['Campagne', 'Dagbudget (€)', 'Standaard max. bod (€)', 'Afwijkende biedingen', 'Uitsluitingen (woordgroep)'])
    for c in CAMPAGNES:
        ws2.append([c['naam'], c['budget'], c['cpc'], ', '.join(f'{s} € {v}' for s, v in CPC_STAD.get(c['naam'], {}).items()),
                    ', '.join(c['neg'])])
    ws2.append([]); ws2.append(['Alle campagnes: alleen Google Zoeken (geen partners/display), Nederlands, heel Nederland, '
                                'handmatige CPC, status Gepauzeerd.'])
    for s in (ws, ws2):
        for cel in s[1]: cel.font = Font(bold=True)
    wb.save(os.path.join(OUT, 'merkcampagne-overzicht.xlsx'))
    for c in CAMPAGNES:
        g = groepen(c)
        print(f"{c['naam']}: {len(g)} advertentiegroepen, {sum(len(x[4]) * 2 for x in g)} zoekwoorden")
    print('->', OUT)


if __name__ == '__main__':
    main()
