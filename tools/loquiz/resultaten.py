"""Resultatenpagina per team uit de Loquiz API v3 (teams, score en foto's).

Haalt voor één game de teams en de media op en schrijft een losse HTML-pagina met per team de score en de foto's.

    python tools/loquiz/resultaten.py                      # game FK9SCMLMAJ, scope ADHOC
    python tools/loquiz/resultaten.py --game ABC123 --scope ADHOC,EVENT
    python tools/loquiz/resultaten.py --bewaar-json        # ook de ruwe API-antwoorden opslaan (handig bij twijfel)
    python tools/loquiz/resultaten.py --demo               # voorbeeldpagina zonder API, om de opmaak te bekijken

De API-key staat in .env in de hoofdmap van het project (LOQUIZ_API_KEY=ApiKey-v1 ...). .env staat in .gitignore.
De pagina komt in tools/loquiz/uitvoer/<game>/index.html. Die map staat ook in .gitignore: er staan foto's van
deelnemers in, dus nooit in docs/ (de publieke website) zetten.

Alleen standaard-Python nodig. API-documentatie: https://api.loquiz.com/v3/docs
"""
import argparse
import html
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

API = 'https://api.loquiz.com/v3'
HIER = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HIER))
STANDAARD_GAME = 'FK9SCMLMAJ'
STANDAARD_SCOPE = 'ADHOC'
PER_PAGINA = 100  # maximum van de Loquiz API

# Huisstijl badassgames.nl. Pas hier de kleuren, het lettertype en het logo aan.
HUISSTIJL = {
    'merk': 'Badass Games',
    'logo': '',               # URL of pad naar het logo; leeg = merknaam als tekst
    'achtergrond': '#0b0b0c',
    'vlak': '#17171a',
    'lijn': '#2a2a2f',
    'tekst': '#f4f4f5',
    'gedempt': '#a1a1aa',
    'accent': '#ff2e4d',
    'accent_tekst': '#0b0b0c',
    'letter': "'Bebas Neue','Oswald','Impact','Arial Narrow Bold',sans-serif",
    'broodtekst': "system-ui,-apple-system,'Segoe UI',Roboto,sans-serif",
}


# ---------------------------------------------------------------- API

def lees_key():
    key = os.environ.get('LOQUIZ_API_KEY', '').strip()
    pad = os.path.join(ROOT, '.env')
    if not key and os.path.exists(pad):
        for regel in open(pad, encoding='utf-8-sig'):
            regel = regel.strip()
            if regel.startswith('LOQUIZ_API_KEY='):
                key = regel.split('=', 1)[1].strip().strip('"').strip("'")
    if not key:
        sys.exit('Geen LOQUIZ_API_KEY gevonden. Zet in .env in de hoofdmap: LOQUIZ_API_KEY=ApiKey-v1 ...')
    # Loquiz verwacht de hele header "ApiKey-v1 <sleutel>"; plak het voorvoegsel erbij als het ontbreekt
    return key if key.lower().startswith('apikey') else 'ApiKey-v1 ' + key


