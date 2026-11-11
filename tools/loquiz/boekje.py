"""Fotoboekje per groep als PDF: alle teams van één Loquiz-game (en scope) in één boekje.

    python tools/loquiz/boekje.py --url https://results.loquiz.com/F3CJ8WVUSC:VANWIJNEN
    python tools/loquiz/boekje.py                         # game FK9SCMLMAJ, scope ADHOC
    python tools/loquiz/boekje.py --game ABC123 --scope ADHOC
    python tools/loquiz/boekje.py --stad "Den Haag"       # "... The Hunt in Den Haag" op de voorkant
    python tools/loquiz/boekje.py --demo                  # voorbeeldboekje zonder API

Opbouw:
  1. voorkant met onze eigen foto: "Missie volbracht · Bedankt voor het spelen van The Hunt"
  2. jullie Hunt in cijfers: gemiddeld en totaal gelopen, per team km, stappen, kcal en CO2-besparing, plus de video
  3. groepsfoto('s) van de spelleider
  4. alle foto's uit Loquiz, vier per pagina
  5. laat een review achter, met de andere spellen van Badass Games, spelleiders werven en de contactgegevens

Groepsfoto's van de spelleider: zet ze in tools/loquiz/groepsfotos/<game>-<scope>/ (jpg, png of webp). Zonder groepsfoto
slaat het boekje die pagina over. Uitvoer: tools/loquiz/uitvoer/<game>-<scope>/boekje-<game>-<scope>.html en .pdf. De PDF maakt het
script met Edge of Chrome (headless, zit standaard op Windows). Lukt dat niet, open dan de .html en kies Afdrukken >
Opslaan als PDF. Teksten, kengetallen en de spellen staan hieronder.
Zonder opdrachtregel: dubbelklik "Boekje maken.bat" (boekje_tool.py), dat opent een invulscherm in de browser.
"""
import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from resultaten import HIER, ROOT, STANDAARD_GAME, STANDAARD_SCOPE, e, ophalen  # noqa: E402

SITE = json.load(open(os.path.join(ROOT, 'src', 'data', 'site.json'), encoding='utf-8'))
DOCS = Path(ROOT) / 'docs'

VOORKANT_FOTO = '/assets/uploads/2026/09/the-hunt-juichende-groep-1600.jpg'  # onze eigen foto, pad binnen docs/
VIDEO = SITE['url'] + '/assets/video/the-hunt-trailer-720p.mp4'
VIDEO_POSTER = '/assets/uploads/2026/09/the-hunt-hunter-en-groepen-1600.jpg'

TEKST = {
    'label': 'Missie volbracht',
    'bedankt': 'Bedankt voor het spelen van The Hunt',
    'cijfers_kop': 'Jullie Hunt in cijfers',
    'cijfers': ('Alle teams zijn de stad door gerend, op de vlucht voor de Hunters. Zo ver zijn jullie gekomen, '
                'helemaal te voet: goed voor de conditie en goed voor de lucht in de stad.'),
    'video_kop': 'Beleef het nog een keer',
    'video': 'Bekijk de video van The Hunt.',
    'groepsfoto_kop': 'Groepsfoto',
    'fotos_kop': 'Jullie foto\'s',
    'review_kop': 'Laat een review achter',
    'review': ('Vonden jullie het een topdag? Laat dan een review achter, dat helpt ons enorm. '
               'En zin in meer? Wij hebben nog veel meer spellen.'),
    'review_url': 'https://escapegamethehunt.nl/',
    'spellen_kop': 'Meer spellen van Badass Games',
    'hunter_label': 'Gezocht: Hunters',
    'hunter_kop': 'Wil jullie zoon of dochter ook Hunter worden?',
    'hunter': ('Wij zoeken spelleiders in heel Nederland: groepen ontvangen, het spel uitleggen en daarna als Hunter '
               'de jacht openen. Een bijbaan vol actie, in de eigen stad.'),
    'hunter_url': 'https://escapegamethehunt.nl/werken-bij/werken-bij-escape-game-the-hunt-spelleider/',
    'hunter_link': 'escapegamethehunt.nl/werken-bij',
}

