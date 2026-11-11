"""Fotoboek per groep: PDF en (via boekje_tool.py) een online pagina met wachtwoord. Eén boekje per Loquiz-game en scope.

    python tools/loquiz/boekje.py --url https://results.loquiz.com/F3CJ8WVUSC:VANWIJNEN --teamfoto team.jpg
    python tools/loquiz/boekje.py --url ... --extra foto1.jpg foto2.jpg --min-fotos 8 --stad "Den Haag"
    python tools/loquiz/boekje.py --demo                  # voorbeeldboekje zonder API

Opbouw van de PDF:
  1. voorkant met onze eigen foto: "Missie volbracht · Bedankt voor het spelen van The Hunt"
  2. jullie Hunt in cijfers: gemiddeld en totaal gelopen, per team km, stappen, kcal en CO2-besparing, plus de video
  3. de teamfoto van de spelleider (één foto, groot)
  4. alle foto's: uit Loquiz, de extra foto's (spelleider, social media) en zo nodig eigen sfeerfoto's tot het minimum
  5. laat een review achter, met de andere spellen van Badass Games, spelleiders werven en de contactgegevens

Werkwijze: verzamel() haalt de gegevens en foto's op in tools/loquiz/uitvoer/<game>-<scope>/ (map fotos/ en boekje.json),
opmaken() maakt daaruit de PDF en de inhoud van de online pagina. De PDF maakt het script met Edge of Chrome (headless,
zit standaard op Windows). Eigen sfeerfoto's: zet ze in tools/loquiz/eigen-fotos/, anders kiest het script foto's van
de site (EIGEN_FOTOS). Zonder opdrachtregel: dubbelklik "Boekje maken.bat" (boekje_tool.py) voor het invulscherm.
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
import urllib.request
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from resultaten import HIER, ROOT, STANDAARD_GAME, STANDAARD_SCOPE, e, ophalen  # noqa: E402

SITE = json.load(open(os.path.join(ROOT, 'src', 'data', 'site.json'), encoding='utf-8'))
DOCS = Path(ROOT) / 'docs'

VOORKANT_FOTO = '/assets/uploads/2026/11/the-hunt-fotoboek-voorkant-1600.jpg'  # onze eigen foto, pad binnen docs/
VIDEO = SITE['url'] + '/assets/video/the-hunt-trailer-720p.mp4'
VIDEO_POSTER = '/assets/uploads/2026/09/the-hunt-hunter-en-groepen-1600.jpg'
REVIEW_FOTO = '/assets/uploads/2026/09/the-hunt-extractiepunt-gehaald-1600.jpg'  # foto op de reviewpagina
HUNTER_FOTO = '/assets/uploads/2026/11/the-hunt-hunter-rugtas-gezocht.jpg'         # foto bij Hunters gezocht
BADASS_LOGO = '/assets/uploads/2026/11/badassgames-logo-rond-600.png'   # logo op de spellenpagina

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
               'Op Google of via onze website: het kost je een minuutje.'),
    'review_url': 'https://escapegamethehunt.nl/review/',
    'spellen_kop': 'Meer spellen van Badass Games',
    'spellen': 'Zin in meer? Badass Games maakt nog meer spellen voor groepen, teams en families.',
    'hunter_label': 'Gezocht: Hunters',
    'hunter_kop': 'Wil jullie zoon of dochter ook Hunter worden?',
    'hunter': ('Wij zoeken spelleiders in heel Nederland: groepen ontvangen, het spel uitleggen en daarna als Hunter '
               'de jacht openen. Een bijbaan vol actie, in de eigen stad.'),
    'hunter_url': 'https://escapegamethehunt.nl/werken-bij/werken-bij-escape-game-the-hunt-spelleider/',
    'hunter_link': 'escapegamethehunt.nl/werken-bij',
}

# Andere spellen op de laatste pagina. Vul de omschrijving en link in; laat 'link' leeg om hem weg te laten.
SPELLEN = SITE.get('badass_spellen', [])  # meer spellen van Badass Games, uit src/data/site.json

KENGETALLEN = {  # indicatief
    'stappen_per_km': 1350,      # gemiddelde wandelaar
    'kcal_per_km': 55,           # per persoon, stevig wandeltempo
    'co2_auto_per_km': 0.18,     # kg CO2 per km voor een gemiddelde personenauto (één auto per team)
}

FOTO_EXT = ('.jpg', '.jpeg', '.png', '.webp')
MIN_FOTOS = 8       # aanvullen met eigen sfeerfoto's tot minimaal zoveel foto's
EIGEN_MAP = os.path.join(HIER, 'eigen-fotos')
EIGEN_FOTOS = [     # sfeerfoto's van de site (pad binnen docs/), gebruikt als tools/loquiz/eigen-fotos/ leeg is
    '/assets/uploads/2026/11/the-hunt-high-five-1600.jpg',
    '/assets/uploads/2026/11/the-hunt-spelleider-briefing-1600.jpg',
    '/assets/uploads/2026/11/the-hunt-gameapp-scannen-1600.jpg',
    '/assets/uploads/2026/11/the-hunt-spelleider-overzicht-1600.jpg',
    '/assets/uploads/2026/11/the-hunt-samen-puzzelen-1600.jpg',
    '/assets/uploads/2026/11/the-hunt-spelleider-legt-uit-1600.jpg',
    '/assets/uploads/2026/09/the-hunt-gameapp-1600.jpg',
    '/assets/uploads/2026/09/the-hunt-puzzelen-met-kaart-1600.jpg',
    '/assets/uploads/2026/09/the-hunt-extractiepunt-gehaald-1600.jpg',
    '/assets/uploads/2026/09/the-hunt-team-puzzelt-1600.jpg',
]
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


def eigen_fotos():
    """Sfeerfoto's om aan te vullen: eerst tools/loquiz/eigen-fotos/, anders de lijst EIGEN_FOTOS van de site."""
    if os.path.isdir(EIGEN_MAP):
        eigen = [p for p in sorted(glob.glob(os.path.join(EIGEN_MAP, '*'))) if p.lower().endswith(FOTO_EXT)]
        if eigen:
            return eigen
    return [str(DOCS / p.lstrip('/')) for p in EIGEN_FOTOS if (DOCS / p.lstrip('/')).exists()]