def haal(pad, key, **params):
    params = {k: v for k, v in params.items() if v not in (None, '')}
    url = API + pad + ('?' + urllib.parse.urlencode(params) if params else '')
    req = urllib.request.Request(url, headers={'Authorization': key, 'Accept': 'application/json',
                                               'User-Agent': 'loquiz-resultaten/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        tekst = e.read().decode('utf-8', 'replace')[:300]
        if e.code in (401, 403):
            sys.exit(f'Loquiz weigert de API-key ({e.code}). Controleer LOQUIZ_API_KEY in .env. {tekst}')
        if e.code == 404:
            sys.exit(f'Niet gevonden: {pad} (klopt het game-ID?). {tekst}')
        sys.exit(f'Loquiz API gaf fout {e.code} op {pad}: {tekst}')
    except urllib.error.URLError as e:
        sys.exit(f'Kan api.loquiz.com niet bereiken: {e.reason}')


def lijst(antwoord):
    if isinstance(antwoord, list):
        return antwoord
    for k in ('items', 'data', 'results', 'media', 'teams'):
        if isinstance(antwoord.get(k), list):
            return antwoord[k]
    return []


def alles(pad, key, **params):
    """Haalt alle pagina's van een lijst op (skip/limit)."""
    uit, skip, ruw = [], 0, []
    while True:
        antwoord = haal(pad, key, skip=skip, limit=PER_PAGINA, **params)
        ruw.append(antwoord)
        items = lijst(antwoord)
        uit += items
        totaal = antwoord.get('total') if isinstance(antwoord, dict) else None
        if len(items) < PER_PAGINA or (totaal is not None and len(uit) >= totaal):
            return uit, ruw
        skip += PER_PAGINA


# ---------------------------------------------------------------- media koppelen aan teams

def team_van(m):
    for k in ('teamId', 'team_id', 'team'):
        v = m.get(k)
        if isinstance(v, dict):
            v = v.get('id') or v.get('_id')
        if v:
            return str(v)
    return None


def eerste_url(m, sleutels):
    for k in sleutels:
        v = m.get(k)
        if isinstance(v, str) and v.startswith(('http://', 'https://', '//')):
            return v
        if isinstance(v, dict):
            u = eerste_url(v, ('url', 'src', 'href', 'original', 'large', 'medium'))
            if u:
                return u
    return None


def foto(m):
    url = eerste_url(m, ('url', 'mediaUrl', 'fileUrl', 'originalUrl', 'src', 'file', 'original', 'media'))
    if not url:
        return None
    duim = eerste_url(m, ('thumbnailUrl', 'thumbUrl', 'thumbnail', 'thumb', 'previewUrl', 'preview')) or url
    soort = ' '.join(str(m.get(k, '')) for k in ('type', 'mediaType', 'mimeType', 'contentType')).lower()
    pad = urllib.parse.urlparse(url).path.lower()
    video = 'video' in soort or pad.endswith(('.mp4', '.mov', '.webm', '.m4v'))
    audio = 'audio' in soort or pad.endswith(('.mp3', '.m4a', '.aac', '.wav', '.ogg'))
    return {'url': url, 'duim': duim, 'video': video, 'audio': audio,
            'bij': m.get('taskTitle') or m.get('questionTitle') or m.get('title') or m.get('caption') or ''}


# ---------------------------------------------------------------- HTML

def e(s):
    return html.escape(str(s if s is not None else ''), quote=True)


def getal(v):
    try:
        f = float(v)
        return str(int(f)) if f == int(f) else f'{f:.1f}'.replace('.', ',')
    except (TypeError, ValueError):
        return '0'


def team_html(rang, t, media):
    kleur = t.get('color') or HUISSTIJL['accent']
    leden = t.get('members')
    if isinstance(leden, list):
        leden = ', '.join(str(x.get('name', x) if isinstance(x, dict) else x) for x in leden)
    feiten = []
    if t.get('correctAnswers') is not None:
        feiten.append(f'<span><b>{e(t["correctAnswers"])}</b> goed</span>')
    if t.get('incorrectAnswers') is not None:
        feiten.append(f'<span><b>{e(t["incorrectAnswers"])}</b> fout</span>')
    if t.get('odometer'):
        feiten.append(f'<span><b>{getal(t["odometer"])}</b> km</span>')
    feiten.append('<span class="ok">uitgespeeld</span>' if t.get('isFinished') else '<span>niet uitgespeeld</span>')

    tegels = []
    for m in media:
        bij = f' title="{e(m["bij"])}"' if m['bij'] else ''
        if m['video']:
            tegels.append(f'<a class="tegel" href="{e(m["url"])}" target="_blank" rel="noopener"{bij}>'
                          f'<video src="{e(m["url"])}#t=0.1" preload="metadata" muted playsinline></video><i>▶</i></a>')
        elif m['audio']:
            tegels.append(f'<div class="tegel geluid"{bij}><audio src="{e(m["url"])}" controls preload="none"></audio></div>')
        else:
            tegels.append(f'<a class="tegel" href="{e(m["url"])}" target="_blank" rel="noopener"{bij}>'
                          f'<img src="{e(m["duim"])}" alt="{e(m["bij"] or "Foto van " + str(t.get("name", "team")))}" loading="lazy"></a>')
    fotos = (f'<div class="fotos">{"".join(tegels)}</div>' if tegels
             else '<p class="leeg">Geen foto\'s van dit team.</p>')
    podium = ' podium p' + str(rang) if rang <= 3 else ''
    return f'''<article class="team{podium}" style="--team:{e(kleur)}">
  <header>
    <div class="rang">#{rang}</div>
    <div class="naam"><h2>{e(t.get("name") or "Naamloos team")}</h2>{f'<p>{e(leden)}</p>' if leden else ''}</div>
    <div class="score"><b>{getal(t.get("totalScore"))}</b><span>punten</span></div>
  </header>
  <div class="feiten">{"".join(feiten)}<span>{len(media)} foto{"" if len(media) == 1 else "'s"}</span></div>
  {fotos}
</article>'''


def pagina(game, teams, media_per_team, scope):
    h = HUISSTIJL
    titel = game.get('title') or game.get('name') or game.get('id') or 'Resultaten'
    logo = (f'<img src="{e(h["logo"])}" alt="{e(h["merk"])}" class="logo">' if h['logo']
            else f'<span class="merk">{e(h["merk"])}</span>')
    kaarten = '\n'.join(team_html(i + 1, t, media_per_team.get(str(t.get('id')), [])) for i, t in enumerate(teams))
    if not teams:
        kaarten = '<p class="leeg">Nog geen teams in deze scope.</p>'
    totaal_fotos = sum(len(v) for v in media_per_team.values())
    nu = datetime.now().strftime('%d-%m-%Y %H:%M')
    return f'''<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>{e(titel)} · resultaten</title>
<style>
:root{{--bg:{h["achtergrond"]};--vlak:{h["vlak"]};--lijn:{h["lijn"]};--tekst:{h["tekst"]};--gedempt:{h["gedempt"]};
  --accent:{h["accent"]};--accent-tekst:{h["accent_tekst"]};--kop:{h["letter"]};--sans:{h["broodtekst"]}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--tekst);font:400 1rem/1.5 var(--sans)}}
.wrap{{max-width:1100px;margin:0 auto;padding:0 16px}}
.top{{border-bottom:1px solid var(--lijn);padding:18px 0}}
.top .wrap{{display:flex;align-items:center;justify-content:space-between;gap:16px}}
.merk{{font:400 1.6rem/1 var(--kop);letter-spacing:.04em;text-transform:uppercase}}
.logo{{height:40px;width:auto}}
.tag{{font-size:.8rem;color:var(--gedempt);text-transform:uppercase;letter-spacing:.12em}}
.hero{{padding:48px 0 28px}}
.hero .label{{display:inline-block;background:var(--accent);color:var(--accent-tekst);font-weight:700;font-size:.75rem;
  letter-spacing:.14em;text-transform:uppercase;padding:4px 10px;border-radius:3px}}
h1{{font:400 clamp(2.6rem,8vw,5.2rem)/.95 var(--kop);text-transform:uppercase;margin:14px 0 10px;letter-spacing:.01em}}
.hero p{{color:var(--gedempt);margin:0}}
.teams{{display:grid;gap:18px;padding-bottom:56px}}
.team{{background:var(--vlak);border:1px solid var(--lijn);border-left:6px solid var(--team);border-radius:8px;padding:18px}}
.team header{{display:grid;grid-template-columns:auto 1fr auto;gap:16px;align-items:center}}
.rang{{font:400 2.4rem/1 var(--kop);color:var(--gedempt);min-width:2.2ch}}
.podium .rang{{color:var(--accent)}}
.p1{{border-color:var(--accent);border-left-color:var(--team);box-shadow:0 0 0 1px var(--accent)}}
.naam h2{{font:400 clamp(1.5rem,4vw,2rem)/1.05 var(--kop);text-transform:uppercase;margin:0;letter-spacing:.02em;overflow-wrap:anywhere}}
.naam p{{margin:4px 0 0;color:var(--gedempt);font-size:.9rem}}
.score{{text-align:right}}
.score b{{display:block;font:400 clamp(2.2rem,6vw,3.2rem)/1 var(--kop);color:var(--accent);font-variant-numeric:tabular-nums}}
.score span{{font-size:.72rem;color:var(--gedempt);text-transform:uppercase;letter-spacing:.14em}}
.feiten{{display:flex;flex-wrap:wrap;gap:6px 16px;margin:12px 0 14px;font-size:.88rem;color:var(--gedempt)}}
.feiten b{{color:var(--tekst)}}
.feiten .ok{{color:var(--accent)}}
.fotos{{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:8px}}
.tegel{{position:relative;display:block;aspect-ratio:1;border-radius:5px;overflow:hidden;background:#000}}
.tegel img,.tegel video{{color:transparent;width:100%;height:100%;object-fit:cover;display:block;transition:transform .2s}}
.tegel:hover img,.tegel:hover video{{transform:scale(1.05)}}
.tegel i{{position:absolute;inset:auto 8px 8px auto;background:var(--accent);color:var(--accent-tekst);font-style:normal;
  width:28px;height:28px;border-radius:50%;display:grid;place-items:center;font-size:.8rem}}
.geluid{{aspect-ratio:auto;display:flex;align-items:center;padding:8px;grid-column:span 2}}
.geluid audio{{width:100%}}
.leeg{{color:var(--gedempt);margin:0;font-size:.9rem}}
footer{{border-top:1px solid var(--lijn);padding:18px 0 28px;color:var(--gedempt);font-size:.8rem}}
@media (max-width:560px){{.team header{{grid-template-columns:auto 1fr}}.score{{grid-column:1/-1;text-align:left;display:flex;align-items:baseline;gap:8px}}
  .fotos{{grid-template-columns:repeat(3,1fr)}}}}
</style>
</head>
<body>
<div class="top"><div class="wrap">{logo}<span class="tag">Uitslag</span></div></div>
<main class="wrap">
  <section class="hero">
    <span class="label">Resultaten</span>
    <h1>{e(titel)}</h1>
    <p>{len(teams)} team{"" if len(teams) == 1 else "s"} · {totaal_fotos} foto{"" if totaal_fotos == 1 else "'s"} · scope {e(scope or "alle")}</p>
  </section>
  <section class="teams">
{kaarten}
  </section>
</main>
<footer><div class="wrap">Bijgewerkt {nu} · game {e(game.get("id", ""))}</div></footer>
</body>
</html>
'''


# ---------------------------------------------------------------- demo

def demo():
    game = {'id': 'DEMO', 'title': 'The Hunt Utrecht'}
    teams, media = [], []
    namen = [('De Vluchtelingen', '#ff2e4d', 1840), ('Team Oranje', '#f29222', 1520), ('Snelle Jelles', '#22c55e', 1380),
             ('Hunters Hunters', '#3b82f6', 990), ('Laatste Kans', '#a855f7', 420)]
    for i, (n, c, s) in enumerate(namen):
        teams.append({'id': f't{i}', 'name': n, 'color': c, 'totalScore': s, 'correctAnswers': 14 - i * 2,
                      'incorrectAnswers': i + 1, 'isFinished': i < 4, 'odometer': 5.4 - i * .6,
                      'members': ['Sanne', 'Joris', 'Fleur', 'Bas'][: 4 - i % 3]})
        for j in range(max(0, 6 - i)):
            media.append({'teamId': f't{i}', 'type': 'photo', 'url': f'https://picsum.photos/seed/hunt{i}{j}/900/900',
                          'thumbnailUrl': f'https://picsum.photos/seed/hunt{i}{j}/300/300', 'taskTitle': f'Opdracht {j + 1}'})
    return game, teams, media


# ---------------------------------------------------------------- hoofdprogramma

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--game', default=STANDAARD_GAME)
    ap.add_argument('--scope', default=STANDAARD_SCOPE, help='een of meer scopes, komma-gescheiden; leeg = alle')
    ap.add_argument('--uit', help='map voor de pagina (standaard tools/loquiz/uitvoer/<game>)')
    ap.add_argument('--bewaar-json', action='store_true', help='ruwe API-antwoorden ook opslaan')
    ap.add_argument('--demo', action='store_true', help='voorbeeldpagina zonder API')
    a = ap.parse_args()

    ruw = {}
    if a.demo:
        game, teams, media = demo()
        a.scope = 'DEMO'
    else:
        key = lees_key()
        game = haal(f'/games/{a.game}', key)
        teams, ruw['teams'] = alles(f'/results/{a.game}/teams', key, scope=a.scope, sort='-totalScore')
        media, ruw['media'] = alles(f'/results/{a.game}/media', key, scope=a.scope)
        ruw['game'] = game
    game.setdefault('id', a.game)

    teams.sort(key=lambda t: float(t.get('totalScore') or 0), reverse=True)
    team_ids = {str(t.get('id')) for t in teams}
    per_team, los = {}, 0
    for m in media:
        f, tid = foto(m), team_van(m)
        if not f:
            continue
        if tid in team_ids:
            per_team.setdefault(tid, []).append(f)
        else:
            los += 1

    uit = a.uit or os.path.join(HIER, 'uitvoer', 'demo' if a.demo else a.game)
    os.makedirs(uit, exist_ok=True)
    pad = os.path.join(uit, 'index.html')
    with open(pad, 'w', encoding='utf-8') as fh:
        fh.write(pagina(game, teams, per_team, a.scope))
    if a.bewaar_json and ruw:
        with open(os.path.join(uit, 'api.json'), 'w', encoding='utf-8') as fh:
            json.dump(ruw, fh, ensure_ascii=False, indent=2)

    n = sum(len(v) for v in per_team.values())
    print(f'{len(teams)} teams, {n} media gekoppeld aan teams'
          + (f', {los} media zonder (bekend) team overgeslagen' if los else '') + f'\nPagina: {pad}')
    if media and not n:
        print('Let op: er is wel media opgehaald maar niets kon aan een team gekoppeld worden. '
              'Draai opnieuw met --bewaar-json en bekijk api.json.')


if __name__ == '__main__':
    main()