# Andere spellen op de laatste pagina. Vul de omschrijving en link in; laat 'link' leeg om hem weg te laten.
SPELLEN = [
    {'naam': 'Escape Box', 'tekst': 'Omschrijving volgt.', 'link': ''},
    {'naam': 'De 100', 'tekst': 'Omschrijving volgt.', 'link': ''},
    {'naam': 'Proef', 'tekst': 'Omschrijving volgt.', 'link': ''},
    {'naam': 'Speurneuzen', 'tekst': 'Omschrijving volgt.', 'link': ''},
]

KENGETALLEN = {  # indicatief
    'stappen_per_km': 1350,      # gemiddelde wandelaar
    'kcal_per_km': 55,           # per persoon, stevig wandeltempo
    'co2_auto_per_km': 0.18,     # kg CO2 per km voor een gemiddelde personenauto (één auto per team)
}

FOTO_EXT = ('.jpg', '.jpeg', '.png', '.webp')
RIJEN_P2 = 21       # teams in de tabel op pagina 2, de rest op een volgende pagina
RIJEN_VERVOLG = 40
RIJEN_GROTE_VIDEO = 9   # tot zoveel teams past de video groot op pagina 2


# ---------------------------------------------------------------- hulpjes

def uri(pad):
    return Path(pad).resolve().as_uri()


def site_uri(pad):
    return uri(DOCS / pad.lstrip('/'))


def nl(v, dec=0):
    s = f'{v:,.{dec}f}'
    return s.replace(',', 'X').replace('.', ',').replace('X', '.')


def stad_uit(titel):
    return re.sub(r'(?i)^\s*(escape\s*game\s*)?the\s*hunt\s*(nl\s*)?[-:|]*\s*', '', titel or '').strip()


def groepsfotos(map_):
    if not map_ or not os.path.isdir(map_):
        return []
    return [uri(p) for p in sorted(glob.glob(os.path.join(map_, '**', '*'), recursive=True))
            if p.lower().endswith(FOTO_EXT)]


def km(team):
    try:
        return float(team.get('odometer') or 0)
    except (TypeError, ValueError):
        return 0.0


# ---------------------------------------------------------------- HTML

