"""Fotoboekje per team als PDF: bedankt, teamfoto, kilometers en duurzaamheid, video, foto's uit Loquiz en info.

    python tools/loquiz/boekje.py                         # alle teams van game FK9SCMLMAJ, scope ADHOC
    python tools/loquiz/boekje.py --team "De Vluchtelingen"
    python tools/loquiz/boekje.py --stad "Den Haag" --video https://...
    python tools/loquiz/boekje.py --demo                  # voorbeeldboekjes zonder API

Teamfoto's van de spelleider: zet ze in tools/loquiz/teamfotos/<game>/. Een foto hoort bij een team als de
bestandsnaam met de teamnaam begint (bijv. "De Vluchtelingen.jpg", "de-vluchtelingen-2.jpg") of als hij in een
submap met de teamnaam staat. Zonder teamfoto komt de mooiste Loquiz-foto op de voorkant.

Uitvoer: tools/loquiz/uitvoer/<game>/boekjes/<team>.html en .pdf. De PDF maakt het script met Edge of Chrome
(headless, zit standaard op Windows). Lukt dat niet, open dan de .html en kies Afdrukken > Opslaan als PDF.
Teksten en kengetallen staan hieronder in TEKST en KENGETALLEN.
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
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from resultaten import HIER, ROOT, STANDAARD_GAME, STANDAARD_SCOPE, e, ophalen  # noqa: E402

SITE = json.load(open(os.path.join(ROOT, 'src', 'data', 'site.json'), encoding='utf-8'))
DOCS = Path(ROOT) / 'docs'

TEKST = {
    'bedankt': 'Bedankt voor het spelen van The Hunt',
    'intro': ('Jullie zijn de Hunters te slim af geweest (of bijna). In dit boekje vinden jullie de foto\'s die '
              'onderweg zijn gemaakt, hoeveel jullie hebben gelopen en de video van de dag.'),
    'duurzaam_kop': 'Lopend door de stad',
    'duurzaam': ('Jullie hebben de hele stad te voet veroverd. Geen bus, geen auto: alleen jullie benen, de app en '
                 'een flinke dosis teamwork. Goed voor de conditie en goed voor de lucht in de stad.'),
    'video_kop': 'De video',
    'video': 'Bekijk de video van The Hunt en beleef het nog een keer.',
    'fotos_kop': 'Onderweg',
    'info_kop': 'Tot de volgende Hunt',
    'info': ('Vonden jullie het een topdag? Laat dan een review achter, dat helpt ons enorm. En The Hunt speel je in '
             'steden door heel Nederland, dus de volgende keer kan het in een andere stad.'),
    'review_url': 'https://escapegamethehunt.nl/',
}

KENGETALLEN = {  # indicatief, alleen voor de duurzaamheidspagina
    'stappen_per_km': 1350,      # gemiddelde wandelaar
    'kcal_per_km': 55,           # per persoon, rustig tot stevig wandeltempo
    'co2_auto_per_km': 0.18,     # kg CO2 per km voor een gemiddelde personenauto
}

STANDAARD_VIDEO = SITE['url'] + '/assets/video/the-hunt-trailer-720p.mp4'
FOTO_EXT = ('.jpg', '.jpeg', '.png', '.webp')


# ---------------------------------------------------------------- hulpjes

def slug(s):
    s = str(s or '').lower()
    for a, b in (('à', 'a'), ('á', 'a'), ('ä', 'a'), ('é', 'e'), ('è', 'e'), ('ë', 'e'), ('ï', 'i'), ('ö', 'o'), ('ü', 'u')):
        s = s.replace(a, b)
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-') or 'team'


def uri(pad):
    return Path(pad).resolve().as_uri()


def nl_getal(v, dec=0):
    s = f'{v:,.{dec}f}'
    return s.replace(',', 'X').replace('.', ',').replace('X', '.')


def tijd(v):
    if v in (None, '', 0):
        return None
    try:
        if isinstance(v, (int, float)) or str(v).isdigit():
            v = float(v)
            return datetime.fromtimestamp(v / 1000 if v > 1e11 else v, tz=timezone.utc).astimezone()
        return datetime.fromisoformat(str(v).replace('Z', '+00:00')).astimezone()
    except (ValueError, OSError):
        return None


MAANDEN = 'januari februari maart april mei juni juli augustus september oktober november december'.split()


def stad_uit(titel):
    t = re.sub(r'(?i)^\s*(escape\s*game\s*)?the\s*hunt\s*(nl\s*)?[-:|]*\s*', '', titel or '').strip()
    return t


def teamfotos(map_, team):
    """Foto's van de spelleider voor dit team."""
    if not map_ or not os.path.isdir(map_):
        return []
    s, uit = slug(team.get('name')), []
    for pad in sorted(glob.glob(os.path.join(map_, '**', '*'), recursive=True)):
        if not pad.lower().endswith(FOTO_EXT):
            continue
        rel = os.path.relpath(pad, map_)
        delen = [slug(os.path.splitext(x)[0]) for x in Path(rel).parts]
        if any(d == s or d.startswith(s + '-') for d in delen):
            uit.append(uri(pad))
    return uit


