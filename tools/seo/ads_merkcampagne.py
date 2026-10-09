"""Merkcampagne Google Ads voor Escape Game The Hunt: één advertentiegroep per stad ("The Hunt <stad>").

Gebruik:  python tools/seo/ads_merkcampagne.py
Schrijft tools/seo/ads/merkcampagne/merkcampagne-google-ads-editor.csv (importeren in Google Ads Editor:
Account > Importeren > Uit bestand) en een leesbaar overzicht merkcampagne-overzicht.xlsx.
De campagne staat op Gepauzeerd, zodat hij eerst nagekeken kan worden. USP: live Hunters.
"""
import csv, json, os
from openpyxl import Workbook
from openpyxl.styles import Font

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(HERE, 'ads', 'merkcampagne')
SITE = 'https://escapegamethehunt.nl'
CAMPAGNE = 'The Hunt - Merk'
BUDGET = '5.00'      # euro per dag
MAX_CPC = '0.60'     # merkzoekwoorden zijn goedkoop; dit is een plafond
LOCS = json.load(open(os.path.join(ROOT, 'src', 'data', 'locations.json'), encoding='utf-8'))

NEGATIEF = ['film', 'movie', 'netflix', 'trailer', 'imdb', 'cast', 'showdown', 'ps4', 'ps5', 'xbox', 'steam',
            'download', 'torrent', 'escape hunt', 'vacature', 'werken bij', 'serie', 'boek']


def headlines(stad):
    return [
        (f'The Hunt {stad}', '1'),          # vast op positie 1
        ('Escape Game The Hunt', ''),
        ('Ontsnap aan Live Hunters', ''),
        ('Echte Hunters Jagen op Jullie', ''),
        (f'Outdoor Escape in {stad}', ''),
        ('90 Minuten Pure Spanning', ''),
        ('Live Hunters op Jullie Hielen', ''),
        ('Teamuitje met Live Hunters', ''),
        (f'Vrijgezellenfeest {stad}', ''),
        (f'Bedrijfsuitje {stad}', ''),
        ('Officiële Site The Hunt', ''),
        ('Vanaf 8 tot 200 Personen', ''),
        ('Puzzelen, Rennen, Ontsnappen', ''),
        ('Vrijblijvend Aanvragen', ''),
        ('De Stad Is Jullie Speelveld', ''),
    ]


def descriptions(stad):
    return [
        f'Ontsnap 90 minuten aan echte live Hunters in {stad}. Puzzelen, rennen en samenwerken!',
        'Geen kamer maar de hele stad als speelveld. Live Hunters zitten jullie op de hielen.',
        'Ideaal als teamuitje, bedrijfsuitje of vrijgezellenfeest. Van 8 tot 200 personen.',
        'Dé escape game met live Hunters. Vraag vrijblijvend een datum aan voor jullie groep.',
    ]


def groepen():
    g = [('The Hunt - Algemeen', SITE + '/', 'The-Hunt', '',
          ['escape game the hunt', 'the hunt escape game', 'escapegamethehunt', 'the hunt escape room',
           'the hunt city game', 'the hunt outdoor escape'], 'Nederland')]
    for l in LOCS:
        s = l['name'].lower()
        g.append((f"The Hunt {l['name']}", SITE + l['url'], 'The-Hunt', l['slug'][:15],
                  [f'the hunt {s}', f'escape game the hunt {s}', f'the hunt escape {s}', f'the hunt escaperoom {s}'],
                  l['name']))
    return g


COLS = ['Campaign', 'Campaign Type', 'Campaign Status', 'Budget', 'Budget type', 'Bid Strategy Type', 'Networks',
        'Languages', 'Location', 'Ad Group', 'Ad Group Status', 'Max CPC', 'Keyword', 'Criterion Type', 'Status',
        'Ad type', 'Final URL', 'Path 1', 'Path 2'] + \
       [c for i in range(1, 16) for c in (f'Headline {i}', f'Headline {i} position')] + \
       [f'Description {i}' for i in range(1, 5)]