def css():
    fonts = DOCS / 'assets' / 'fonts'
    return f'''
@font-face{{font-family:'Lato';font-weight:400;src:url({uri(fonts / 'S6uyw4BMUTPHjx4wXg.woff2')}) format('woff2')}}
@font-face{{font-family:'Lato';font-weight:700;src:url({uri(fonts / 'S6u9w4BMUTPHh6UVSwiPGQ.woff2')}) format('woff2')}}
@page{{size:A4;margin:0}}
:root{{--night:#141e29;--navy:#29394a;--signal:#f29222;--paper:#f3f5f7;--ink:#1c2834;--muted:#5a6878;--line:#dbe2e9;
  --on-dark:#e7edf3;--on-dark-muted:#a9b6c4;--mono:ui-monospace,'Cascadia Mono',Consolas,monospace}}
*{{box-sizing:border-box}}
html,body{{margin:0;background:#888}}
body{{font:400 11pt/1.5 'Lato',system-ui,sans-serif;color:var(--ink);-webkit-print-color-adjust:exact;print-color-adjust:exact}}
.blad{{width:210mm;height:297mm;margin:0 auto 10mm;background:#fff;position:relative;overflow:hidden;break-after:page}}
.blad:last-child{{break-after:auto}}
@media print{{html,body{{background:#fff}}.blad{{margin:0}}}}
.label{{font:700 8pt/1.2 var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--signal)}}
h1,h2,h3{{margin:0;line-height:1.08;letter-spacing:-.01em}}
h2{{font-size:24pt;margin:2.5mm 0 4mm}}
.binnen{{padding:16mm 16mm 0}}
.voet{{position:absolute;left:16mm;right:16mm;bottom:9mm;display:flex;justify-content:space-between;font:7.5pt var(--mono);
  color:var(--muted);letter-spacing:.06em;text-transform:uppercase;border-top:1px solid var(--line);padding-top:2.5mm}}
.donker{{background:var(--night);color:var(--on-dark)}}
.donker h2{{color:#fff}}
.donker .voet{{border-color:rgba(255,255,255,.15);color:var(--on-dark-muted)}}

/* voorkant */
.voor .beeld{{position:absolute;inset:0 0 auto 0;height:200mm;background:var(--navy) center/cover no-repeat}}
.voor .beeld::after{{content:'';position:absolute;inset:0;background:linear-gradient(180deg,rgba(20,30,41,.45) 0,rgba(20,30,41,0) 30%,rgba(20,30,41,.15) 65%,var(--night) 100%)}}
.voor .logo{{position:absolute;top:14mm;left:16mm;height:20mm;z-index:2}}
.voor .tekst{{position:absolute;left:16mm;right:16mm;top:190mm;z-index:2}}
.voor h1{{font-size:36pt;color:#fff;margin:3mm 0 5mm}}
.voor h1 em{{font-style:normal;color:var(--signal)}}
.voor .sub{{font:9pt var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--on-dark-muted)}}
.voor .streep{{position:absolute;right:0;bottom:0;width:70mm;height:4mm;background:var(--signal)}}

/* cijfers */
.intro{{color:var(--muted);max-width:165mm;font-size:10.5pt}}
.grootrij{{display:grid;grid-template-columns:repeat(4,1fr);gap:3mm;margin:5mm 0 4mm}}
.groot{{background:var(--paper);border-radius:2.5mm;padding:4mm}}
.groot b{{display:block;font-size:20pt;line-height:1.05;color:var(--navy)}}
.groot.oranje{{background:var(--navy)}}
.groot.oranje b{{color:var(--signal)}}
.groot.oranje span{{color:var(--on-dark-muted)}}
.groot span{{font-size:8pt;color:var(--muted);line-height:1.3;display:block;margin-top:1mm}}
table{{width:100%;border-collapse:collapse;font-size:8.5pt;line-height:1.35}}
th{{font:700 7pt var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--muted);text-align:right;padding:0 2mm 1.5mm;border-bottom:1.5px solid var(--navy)}}
td{{padding:.85mm 2mm;border-bottom:1px solid var(--line);text-align:right;font-variant-numeric:tabular-nums}}
th:first-child,td:first-child{{text-align:left;padding-left:0}}
td:first-child{{font-weight:700;max-width:70mm;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
tr.totaal td{{border-bottom:0;border-top:1.5px solid var(--navy);font-weight:700;color:var(--navy)}}
.kleine{{font-size:7pt;color:var(--muted);margin-top:2mm}}
.video{{position:absolute;left:16mm;right:16mm;bottom:20mm;display:grid;grid-template-columns:66mm 1fr;gap:6mm;align-items:center;
  text-decoration:none;color:inherit;background:var(--paper);border-radius:2.5mm;padding:3mm}}
.video .poster{{position:relative;height:37mm;border-radius:2mm;background:var(--navy) center/cover no-repeat}}
.video .poster i{{position:absolute;left:50%;top:50%;width:11mm;height:11mm;margin:-5.5mm 0 0 -5.5mm;border-radius:50%;background:var(--signal);
  display:grid;place-items:center;color:var(--night);font-style:normal;font-size:11pt;padding-left:.8mm}}
.video h3{{font-size:15pt;margin-bottom:1mm}}
.video p{{margin:0;color:var(--muted);font-size:10.5pt}}
.video u{{color:#a85600;text-decoration:none;font-weight:700;font-size:10.5pt}}
.video.groot{{grid-template-columns:1fr;gap:4mm;padding:4mm}}
.video.groot .poster{{height:78mm;border-radius:2.5mm}}
.video.groot .poster i{{width:20mm;height:20mm;margin:-10mm 0 0 -10mm;font-size:20pt;padding-left:1.5mm}}
.video.groot h3{{font-size:17pt}}
.video.groot p,.video.groot u{{font-size:11pt}}
.video.groot .tekst{{display:flex;align-items:baseline;gap:5mm;flex-wrap:wrap;padding:0 2mm 1mm}}

/* foto's */
.groepsfoto img{{width:100%;height:225mm;object-fit:cover;border-radius:2.5mm;display:block}}
.groepsfoto.twee img{{height:110mm;margin-bottom:5mm}}
.raster{{display:grid;grid-template-columns:1fr 1fr;gap:5mm}}
.raster figure{{margin:0}}
.raster img{{width:100%;height:104mm;object-fit:cover;border-radius:2mm;display:block;background:var(--paper)}}
.raster figcaption{{font:7.5pt var(--mono);letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin-top:1.5mm;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}

/* review + spellen */
.review p{{color:var(--on-dark-muted);font-size:11.5pt;max-width:165mm}}
.knop{{display:inline-block;margin-top:6mm;background:var(--signal);color:var(--night);font-weight:700;padding:3.5mm 8mm;border-radius:20mm;text-decoration:none;font-size:12pt}}
.spellen{{margin-top:9mm}}
.hunter{{margin-top:6mm;display:grid;grid-template-columns:1fr auto;gap:6mm;align-items:center;background:var(--signal);
  color:var(--night);border-radius:2.5mm;padding:5mm 6mm;text-decoration:none}}
.hunter .label{{color:var(--night);opacity:.75}}
.hunter b{{display:block;font-size:13.5pt;line-height:1.2;margin:1mm 0 1.5mm}}
.hunter span{{font-size:9.5pt;line-height:1.4;display:block}}
.hunter u{{text-decoration:none;font-weight:700;font-size:10pt;white-space:nowrap;border:2px solid var(--night);border-radius:20mm;padding:2.5mm 4.5mm}}
.spellen h3{{color:#fff;font-size:14pt;margin-bottom:4mm}}
.kaarten{{display:grid;grid-template-columns:1fr 1fr;gap:4mm}}
.kaart{{border:1px solid rgba(255,255,255,.15);border-radius:2.5mm;padding:5mm;border-top:3px solid var(--signal);text-decoration:none;color:inherit;display:block}}
.kaart b{{display:block;color:#fff;font-size:13pt;margin-bottom:1mm}}
.kaart span{{font-size:9.5pt;color:var(--on-dark-muted)}}
.contact{{position:absolute;left:16mm;right:16mm;bottom:20mm;display:flex;justify-content:space-between;align-items:flex-end}}
.contact img{{height:15mm}}
.contact div{{text-align:right;font-size:10pt;line-height:1.6}}
.contact a{{color:#fff;text-decoration:none}}
'''