def cijfers(teams):
    """Per team km, stappen, kcal en CO2, plus de totalen (gedeeld door PDF en online pagina)."""
    k = KENGETALLEN
    rijen = [(t.get('naam') or t.get('name') or 'Team', km(t)) for t in teams]
    rijen = [(n, d, d * k['stappen_per_km'], d * k['kcal_per_km'], d * k['co2_auto_per_km']) for n, d in rijen]
    rijen.sort(key=lambda r: r[1], reverse=True)  # wie het verst liep bovenaan
    gelopen = [r for r in rijen if r[1] > 0]
    tot_km = sum(r[1] for r in rijen)
    return {'rijen': rijen, 'tot_km': tot_km, 'gem_km': tot_km / len(gelopen) if gelopen else 0,
            'tot_co2': sum(r[4] for r in rijen)}


def km(team):
    try:
        return float(team.get('km', team.get('odometer')) or 0)
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
.voor .beeld{{position:absolute;inset:0 0 auto 0;height:190mm;background:var(--navy) center/cover no-repeat}}
.voor .logovlak{{position:absolute;top:0;left:0;background:var(--night);padding:8mm 10mm 8mm 16mm;border-bottom-right-radius:4mm;z-index:2}}
.voor .logo{{display:block;height:18mm}}
.voor .tekst{{position:absolute;left:16mm;right:16mm;top:204mm;z-index:2}}
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
.raster{{display:grid;grid-template-columns:1fr 1fr;gap:5mm}}
.raster figure{{margin:0}}
.raster img{{width:100%;height:104mm;object-fit:cover;border-radius:2mm;display:block;background:var(--paper)}}
.raster figcaption{{font:7.5pt var(--mono);letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin-top:1.5mm;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}

/* review + hunters */
.review p{{color:var(--on-dark-muted);font-size:11.5pt;max-width:165mm}}
.rv-foto{{width:100%;height:62mm;object-fit:cover;border-radius:2.5mm;display:block;margin:2mm 0 5mm}}
.knoppen{{display:flex;flex-wrap:wrap;gap:4mm;margin-top:5mm}}
.knop{{display:inline-block;background:var(--signal);color:var(--night);font-weight:700;padding:3.5mm 8mm;border-radius:20mm;text-decoration:none;font-size:12pt}}
.knop.lijn{{background:none;color:#fff;border:1.5px solid rgba(255,255,255,.5)}}
.hunter{{margin-top:10mm;display:grid;grid-template-columns:62mm 1fr;background:var(--signal);color:var(--night);border-radius:2.5mm;overflow:hidden;text-decoration:none}}
.hunter img{{width:100%;height:100%;min-height:62mm;object-fit:cover;display:block}}
.hunter .in{{padding:6mm}}
.hunter .label{{color:var(--night);opacity:.75}}
.hunter b{{display:block;font-size:15pt;line-height:1.2;margin:1.5mm 0 2mm}}
.hunter span{{font-size:10pt;line-height:1.45;display:block}}
.hunter u{{display:inline-block;margin-top:4mm;text-decoration:none;font-weight:700;font-size:10pt;border:2px solid var(--night);border-radius:20mm;padding:2.5mm 4.5mm}}
/* meer spellen */

.spellen-blad .bg-logo{{float:right;width:30mm;height:30mm;margin:0 0 4mm 6mm}}
.spellen-blad p.intro{{color:var(--on-dark-muted)}}
.kaarten{{display:grid;grid-template-columns:1fr 1fr;gap:5mm;margin-top:6mm}}
.kaart{{border:1px solid rgba(255,255,255,.15);border-radius:2.5mm;overflow:hidden;border-top:3px solid var(--signal);text-decoration:none;color:inherit;display:block;background:rgb(31,43,56)}}
.kaart img{{width:100%;height:42mm;object-fit:cover;display:block}}
.kaart .in{{padding:5mm}}
.kaart b{{display:block;color:#fff;font-size:14pt;margin-bottom:1.5mm}}
.kaart span{{font-size:10pt;line-height:1.45;color:var(--on-dark-muted);display:block}}
.kaart u{{display:block;margin-top:3mm;text-decoration:none;font-weight:700;font-size:10pt;color:var(--signal)}}
.contact{{position:absolute;left:16mm;right:16mm;bottom:20mm;display:flex;justify-content:space-between;align-items:flex-end}}
.contact img{{height:15mm}}
.contact div{{text-align:right;font-size:10pt;line-height:1.6}}
.contact a{{color:#fff;text-decoration:none}}
'''


def voet(onder, nr, donker=False):
    return f'<div class="voet"><span>{e(onder)}</span><span>{nr:02d}</span></div>'


def boekje(titel_game, teams, fotos, teamfoto, stad):
    """fotos: lijst van (src, bijschrift); teamfoto: src of None."""
    logo = site_uri(SITE['logo'])
    onder = 'The Hunt' + (f' · {stad}' if stad else '')
    k = KENGETALLEN
    bladen, nr = [], 1

    # 1. voorkant
    bladen.append(f'''<section class="blad donker voor">
  <div class="beeld" style="background-image:url('{e(site_uri(VOORKANT_FOTO))}')"></div>
  <div class="logovlak"><img class="logo" src="{e(logo)}" alt="The Hunt"></div>
  <div class="tekst">
    <div class="label">{e(TEKST["label"])}</div>
    <h1>{e(TEKST["bedankt"])}{f' in <em>{e(stad)}</em>' if stad else ''}</h1>
  </div>
  <div class="streep"></div>
</section>''')

    # 2. cijfers per groep en per team, met de video
    c = cijfers(teams)
    rijen, tot_km, gem_km, tot_co2 = c['rijen'], c['tot_km'], c['gem_km'], c['tot_co2']
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

    # 3. teamfoto van de spelleider, groot
    if teamfoto:
        nr += 1
        bladen.append(f'''<section class="blad"><div class="binnen groepsfoto">
    <div class="label">{e(TEKST["label"])}</div><h2>{e(TEKST["groepsfoto_kop"])}</h2>
    <img src="{e(teamfoto)}" alt="Groepsfoto">
  </div>{voet(onder, nr)}</section>''')

    # 4. alle foto's, vier per pagina, met de teamnaam
    alle = fotos
    for i in range(0, len(alle), 4):
        nr += 1
        figs = ''.join(f'<figure><img src="{e(src)}" alt="{e(n or "Foto")}"><figcaption>{e(n)}&nbsp;</figcaption></figure>'
                       for src, n in alle[i:i + 4])
        kop = (f'<div class="label">{e(TEKST["label"])}</div><h2>{e(TEKST["fotos_kop"])}</h2>' if i == 0
               else f'<div class="label">{e(TEKST["fotos_kop"])}</div><div style="height:5mm"></div>')
        bladen.append(f'''<section class="blad"><div class="binnen">{kop}
    <div class="raster">{figs}</div>
  </div>{voet(onder, nr)}</section>''')

    # 5. review en Hunters gezocht
    nr += 1
    google = SITE.get('google_review_url') or ''
    knoppen = ((f'<a class="knop" href="{e(google)}">Google-review</a>'
                f'<a class="knop lijn" href="{e(TEKST["review_url"])}">Review via onze website</a>') if google
               else f'<a class="knop" href="{e(TEKST["review_url"])}">Laat een review achter</a>')
    bladen.append(f'''<section class="blad donker review"><div class="binnen">
    <div class="label">{e(TEKST["label"])}</div>
    <h2>{e(TEKST["review_kop"])}</h2>
    <img class="rv-foto" src="{e(site_uri(REVIEW_FOTO))}" alt="">
    <p>{e(TEKST["review"])}</p>
    <div class="knoppen">{knoppen}</div>
    <a class="hunter" href="{e(TEKST["hunter_url"])}">
      <img src="{e(site_uri(HUNTER_FOTO))}" alt="">
      <div class="in"><div class="label">{e(TEKST["hunter_label"])}</div><b>{e(TEKST["hunter_kop"])}</b><span>{e(TEKST["hunter"])}</span>
      <u>{e(TEKST["hunter_link"])} →</u></div>
    </a>
  </div>
  {voet(onder, nr, True)}
</section>''')

    # 6. meer spellen van Badass Games + contact
    nr += 1
    kaarten = ''.join(
        (f'<a class="kaart" href="{e(s["link"])}">' if s.get('link') else '<div class="kaart">')
        + (f'<img src="{e(site_uri(s["foto"]) if s["foto"].startswith("/") else s["foto"])}" alt="">' if s.get('foto') else '')
        + f'<div class="in"><b>{e(s["naam"])}</b><span>{e(s["tekst"])}</span>'
        + (f'<u>{e(s["link"].replace("https://", "").rstrip("/"))} →</u>' if s.get('link') else '')
        + '</div>' + ('</a>' if s.get('link') else '</div>')
        for s in SPELLEN)
    bladen.append(f'''<section class="blad donker spellen-blad"><div class="binnen">
    <img class="bg-logo" src="{e(site_uri(BADASS_LOGO))}" alt="Badass Games">
    <div class="label">Badass Games</div>
    <h2>{e(TEKST["spellen_kop"])}</h2>
    <p class="intro">{e(TEKST["spellen"])}</p>
    <div class="kaarten">{kaarten}</div>
  </div>
  <div class="contact">
    <img src="{e(logo)}" alt="The Hunt">
    <div><a href="{e(SITE["url"])}">{e(SITE["url"].replace("https://", ""))}</a><br>
      <a href="mailto:{e(SITE["email"])}">{e(SITE["email"])}</a><br>
      <a href="tel:{e(SITE["phone"])}">{e(SITE["phone_display"])}</a></div>
  </div>
  {voet(onder, nr, True)}
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


# ---------------------------------------------------------------- verzamelen

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


def werkmap(sleutel):
    return os.path.join(HIER, 'uitvoer', sleutel)


def ext_van(naam, standaard='.jpg'):
    x = os.path.splitext(urllib.parse.urlparse(naam).path)[1].lower()
    return '.jpg' if x == '.jpeg' else (x if x in FOTO_EXT else standaard)


def download(url, doel):
    req = urllib.request.Request(url, headers={'User-Agent': 'thehunt-fotoboek/1.0'})
    with urllib.request.urlopen(req, timeout=60) as r, open(doel, 'wb') as fh:
        shutil.copyfileobj(r, fh)


def verzamel(game_id, scope, stad='', teamfoto=None, extra=(), min_fotos=MIN_FOTOS, demo=False, log=print, vervang=False):
    """Haalt teams en foto's op en zet alles in de werkmap: fotos/ en boekje.json.

    teamfoto en extra zijn paden naar foto's op schijf; ze worden naar fotos/team.* en fotos/extra-NN.* gekopieerd.
    Bestaan die al in fotos/ en geef je niets mee, dan blijven ze staan; met vervang=True gaan oude altijd weg."""
    game, teams, per_team, _, _ = ophalen(game_id, scope, demo)
    sleutel = 'demo' if demo else mapnaam(game_id, scope)
    map_ = werkmap(sleutel)
    fmap = os.path.join(map_, 'fotos')
    os.makedirs(fmap, exist_ok=True)
    weg = ('loquiz-', 'eigen-') + (('team.', 'extra-') if vervang else ())
    for oud in os.listdir(fmap):  # Loquiz- en eigen foto's altijd opnieuw
        if oud.startswith(weg):
            os.remove(os.path.join(fmap, oud))
    if teamfoto:
        for oud in os.listdir(fmap):
            if oud.startswith('team.'):
                os.remove(os.path.join(fmap, oud))
        shutil.copyfile(teamfoto, os.path.join(fmap, 'team' + ext_van(teamfoto)))
    if extra:
        for oud in os.listdir(fmap):
            if oud.startswith('extra-'):
                os.remove(os.path.join(fmap, oud))
        for i, pad in enumerate(extra, 1):
            shutil.copyfile(pad, os.path.join(fmap, f'extra-{i:02d}{ext_van(pad)}'))

    fotos = []
    demo_bron = eigen_fotos()
    n = 0
    for t in teams:
        for m in per_team.get(str(t.get('id')), []):
            if m['video'] or m['audio']:
                continue
            n += 1
            naam = f'loquiz-{n:02d}{ext_van(m["url"])}'
            try:
                if demo:
                    shutil.copyfile(demo_bron[(n - 1) % len(demo_bron)], os.path.join(fmap, naam))
                else:
                    download(m['url'], os.path.join(fmap, naam))
            except OSError as fout:
                log(f'Foto overgeslagen ({fout}): {m["url"]}')
                continue
            fotos.append({'bestand': naam, 'bron': 'loquiz', 'bijschrift': t.get('name') or ''})
    for naam in sorted(os.listdir(fmap)):
        if naam.startswith('extra-'):
            fotos.append({'bestand': naam, 'bron': 'extra', 'bijschrift': ''})
    tekort = max(0, int(min_fotos or 0) - len(fotos))
    for i, bron in enumerate(eigen_fotos()[:tekort], 1):
        naam = f'eigen-{i:02d}{ext_van(bron)}'
        shutil.copyfile(bron, os.path.join(fmap, naam))
        fotos.append({'bestand': naam, 'bron': 'eigen', 'bijschrift': ''})
    team = next((f for f in sorted(os.listdir(fmap)) if f.startswith('team.')), None)

    gegevens = {'sleutel': sleutel, 'game': game_id, 'scope': scope, 'stad': (stad or '').strip(),
                'titel': game.get('title') or game.get('name') or game_id,
                'teams': [{'naam': t.get('name') or 'Team', 'km': km(t)} for t in teams],
                'teamfoto': team, 'fotos': fotos}
    with open(os.path.join(map_, 'boekje.json'), 'w', encoding='utf-8') as fh:
        json.dump(gegevens, fh, ensure_ascii=False, indent=1)
    soorten = {b: sum(1 for f in fotos if f['bron'] == b) for b in ('loquiz', 'extra', 'eigen')}
    log(f'{len(teams)} teams; foto\'s: {soorten["loquiz"]} uit Loquiz, {soorten["extra"]} extra, '
        f'{soorten["eigen"]} eigen; teamfoto: {"ja" if team else "nee"}')
    return gegevens


# ---------------------------------------------------------------- opmaken

def opmaken(sleutel, exe=None, pdf=True, log=print):
    """Maakt uit de werkmap de PDF (boekje-<sleutel>.pdf) en de inhoud voor de online pagina (online.html)."""
    import fotoboek_web
    map_ = werkmap(sleutel)
    g = json.load(open(os.path.join(map_, 'boekje.json'), encoding='utf-8'))
    fmap = os.path.join(map_, 'fotos')
    fotos = [(uri(os.path.join(fmap, f['bestand'])), f['bijschrift']) for f in g['fotos']]
    team = uri(os.path.join(fmap, g['teamfoto'])) if g.get('teamfoto') else None
    html_pad = os.path.join(map_, f'boekje-{sleutel}.html')
    with open(html_pad, 'w', encoding='utf-8') as fh:
        fh.write(boekje(g['titel'], g['teams'], fotos, team, g['stad']))
    uitkomst = {'titel': g['titel'], 'teams': len(g['teams']), 'fotos': len(g['fotos']), 'teamfoto': bool(team),
                'html': html_pad, 'pdf': None, 'online': None, 'map': map_}
    if pdf:
        exe = exe or browser()
        pdf_pad = os.path.join(map_, f'fotoboek-the-hunt-{sleutel}.pdf')
        if not exe:
            log('Geen Edge of Chrome gevonden: open de HTML en kies Afdrukken > Opslaan als PDF.')
        elif naar_pdf(exe, html_pad, pdf_pad):
            uitkomst['pdf'] = pdf_pad
            log(f'PDF: {pdf_pad}')
        else:
            log('PDF maken mislukt: open de HTML en kies Afdrukken > Opslaan als PDF.')
    online = os.path.join(map_, 'online.html')
    with open(online, 'w', encoding='utf-8') as fh:
        fh.write(fotoboek_web.inhoud(g, os.path.basename(uitkomst['pdf']) if uitkomst['pdf'] else None))
    uitkomst['online'] = online
    log(f'HTML: {html_pad}')
    return uitkomst


def maak(game_id, scope, stad='', teamfoto=None, extra=(), min_fotos=MIN_FOTOS, exe=None, pdf=True, demo=False,
         log=print):
    g = verzamel(game_id, scope, stad, teamfoto, extra, min_fotos, demo, log)
    return opmaken(g['sleutel'], exe, pdf, log)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--url', help='spelleider-URL, bijv. https://results.loquiz.com/F3CJ8WVUSC:VANWIJNEN')
    ap.add_argument('--game', default=STANDAARD_GAME)
    ap.add_argument('--scope', default=STANDAARD_SCOPE)
    ap.add_argument('--stad', default='', help='plaatsnaam achter "The Hunt" op de voorkant (standaard zonder)')
    ap.add_argument('--teamfoto', help='de teamfoto van de spelleider (één foto)')
    ap.add_argument('--extra', nargs='*', default=[], help='extra foto\'s (spelleider, social media)')
    ap.add_argument('--min-fotos', type=int, default=MIN_FOTOS, help='aanvullen met eigen foto\'s tot dit aantal')
    ap.add_argument('--browser', help='pad naar Edge of Chrome voor de PDF')
    ap.add_argument('--geen-pdf', action='store_true', help='alleen HTML maken')
    ap.add_argument('--demo', action='store_true')
    a = ap.parse_args()
    if a.url:
        try:
            a.game, a.scope = lees_url(a.url)
        except ValueError as fout:
            sys.exit(str(fout))
    maak(a.game, a.scope, a.stad, a.teamfoto, a.extra, a.min_fotos, browser(a.browser) if a.browser else None,
         pdf=not a.geen_pdf, demo=a.demo)


if __name__ == '__main__':
    main()