def duur(team):
    begin = tijd(team.get('startTime') or team.get('startedAt'))
    eind = tijd(team.get('finishTime') or team.get('finishedAt') or team.get('endTime') or team.get('finishedTime'))
    if begin and eind and eind > begin:
        m = int((eind - begin).total_seconds() // 60)
        return f'{m // 60}:{m % 60:02d}'
    return None


def leden(team):
    l = team.get('members')
    if isinstance(l, list):
        return [str(x.get('name', '') if isinstance(x, dict) else x) for x in l if x]
    if isinstance(l, str) and l.strip():
        return [x.strip() for x in re.split(r'[,\n]', l) if x.strip()]
    return []


# ---------------------------------------------------------------- HTML

def css():
    fonts = DOCS / 'assets' / 'fonts'
    return f'''
@font-face{{font-family:'Lato';font-weight:400;src:url({uri(fonts / 'S6uyw4BMUTPHjx4wXg.woff2')}) format('woff2')}}
@font-face{{font-family:'Lato';font-weight:700;src:url({uri(fonts / 'S6u9w4BMUTPHh6UVSwiPGQ.woff2')}) format('woff2')}}
@page{{size:A4;margin:0}}
:root{{--night:#141e29;--navy:#29394a;--signal:#f29222;--signal-2:#ffae4d;--paper:#f3f5f7;--ink:#1c2834;--muted:#5a6878;
  --on-dark:#e7edf3;--on-dark-muted:#a9b6c4;--mono:ui-monospace,'Cascadia Mono',Consolas,monospace}}
*{{box-sizing:border-box}}
html,body{{margin:0;background:#888}}
body{{font:400 11pt/1.55 'Lato',system-ui,sans-serif;color:var(--ink);-webkit-print-color-adjust:exact;print-color-adjust:exact}}
.blad{{width:210mm;height:297mm;margin:0 auto 10mm;background:#fff;position:relative;overflow:hidden;page-break-after:always;break-after:page}}
.blad:last-child{{page-break-after:auto;break-after:auto}}
@media print{{html,body{{background:#fff}}.blad{{margin:0}}}}
.label{{font:700 8pt/1.2 var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--signal)}}
h1,h2{{margin:0;line-height:1.05;letter-spacing:-.01em}}
h2{{font-size:24pt;margin:3mm 0 5mm}}
.binnen{{padding:18mm 18mm 0}}
.voet{{position:absolute;left:18mm;right:18mm;bottom:10mm;display:flex;justify-content:space-between;font:8pt var(--mono);
  color:var(--muted);letter-spacing:.06em;text-transform:uppercase;border-top:1px solid #dbe2e9;padding-top:3mm}}

/* voorkant */
.voor{{background:var(--night);color:var(--on-dark)}}
.voor .beeld{{position:absolute;inset:0 0 auto 0;height:190mm;background:var(--navy) center/cover no-repeat}}
.voor .beeld::after{{content:'';position:absolute;inset:0;background:linear-gradient(180deg,rgba(20,30,41,.35) 0,rgba(20,30,41,0) 35%,rgba(20,30,41,.2) 70%,var(--night) 100%)}}
.voor .logo{{position:absolute;top:14mm;left:18mm;height:16mm;z-index:2}}
.voor .tekst{{position:absolute;left:18mm;right:18mm;top:178mm;z-index:2}}
.voor h1{{font-size:34pt;color:#fff;margin:3mm 0 4mm}}
.voor h1 em{{font-style:normal;color:var(--signal)}}
.voor .team{{font-size:17pt;font-weight:700;color:#fff}}
.voor .wie{{color:var(--on-dark-muted);margin-top:1mm}}
.voor .datum{{position:absolute;left:18mm;bottom:12mm;font:9pt var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--on-dark-muted)}}
.voor .streep{{position:absolute;right:0;bottom:0;width:60mm;height:4mm;background:var(--signal)}}

/* cijfers */
.intro{{font-size:12.5pt;color:var(--muted);max-width:150mm}}
.km{{margin:10mm 0 8mm;display:flex;align-items:flex-end;gap:5mm}}
.km b{{font-size:78pt;line-height:.85;font-weight:700;color:var(--navy);letter-spacing:-.03em}}
.km span{{font:700 13pt/1.2 'Lato';color:var(--signal);padding-bottom:3mm}}
.tegels{{display:grid;grid-template-columns:repeat(3,1fr);gap:4mm}}
.tegel{{background:var(--paper);border-radius:3mm;padding:5mm}}
.tegel b{{display:block;font-size:20pt;color:var(--navy);line-height:1.1}}
.tegel span{{font-size:9pt;color:var(--muted)}}
.duurzaam{{margin-top:8mm;background:var(--navy);color:var(--on-dark);border-radius:3mm;padding:7mm;display:grid;grid-template-columns:1fr 46mm;gap:6mm;align-items:center}}
.duurzaam h3{{margin:0 0 2mm;color:#fff;font-size:14pt}}
.duurzaam p{{margin:0;font-size:10pt;color:var(--on-dark-muted)}}
.duurzaam .co2{{text-align:center;border-left:1px solid rgba(255,255,255,.15);padding-left:5mm}}
.duurzaam .co2 b{{display:block;font-size:30pt;color:var(--signal);line-height:1}}
.duurzaam .co2 span{{font-size:8.5pt;color:var(--on-dark-muted)}}
.kleine{{font-size:7.5pt;color:var(--muted);margin-top:2mm}}
.video{{margin-top:8mm;display:grid;grid-template-columns:78mm 1fr;gap:6mm;align-items:center;text-decoration:none;color:inherit}}
.video .poster{{position:relative;height:44mm;border-radius:3mm;background:var(--navy) center/cover no-repeat}}
.video .poster i{{position:absolute;left:50%;top:50%;width:14mm;height:14mm;margin:-7mm 0 0 -7mm;border-radius:50%;background:var(--signal);
  display:grid;place-items:center;color:var(--night);font-style:normal;font-size:14pt;padding-left:1mm}}
.video h3{{margin:0 0 2mm;font-size:14pt}}
.video p{{margin:0;color:var(--muted);font-size:10pt}}
.video u{{color:var(--signal);text-decoration:none;font-weight:700;font-size:10pt}}

/* foto's */
.raster{{display:grid;gap:4mm;grid-template-columns:1fr 1fr}}
.raster.n1{{grid-template-columns:1fr}}
.raster img{{width:100%;height:100%;object-fit:cover;border-radius:2mm;display:block;background:var(--paper)}}
.raster.n1 img{{height:200mm}}
.raster.n2 img{{height:120mm}}
.raster.n3 img,.raster.n4 img{{height:108mm}}
.raster.n5 img,.raster.n6 img{{height:72mm}}
.raster.n3 img:first-child{{grid-column:1/-1}}
.raster.n5 img:first-child{{grid-column:1/-1}}
.teamfoto img{{width:100%;height:150mm;object-fit:cover;border-radius:3mm}}
.teamfoto p{{color:var(--muted);margin-top:4mm}}

/* info */
.info{{background:var(--night);color:var(--on-dark)}}
.info h2{{color:#fff}}
.info p{{color:var(--on-dark-muted);font-size:12pt;max-width:150mm}}
.knop{{display:inline-block;margin-top:7mm;background:var(--signal);color:var(--night);font-weight:700;padding:3.5mm 7mm;border-radius:20mm;text-decoration:none}}
.steden{{margin-top:12mm;columns:3;font-size:9.5pt;color:var(--on-dark-muted)}}
.steden div{{break-inside:avoid}}
.contact{{position:absolute;left:18mm;right:18mm;bottom:22mm;display:flex;justify-content:space-between;align-items:flex-end}}
.contact img{{height:14mm}}
.contact div{{text-align:right;font-size:10pt;line-height:1.6}}
.contact a{{color:#fff;text-decoration:none}}
.info .voet{{border-color:rgba(255,255,255,.15);color:var(--on-dark-muted)}}
'''


def voet(stad, team, nr):
    return f'<div class="voet"><span>The Hunt{" · " + e(stad) if stad else ""} · {e(team)}</span><span>{nr:02d}</span></div>'


def boekje(game, team, media, fotos_spelleider, stad, video):
    naam = team.get('name') or 'Team'
    logo = uri(DOCS / SITE['logo'].lstrip('/'))
    poster = uri(DOCS / SITE['og_image'].lstrip('/'))
    loquiz = [m for m in media if not m['video'] and not m['audio']]
    voor = (fotos_spelleider or [m['url'] for m in loquiz] or [poster])[0]
    begin = tijd(team.get('startTime') or team.get('startedAt'))
    datum = f'{begin.day} {MAANDEN[begin.month - 1]} {begin.year}' if begin else ''
    wie = leden(team)
    nr = 1
    bladen = []

    # 1. voorkant
    bladen.append(f'''<section class="blad voor">
  <div class="beeld" style="background-image:url('{e(voor)}')"></div>
  <img class="logo" src="{e(logo)}" alt="The Hunt">
  <div class="tekst">
    <div class="label">Missie volbracht</div>
    <h1>{e(TEKST["bedankt"])}{f' in <em>{e(stad)}</em>' if stad else ''}</h1>
    <div class="team">{e(naam)}</div>
    {f'<div class="wie">{e(", ".join(wie))}</div>' if wie else ''}
  </div>
  {f'<div class="datum">{e(datum)}</div>' if datum else ''}
  <div class="streep"></div>
</section>''')

    # 2. jullie hunt in cijfers + duurzaamheid + video
    nr += 1
    km = float(team.get('odometer') or 0)
    k = KENGETALLEN
    personen = max(len(wie), 1)
    tegels = [
        (nl_getal(km * k['stappen_per_km']), 'stappen per persoon (ongeveer)'),
        (nl_getal(km * k['kcal_per_km']), 'kcal verbrand per persoon'),
    ]
    d = duur(team)
    tegels.append((d, 'uur onderweg') if d else (str(len(loquiz)), "foto's gemaakt"))
    tegels_html = ''.join(f'<div class="tegel"><b>{e(a)}</b><span>{e(b)}</span></div>' for a, b in tegels)
    co2 = km * k['co2_auto_per_km'] * max(1, round(personen / 4))
    bladen.append(f'''<section class="blad">
  <div class="binnen">
    <div class="label">Jullie Hunt</div>
    <h2>{e(naam)}</h2>
    <p class="intro">{e(TEKST["intro"])}</p>
    <div class="km"><b>{nl_getal(km, 1)}</b><span>kilometer<br>gelopen</span></div>
    <div class="tegels">{tegels_html}</div>
    <div class="duurzaam">
      <div><h3>{e(TEKST["duurzaam_kop"])}</h3><p>{e(TEKST["duurzaam"])}</p></div>
      <div class="co2"><b>{nl_getal(co2, 1)} kg</b><span>CO₂ bespaard ten opzichte van dezelfde afstand met de auto</span></div>
    </div>
    <p class="kleine">Indicatief: {nl_getal(k["stappen_per_km"])} stappen en {k["kcal_per_km"]} kcal per km, {nl_getal(k["co2_auto_per_km"], 2)} kg CO₂ per autokilometer, één auto per vier personen.</p>
    <a class="video" href="{e(video)}">
      <div class="poster" style="background-image:url('{e(poster)}')"><i>▶</i></div>
      <div><h3>{e(TEKST["video_kop"])}</h3><p>{e(TEKST["video"])}</p><u>Bekijk de video →</u></div>
    </a>
  </div>
  {voet(stad, naam, nr)}
</section>''')

    # 3. teamfoto('s) van de spelleider
    for f in fotos_spelleider:
        nr += 1
        bladen.append(f'''<section class="blad"><div class="binnen teamfoto">
    <div class="label">Teamfoto</div><h2>{e(naam)}</h2>
    <img src="{e(f)}" alt="Teamfoto {e(naam)}">
  </div>{voet(stad, naam, nr)}</section>''')

    # 4. foto's uit Loquiz, zes per blad
    for i in range(0, len(loquiz), 6):
        groep = loquiz[i:i + 6]
        nr += 1
        imgs = ''.join(f'<img src="{e(m["url"])}" alt="{e(m["bij"] or "Foto")}">' for m in groep)
        kop = (f'<div class="label">{e(TEKST["fotos_kop"])}</div><h2>Jullie foto\'s</h2>' if i == 0
               else '<div class="label">' + e(TEKST["fotos_kop"]) + '</div><div style="height:8mm"></div>')
        bladen.append(f'''<section class="blad"><div class="binnen">{kop}
    <div class="raster n{len(groep)}">{imgs}</div>
  </div>{voet(stad, naam, nr)}</section>''')

    # 5. info
    nr += 1
    steden = sorted(json.load(open(os.path.join(ROOT, 'src', 'data', 'locations.json'), encoding='utf-8')),
                    key=lambda l: l['name'])
    steden_html = ''.join(f'<div>{e(l["name"])}</div>' for l in steden)
    bladen.append(f'''<section class="blad info"><div class="binnen">
    <div class="label">The Hunt</div>
    <h2>{e(TEKST["info_kop"])}</h2>
    <p>{e(TEKST["info"])}</p>
    <a class="knop" href="{e(TEKST["review_url"])}">Laat een review achter</a>
    <div class="steden">{steden_html}</div>
  </div>
  <div class="contact">
    <img src="{e(logo)}" alt="The Hunt">
    <div><a href="{e(SITE["url"])}">{e(SITE["url"].replace("https://", ""))}</a><br>
      <a href="mailto:{e(SITE["email"])}">{e(SITE["email"])}</a><br>
      <a href="tel:{e(SITE["phone"])}">{e(SITE["phone_display"])}</a></div>
  </div>
  {voet(stad, naam, nr)}
</section>''')

    return f'''<!doctype html>
<html lang="nl"><head><meta charset="utf-8">
<title>The Hunt{" " + e(stad) if stad else ""} · {e(naam)}</title>
<style>{css()}</style></head>
<body>
{chr(10).join(bladen)}
</body></html>
'''


# ---------------------------------------------------------------- PDF

def browser(opgegeven=None):
    kandidaten = [opgegeven] if opgegeven else []
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
        cmd = [exe, '--headless=new', '--disable-gpu', '--no-sandbox', '--no-first-run', '--allow-file-access-from-files', '--no-pdf-header-footer', '--print-to-pdf-no-header',
               '--virtual-time-budget=20000', f'--print-to-pdf={pdf_pad}', uri(html_pad)]
        if os.name == 'nt':  # los profiel, zodat een geopende Edge/Chrome niet in de weg zit
            cmd.insert(1, f'--user-data-dir={profiel}')
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
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

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--game', default=STANDAARD_GAME)
    ap.add_argument('--scope', default=STANDAARD_SCOPE)
    ap.add_argument('--team', action='append', help='alleen dit team (mag vaker)')
    ap.add_argument('--stad', help='plaatsnaam op de voorkant (standaard uit de gametitel; "" = zonder stad)')
    ap.add_argument('--video', default=STANDAARD_VIDEO, help='link naar de video')
    ap.add_argument('--teamfotos', help='map met teamfoto\'s (standaard tools/loquiz/teamfotos/<game>)')
    ap.add_argument('--uit', help='uitvoermap (standaard tools/loquiz/uitvoer/<game>/boekjes)')
    ap.add_argument('--browser', help='pad naar Edge of Chrome voor de PDF')
    ap.add_argument('--geen-pdf', action='store_true', help='alleen HTML maken')
    ap.add_argument('--demo', action='store_true')
    a = ap.parse_args()

    game, teams, per_team, _, _ = ophalen(a.game, a.scope, a.demo)
    if a.demo:
        demo_media(per_team)
    sleutel = 'demo' if a.demo else a.game
    stad = a.stad if a.stad is not None else stad_uit(game.get('title') or game.get('name'))
    fotomap = a.teamfotos or os.path.join(HIER, 'teamfotos', sleutel)
    os.makedirs(fotomap, exist_ok=True)
    uit = a.uit or os.path.join(HIER, 'uitvoer', sleutel, 'boekjes')
    os.makedirs(uit, exist_ok=True)

    if a.team:
        gezocht = {slug(t) for t in a.team}
        teams = [t for t in teams if slug(t.get('name')) in gezocht]
        if not teams:
            sys.exit('Geen team gevonden met die naam.')

    exe = None if a.geen_pdf else browser(a.browser)
    if not a.geen_pdf and not exe:
        print('Geen Edge of Chrome gevonden: alleen HTML. Open die en kies Afdrukken > Opslaan als PDF.')

    zonder_teamfoto = []
    for t in teams:
        naam = t.get('name') or 'team'
        eigen = teamfotos(fotomap, t)
        if not eigen:
            zonder_teamfoto.append(naam)
        html_pad = os.path.join(uit, slug(naam) + '.html')
        with open(html_pad, 'w', encoding='utf-8') as fh:
            fh.write(boekje(game, t, per_team.get(str(t.get('id')), []), eigen, stad, a.video))
        regel = f'{naam}: {len(per_team.get(str(t.get("id")), []))} Loquiz-foto\'s, {len(eigen)} teamfoto(\'s)'
        if exe:
            pdf = html_pad[:-5] + '.pdf'
            regel += ' -> PDF' if naar_pdf(exe, html_pad, pdf) else ' -> PDF mislukt, gebruik de HTML'
        print(regel)

    print(f'\nBoekjes in: {uit}')
    if zonder_teamfoto:
        print(f'Zonder teamfoto ({len(zonder_teamfoto)}): zet foto\'s in {fotomap}, met de teamnaam in de bestandsnaam.')


if __name__ == '__main__':
    main()