def voet(onder, nr, donker=False):
    return f'<div class="voet"><span>{e(onder)}</span><span>{nr:02d}</span></div>'


def boekje(game, teams, per_team, fotos_groep, stad):
    logo = site_uri(SITE['logo'])
    titel_game = game.get('title') or game.get('name') or ''
    onder = 'The Hunt' + (f' · {stad}' if stad else '')
    k = KENGETALLEN
    bladen, nr = [], 1

    # 1. voorkant
    bladen.append(f'''<section class="blad donker voor">
  <div class="beeld" style="background-image:url('{e(site_uri(VOORKANT_FOTO))}')"></div>
  <img class="logo" src="{e(logo)}" alt="The Hunt">
  <div class="tekst">
    <div class="label">{e(TEKST["label"])}</div>
    <h1>{e(TEKST["bedankt"])}{f' in <em>{e(stad)}</em>' if stad else ''}</h1>
  </div>
  <div class="streep"></div>
</section>''')

    # 2. cijfers per groep en per team, met de video
    rijen = []
    for t in teams:
        d = km(t)
        rijen.append((t.get('name') or 'Team', d, d * k['stappen_per_km'], d * k['kcal_per_km'], d * k['co2_auto_per_km']))
    rijen.sort(key=lambda r: r[1], reverse=True)  # wie het verst liep bovenaan
    gelopen = [r for r in rijen if r[1] > 0]
    tot_km = sum(r[1] for r in rijen)
    gem_km = tot_km / len(gelopen) if gelopen else 0
    tot_co2 = sum(r[4] for r in rijen)
    groot = f'''<div class="grootrij">
      <div class="groot"><b>{nl(gem_km, 1)} km</b><span>gemiddeld gelopen per team</span></div>
      <div class="groot"><b>{nl(gem_km * k["stappen_per_km"])}</b><span>stappen per persoon, gemiddeld</span></div>
      <div class="groot"><b>{nl(tot_km, 1)} km</b><span>samen gelopen door {len(teams)} teams</span></div>
      <div class="groot oranje"><b>{nl(tot_co2, 1)} kg</b><span>CO₂ bespaard ten opzichte van de auto</span></div>
    </div>'''

    def tabel(deel, met_totaal):
        trs = ''.join(f'<tr><td>{e(n)}</td><td>{nl(d, 1)}</td><td>{nl(s)}</td><td>{nl(c)}</td><td>{nl(co, 2)}</td></tr>'
                      for n, d, s, c, co in deel)
        if met_totaal:
            trs += (f'<tr class="totaal"><td>Samen</td><td>{nl(tot_km, 1)}</td><td></td><td></td>'
                    f'<td>{nl(tot_co2, 1)}</td></tr>')
        return ('<table><thead><tr><th>Team</th><th>km</th><th>stappen p.p.</th><th>kcal p.p.</th><th>kg CO₂ bespaard</th></tr>'
                f'</thead><tbody>{trs}</tbody></table>')

    eerste, rest = rijen[:RIJEN_P2], rijen[RIJEN_P2:]
    nr += 1
    bladen.append(f'''<section class="blad"><div class="binnen">
    <div class="label">{e(TEKST["label"])}</div>
    <h2>{e(TEKST["cijfers_kop"])}</h2>
    <p class="intro">{e(TEKST["cijfers"])}</p>
    {groot}
    {tabel(eerste, not rest)}
    <p class="kleine">Indicatief: {nl(k["stappen_per_km"])} stappen en {k["kcal_per_km"]} kcal per km per persoon, {nl(k["co2_auto_per_km"], 2)} kg CO₂ per autokilometer, één auto per team.</p>
  </div>
  <a class="video{' groot' if len(rijen) <= RIJEN_GROTE_VIDEO else ''}" href="{e(VIDEO)}">
    <div class="poster" style="background-image:url('{e(site_uri(VIDEO_POSTER))}')"><i>▶</i></div>
    <div class="tekst"><h3>{e(TEKST["video_kop"])}</h3><p>{e(TEKST["video"])}</p><u>Bekijk de video →</u></div>
  </a>
  {voet(onder, nr)}
</section>''')
    for i in range(0, len(rest), RIJEN_VERVOLG):
        deel = rest[i:i + RIJEN_VERVOLG]
        nr += 1
        bladen.append(f'''<section class="blad"><div class="binnen">
    <div class="label">{e(TEKST["cijfers_kop"])} (vervolg)</div><div style="height:6mm"></div>
    {tabel(deel, i + RIJEN_VERVOLG >= len(rest))}
  </div>{voet(onder, nr)}</section>''')

    # 3. groepsfoto('s)
    for i in range(0, len(fotos_groep), 2):
        deel = fotos_groep[i:i + 2]
        nr += 1
        imgs = ''.join(f'<img src="{e(f)}" alt="Groepsfoto">' for f in deel)
        bladen.append(f'''<section class="blad"><div class="binnen groepsfoto{" twee" if len(deel) == 2 else ""}">
    <div class="label">{e(TEKST["label"])}</div><h2>{e(TEKST["groepsfoto_kop"])}</h2>
    {imgs}
  </div>{voet(onder, nr)}</section>''')

    # 4. Loquiz-foto's, vier per pagina, met de teamnaam
    alle = []
    for t in teams:
        for m in per_team.get(str(t.get('id')), []):
            if not m['video'] and not m['audio']:
                alle.append((t.get('name') or '', m))
    for i in range(0, len(alle), 4):
        nr += 1
        figs = ''.join(f'<figure><img src="{e(m["url"])}" alt="Foto van {e(n)}"><figcaption>{e(n)}</figcaption></figure>'
                       for n, m in alle[i:i + 4])
        kop = (f'<div class="label">{e(TEKST["label"])}</div><h2>{e(TEKST["fotos_kop"])}</h2>' if i == 0
               else f'<div class="label">{e(TEKST["fotos_kop"])}</div><div style="height:5mm"></div>')
        bladen.append(f'''<section class="blad"><div class="binnen">{kop}
    <div class="raster">{figs}</div>
  </div>{voet(onder, nr)}</section>''')

    # 5. review + spellen + contact
    nr += 1
    kaarten = ''.join(
        (f'<a class="kaart" href="{e(s["link"])}">' if s.get('link') else '<div class="kaart">')
        + f'<b>{e(s["naam"])}</b><span>{e(s["tekst"])}</span>' + ('</a>' if s.get('link') else '</div>')
        for s in SPELLEN)
    bladen.append(f'''<section class="blad donker review"><div class="binnen">
    <div class="label">{e(TEKST["label"])}</div>
    <h2>{e(TEKST["review_kop"])}</h2>
    <p>{e(TEKST["review"])}</p>
    <a class="knop" href="{e(TEKST["review_url"])}">Laat een review achter</a>
    <div class="spellen"><h3>{e(TEKST["spellen_kop"])}</h3><div class="kaarten">{kaarten}</div></div>
    <a class="hunter" href="{e(TEKST["hunter_url"])}">
      <div><div class="label">{e(TEKST["hunter_label"])}</div><b>{e(TEKST["hunter_kop"])}</b><span>{e(TEKST["hunter"])}</span></div>
      <u>{e(TEKST["hunter_link"])} →</u>
    </a>
  </div>
  <div class="contact">
    <img src="{e(logo)}" alt="The Hunt">
    <div><a href="{e(SITE["url"])}">{e(SITE["url"].replace("https://", ""))}</a><br>
      <a href="mailto:{e(SITE["email"])}">{e(SITE["email"])}</a><br>
      <a href="tel:{e(SITE["phone"])}">{e(SITE["phone_display"])}</a></div>
  </div>
  {voet(onder, nr)}
</section>''')

    return f'''<!doctype html>
<html lang="nl"><head><meta charset="utf-8">
<title>{e(onder)} · {e(titel_game)}</title>
<style>{css()}</style></head>
<body>
{chr(10).join(bladen)}
</body></html>
'''