def main():
    os.makedirs(OUT, exist_ok=True)
    rows = [{'Campaign': CAMPAGNE, 'Campaign Type': 'Search', 'Campaign Status': 'Paused', 'Budget': BUDGET,
             'Budget type': 'Daily', 'Bid Strategy Type': 'Manual CPC', 'Networks': 'Google search',
             'Languages': 'nl', 'Location': 'Netherlands'}]
    for n in NEGATIEF:
        rows.append({'Campaign': CAMPAGNE, 'Keyword': n, 'Criterion Type': 'Campaign negative phrase'})
    fouten = []
    for naam, url, p1, p2, kws, stad in groepen():
        rows.append({'Campaign': CAMPAGNE, 'Ad Group': naam, 'Ad Group Status': 'Enabled', 'Max CPC': MAX_CPC})
        for k in kws:
            for mt in ('Exact', 'Phrase'):
                rows.append({'Campaign': CAMPAGNE, 'Ad Group': naam, 'Keyword': k, 'Criterion Type': mt,
                             'Status': 'Enabled'})
        H = headlines('Nederland' if stad == 'Nederland' else stad)
        if stad == 'Nederland':
            H[0] = ('The Hunt Escape Game', '1'); H[4] = ('Outdoor Escape Game', '')
            H[8] = ('Vrijgezellenfeest The Hunt', ''); H[9] = ('Bedrijfsuitje The Hunt', '')
        D = descriptions('jouw stad' if stad == 'Nederland' else stad)
        ad = {'Campaign': CAMPAGNE, 'Ad Group': naam, 'Ad type': 'Responsive search ad', 'Status': 'Enabled',
              'Final URL': url, 'Path 1': p1, 'Path 2': p2}
        for i, (h, pos) in enumerate(H, 1):
            if len(h) > 30: fouten.append(f'{naam}: kop te lang ({len(h)}): {h}')
            ad[f'Headline {i}'] = h
            if pos: ad[f'Headline {i} position'] = pos
        for i, d in enumerate(D, 1):
            if len(d) > 90: fouten.append(f'{naam}: beschrijving te lang ({len(d)}): {d}')
            ad[f'Description {i}'] = d
        rows.append(ad)
    if fouten:
        raise SystemExit('\n'.join(fouten))

    with open(os.path.join(OUT, 'merkcampagne-google-ads-editor.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=COLS); w.writeheader(); w.writerows(rows)

    wb = Workbook(); ws = wb.active; ws.title = 'Advertenties'
    ws.append(['Advertentiegroep', 'Landingspagina', 'Zoekwoorden (exact + woordgroep)'] +
              [f'Kop {i}' for i in range(1, 16)] + [f'Beschrijving {i}' for i in range(1, 5)])
    for naam, url, p1, p2, kws, stad in groepen():
        ad = next(r for r in rows if r.get('Ad Group') == naam and r.get('Ad type'))
        ws.append([naam, url, ', '.join(kws)] + [ad.get(f'Headline {i}', '') for i in range(1, 16)] +
                  [ad.get(f'Description {i}', '') for i in range(1, 5)])
    ws2 = wb.create_sheet('Instellingen')
    for r in [('Campagne', CAMPAGNE), ('Type', 'Zoeken (alleen Google Zoeken, geen partners/display)'),
              ('Status', 'Gepauzeerd (eerst nakijken)'), ('Dagbudget', f'€ {BUDGET}'),
              ('Bieden', f'Handmatige CPC, max € {MAX_CPC}'), ('Taal / locatie', 'Nederlands / Nederland'),
              ('Uitsluitingen (woordgroep)', ', '.join(NEGATIEF))]:
        ws2.append(r)
    for s in (ws, ws2):
        for c in s[1]: c.font = Font(bold=True)
    wb.save(os.path.join(OUT, 'merkcampagne-overzicht.xlsx'))
    print(f'{len(groepen())} advertentiegroepen, {sum(len(g[4]) * 2 for g in groepen())} zoekwoorden -> {OUT}')


if __name__ == '__main__':
    main()