# ---------------------------------------------------------------- PDF

def browser(opgegeven=None):
    kandidaten = [opgegeven or os.environ.get('BOEKJE_BROWSER')]
    for basis in (os.environ.get('PROGRAMFILES(X86)'), os.environ.get('PROGRAMFILES'), os.environ.get('LOCALAPPDATA')):
        if basis:
            kandidaten += [os.path.join(basis, 'Microsoft', 'Edge', 'Application', 'msedge.exe'),
                           os.path.join(basis, 'Google', 'Chrome', 'Application', 'chrome.exe')]
    kandidaten += [shutil.which(n) for n in ('msedge', 'chrome', 'google-chrome', 'chromium', 'chromium-browser')]
    kandidaten += ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
                   '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge']
    return next((k for k in kandidaten if k and os.path.exists(k)), None)


def naar_pdf(exe, html_pad, pdf_pad):
    with tempfile.TemporaryDirectory() as profiel:
        cmd = [exe, '--headless=new', '--disable-gpu', '--no-sandbox', '--no-first-run', '--allow-file-access-from-files',
               '--no-pdf-header-footer', '--print-to-pdf-no-header', '--virtual-time-budget=30000',
               f'--print-to-pdf={pdf_pad}', uri(html_pad)]
        if os.name == 'nt':  # los profiel, zodat een geopende Edge/Chrome niet in de weg zit
            cmd.insert(1, f'--user-data-dir={profiel}')
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
        except (subprocess.TimeoutExpired, OSError):
            return False
    return os.path.exists(pdf_pad) and os.path.getsize(pdf_pad) > 1000


# ---------------------------------------------------------------- demo

def demo_media(per_team):
    """Vervangt de demo-plaatjes door foto's van de site, zodat het voorbeeld zonder internet werkt."""
    fotos = sorted(glob.glob(str(DOCS / 'assets' / 'uploads' / '2026' / '09' / 'the-hunt-*-1600.jpg')))
    i = 0
    for lijst in per_team.values():
        for m in lijst:
            if fotos:
                m['url'] = m['duim'] = uri(fotos[i % len(fotos)])
                i += 1


# ---------------------------------------------------------------- hoofdprogramma

def lees_url(url):
    """Haalt game-ID en scope uit een spelleider-URL, bijv. https://results.loquiz.com/F3CJ8WVUSC:VANWIJNEN."""
    url = urllib.parse.unquote(url.strip()).split('?')[0].split('#')[0]
    deel = url.split('://')[-1].strip('/').split('/')[-1]
    m = re.fullmatch(r'([A-Za-z0-9]{6,})(?::(.+))?', deel)
    if not m:
        raise ValueError(f'Geen game-ID gevonden in "{url}". Verwacht iets als https://results.loquiz.com/ABC123XYZ0:scope')
    return m.group(1).upper(), (m.group(2) or '')


def mapnaam(game_id, scope):
    return game_id + ('-' + re.sub(r'[^A-Za-z0-9]+', '-', scope).strip('-') if scope else '')


def maak(game_id, scope, stad='', groepsfotomap=None, uit=None, exe=None, pdf=True, demo=False, log=print):
    """Haalt alles op en schrijft het boekje. Geeft de paden en tellingen terug. Ook gebruikt door boekje_tool.py."""
    game, teams, per_team, _, _ = ophalen(game_id, scope, demo)
    if demo:
        demo_media(per_team)
    sleutel = 'demo' if demo else mapnaam(game_id, scope)
    fotomap = groepsfotomap or os.path.join(HIER, 'groepsfotos', sleutel)
    os.makedirs(fotomap, exist_ok=True)
    groep = groepsfotos(fotomap)
    uit = uit or os.path.join(HIER, 'uitvoer', sleutel)
    os.makedirs(uit, exist_ok=True)

    html_pad = os.path.join(uit, f'boekje-{sleutel}.html')
    with open(html_pad, 'w', encoding='utf-8') as fh:
        fh.write(boekje(game, teams, per_team, groep, (stad or '').strip()))
    n_fotos = sum(1 for v in per_team.values() for m in v if not m['video'] and not m['audio'])
    uitkomst = {'titel': game.get('title') or game.get('name') or game_id, 'teams': len(teams), 'fotos': n_fotos,
                'groepsfotos': len(groep), 'html': html_pad, 'pdf': None, 'fotomap': fotomap}
    log(f'{len(teams)} teams, {n_fotos} foto\'s uit Loquiz, {len(groep)} groepsfoto(\'s)')
    if not groep:
        log(f'Geen groepsfoto: zet die in {fotomap} en draai opnieuw.')
    if pdf:
        exe = exe or browser()
        if not exe:
            log('Geen Edge of Chrome gevonden: open de HTML en kies Afdrukken > Opslaan als PDF.')
        elif naar_pdf(exe, html_pad, html_pad[:-5] + '.pdf'):
            uitkomst['pdf'] = html_pad[:-5] + '.pdf'
            log(f'PDF: {uitkomst["pdf"]}')
        else:
            log('PDF maken mislukt: open de HTML en kies Afdrukken > Opslaan als PDF.')
    log(f'HTML: {html_pad}')
    return uitkomst


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--url', help='spelleider-URL, bijv. https://results.loquiz.com/F3CJ8WVUSC:VANWIJNEN')
    ap.add_argument('--game', default=STANDAARD_GAME)
    ap.add_argument('--scope', default=STANDAARD_SCOPE)
    ap.add_argument('--stad', default='', help='plaatsnaam achter "The Hunt" op de voorkant (standaard zonder)')
    ap.add_argument('--groepsfotos', help='map met groepsfoto\'s (standaard tools/loquiz/groepsfotos/<game>-<scope>)')
    ap.add_argument('--uit', help='uitvoermap (standaard tools/loquiz/uitvoer/<game>-<scope>)')
    ap.add_argument('--browser', help='pad naar Edge of Chrome voor de PDF')
    ap.add_argument('--geen-pdf', action='store_true', help='alleen HTML maken')
    ap.add_argument('--demo', action='store_true')
    a = ap.parse_args()
    if a.url:
        try:
            a.game, a.scope = lees_url(a.url)
        except ValueError as fout:
            sys.exit(str(fout))
    maak(a.game, a.scope, a.stad, a.groepsfotos, a.uit, browser(a.browser) if a.browser else None,
         pdf=not a.geen_pdf, demo=a.demo)


if __name__ == '__main__':
    main()
