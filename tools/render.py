"""Templates voor de nieuwe site. Alleen standaard-Python; wordt aangeroepen door tools/build.py."""
import html
import json
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = json.load(open(os.path.join(ROOT, 'src', 'data', 'site.json'), encoding='utf-8'))
LOCS = json.load(open(os.path.join(ROOT, 'src', 'data', 'locations.json'), encoding='utf-8'))
PROVINCES = ['Groningen', 'Friesland', 'Drenthe', 'Overijssel', 'Flevoland', 'Gelderland', 'Utrecht',
             'Noord-Holland', 'Zuid-Holland', 'Zeeland', 'Noord-Brabant', 'Limburg']
P = SITE['prices']
esc = lambda s: html.escape(str(s), quote=True)

ICON_MENU = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M3 6h18M3 12h18M3 18h18"/></svg>'
ICON_ARROW = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>'


def content(kind, slug):
    return json.load(open(os.path.join(ROOT, 'src', 'content', kind, slug + '.json'), encoding='utf-8'))


def coords(loc):
    return '%.4f° N · %.4f° O' % (loc['lat'], loc['lng'])


def jsonld(data):
    return '<script type="application/ld+json">%s</script>' % json.dumps(data, ensure_ascii=False).replace('</', '<\\/')


# ---------- basis ----------

def page(*, path, title, description, body, og_image=None, robots=None, schema=(), head_extra='', active=None):
    url = SITE['url'] + path
    img = SITE['url'] + (og_image or SITE['og_image'])
    nav = ''.join('<a href="%s"%s>%s</a>' % (h, ' aria-current="page"' if h == active else '', t) for t, h in SITE['nav'])
    org = {'@context': 'https://schema.org', '@type': 'Organization', '@id': SITE['url'] + '/#organization',
           'name': SITE['name'], 'url': SITE['url'], 'email': SITE['email'], 'telephone': SITE['phone'],
           'logo': SITE['url'] + SITE['logo'],
           'address': {'@type': 'PostalAddress', 'streetAddress': 'Nering 10-1', 'postalCode': '8355 DK',
                       'addressLocality': 'Giethoorn', 'addressCountry': 'NL'}}
    return f'''<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<meta name="robots" content="{robots or 'index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1'}">
<link rel="canonical" href="{url}">
<meta property="og:locale" content="nl_NL">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{SITE['name']}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{img}">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#141e29">
<link rel="icon" href="/assets/uploads/2025/05/cropped-escapegamethehunt-512-32x32.png" sizes="32x32">
<link rel="icon" href="/assets/uploads/2025/05/cropped-escapegamethehunt-512-192x192.png" sizes="192x192">
<link rel="apple-touch-icon" href="/assets/uploads/2025/05/cropped-escapegamethehunt-512-180x180.png">
<link rel="preload" href="/assets/fonts/S6u9w4BMUTPHh6UVSwiPGQ.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/assets/css/style.css">
{head_extra}{jsonld(org)}
{''.join(jsonld(s) for s in schema)}
</head>
<body>
<a class="skip" href="#inhoud">Naar de inhoud</a>
<header class="site-header">
<div class="wrap">
<a class="brand" href="/"><img src="{SITE['logo']}" alt="" width="40" height="48"><span>Escape Game<br>The Hunt<small>Outdoor escape room</small></span></a>
<button class="nav-toggle" type="button" aria-controls="nav" aria-expanded="false" aria-label="Menu">{ICON_MENU}</button>
<nav class="nav" id="nav" aria-label="Hoofdmenu">{nav}<a class="btn btn-signal" href="#boeken">Boek nu</a></nav>
</div>
</header>
<main id="inhoud">
{body}
</main>
{footer()}
<a class="btn btn-signal mobile-cta" href="#boeken">Boek The Hunt {ICON_ARROW}</a>
<script src="/assets/js/main.js" defer></script>
</body>
</html>
'''


def footer():
    cities = ''.join('<li><a href="%s">%s</a></li>' % (l['url'], l['name']) for l in sorted(LOCS, key=lambda l: l['name']))
    links = ''.join('<li><a href="%s">%s</a></li>' % (h, t) for t, h in SITE['footer_links'])
    return f'''<footer class="site-footer">
<div class="wrap">
<div class="footer-grid">
<div class="stack">
<a class="brand" href="/"><img src="{SITE['logo']}" alt="" width="40" height="48"><span>Escape Game<br>The Hunt</span></a>
<p>De outdoor escape room waarin jullie door de stad vluchten voor de Hunters. Te spelen in heel Nederland: overal waar we een speelveld kunnen maken. Vanaf 8 personen.</p>
<div class="contact-lines"><a href="tel:{SITE['phone']}">{SITE['phone_display']}</a><a href="mailto:{SITE['email']}">{SITE['email']}</a></div>
</div>
<div><h2>Speel The Hunt in</h2><ul class="footer-cities">{cities}</ul></div>
<div><h2>Meer</h2><ul class="footer-links">{links}</ul></div>
</div>
<div class="footer-bottom"><span>© 2020–2026 {SITE['name']} is onderdeel van {SITE['company']} · KvK {SITE['kvk']}</span><span>{SITE['address']}</span></div>
</div>
</footer>'''


# ---------- onderdelen ----------

def facts(items):
    return '<div class="facts">%s</div>' % ''.join('<div class="fact"><b>%s</b><span>%s</span></div>' % i for i in items)


def clock(start_place=None, city=None):
    where = ('bij <strong>%s</strong>' % esc(start_place)) if start_place else ('op de startlocatie in %s' % esc(city) if city else 'op de startlocatie')
    steps = [
        ('-00:15', 'Ontvangst', f'Jullie spelleider wacht {where}, legt het spel uit en verdeelt de groep in teams van ongeveer zes personen.', ''),
        ('00:00', 'Start', 'Elk team krijgt een gametas met zes escape-puzzels en toegang tot de GameApp. Jullie hebben 10 minuten voorsprong.', ''),
        ('00:10', 'De jacht begint', 'De Hunters komen in actie. Elke 10 minuten krijgen zij jullie locatie door, en dan gaan ze op jacht.', ' class="hot"'),
        ('90:00', 'Extractiepunt', 'Elk goed antwoord levert een deel van de GPS-code op. Halen jullie het extractiepunt voordat de tijd op is, zonder gepakt te worden?', ''),
    ]
    lis = ''.join(f'<li{h}><time>{t}</time><h3>{a}</h3><p>{b}</p></li>' for t, a, b, h in steps)
    return f'<ol class="clock">{lis}</ol>'


def pricing(city=None):
    rows = ''.join('<tr><td>%d personen</td><td>%s</td></tr>' % (n, p) for n, p in P['examples'])
    return f'''<div class="pricing">
<div class="price-card">
<span class="label">Prijs{' in ' + esc(city) if city else ''}</span>
<div class="amount tnum">€{P['base']}<small>t/m {P['base_max_people']} personen</small></div>
<div class="price-rows">
<div><span>Vanaf {P['base_max_people'] + 1} personen</span><b>€{P['per_person']} p.p.</b></div>
<div><span>Opdrachten op maat voor jullie groep</span><b>+ €{P['custom']}</b></div>
<div><span>Groepsgrootte</span><b>{P['min_people']} tot ±{P['max_people']} personen</b></div>
</div>
<p class="price-note">Alle prijzen zijn exclusief 21% btw. Voor groepen boven de {P['max_people']} maken we een wisselprogramma met onze andere spellen.</p>
</div>
<div class="examples">
<span class="label">Rekenvoorbeelden</span>
<table><thead><tr><th>Groep</th><th>Totaal ex. btw</th></tr></thead><tbody>{rows}</tbody></table>
<a class="btn btn-line" href="/escape-game-the-hunt-prijzen/">Alles over prijzen {ICON_ARROW}</a>
</div>
</div>'''


def faq_block(items):
    det = ''.join(f'<details><summary>{esc(q)}</summary><div class="answer">{a}</div></details>' for q, a in items)
    return f'<div class="faq">{det}</div>'


def faq_schema(items):
    import re
    strip = lambda s: re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', s))).strip()
    return {'@context': 'https://schema.org', '@type': 'FAQPage', 'mainEntity': [
        {'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': strip(a)}} for q, a in items]}


def project(lat, lng):
    return 12 + (lng - 3.45) * math.cos(math.radians(52.2)) * 118, 14 + (53.45 - lat) * 118


# Vereenvoudigde omtrek van Nederland (breedte, lengte), met IJsselmeer/Markermeer en de Waddeneilanden.
NL_LAND = [(52.96, 4.76), (52.94, 5.04), (53.09, 5.40), (53.17, 5.41), (53.35, 5.62), (53.40, 5.95), (53.41, 6.20),
           (53.43, 6.55), (53.45, 6.83), (53.33, 6.93), (53.24, 7.00), (53.18, 7.21), (52.95, 7.05), (52.85, 7.07),
           (52.65, 7.05), (52.64, 6.72), (52.47, 6.70), (52.45, 7.03), (52.25, 7.05), (52.22, 6.98), (52.07, 6.83),
           (51.97, 6.83), (51.84, 6.40), (51.85, 6.05), (51.75, 6.00), (51.55, 6.20), (51.36, 6.22), (51.17, 6.08),
           (51.05, 5.98), (50.95, 6.05), (50.76, 6.02), (50.75, 5.70), (50.80, 5.63), (50.92, 5.65), (51.02, 5.76), (51.15, 5.85), (51.20, 5.50),
           (51.30, 5.25), (51.43, 5.05), (51.45, 4.75), (51.48, 4.40), (51.35, 4.30), (51.30, 4.00), (51.23, 3.80),
           (51.27, 3.55), (51.37, 3.37), (51.39, 3.55), (51.37, 3.83), (51.36, 3.95), (51.38, 4.15), (51.41, 4.22),
           (51.43, 4.20), (51.44, 4.00), (51.45, 3.66), (51.48, 3.45), (51.58, 3.48), (51.62, 3.70), (51.70, 3.85),
           (51.83, 3.95), (51.98, 4.10),
           (52.10, 4.26), (52.25, 4.42), (52.46, 4.56), (52.70, 4.63)]
NL_WATER = [(52.94, 5.04), (53.09, 5.40), (52.84, 5.71), (52.66, 5.60), (52.52, 5.47), (52.37, 5.21), (52.33, 5.07),
            (52.38, 4.97), (52.51, 5.05), (52.64, 5.07), (52.70, 5.29), (52.77, 5.10)]
NL_ISLANDS = [[(53.00, 4.72), (53.18, 4.85), (53.18, 4.91), (53.02, 4.80)],
              [(53.24, 4.93), (53.31, 5.10), (53.29, 5.12), (53.22, 4.96)],
              [(53.36, 5.12), (53.45, 5.52), (53.42, 5.56), (53.34, 5.18)],
              [(53.44, 5.62), (53.47, 5.93), (53.44, 5.95), (53.42, 5.66)],
              [(53.48, 6.10), (53.50, 6.30), (53.47, 6.31), (53.46, 6.12)]]


def poly(points):
    return ' '.join('%.1f,%.1f' % project(lat, lng) for lat, lng in points)


# Vaste labels voor grote steden (dx, dy, anker); de overige namen verschijnen bij aanwijzen of focus.
MAJOR = {'groningen': (4, -10, 'start'), 'leeuwarden': (0, -11, 'middle'), 'amsterdam': (-9, 4, 'end'),
         'rotterdam': (-9, 4, 'end'), 'den-haag': (-9, 4, 'end'), 'utrecht': (-2, 16, 'end'), 'zwolle': (9, 4, 'start'),
         'eindhoven': (9, 4, 'start'), 'maastricht': (9, 4, 'start'), 'enschede': (0, 17, 'middle'), 'arnhem': (9, 4, 'start'),
         'tilburg': (-9, 4, 'end'), 'amersfoort': (9, 4, 'start')}


def nl_map(current=None):
    parts = [f'<polygon class="land" points="{poly(NL_LAND)}"/>', f'<polygon class="water" points="{poly(NL_WATER)}"/>']
    parts += [f'<polygon class="land" points="{poly(i)}"/>' for i in NL_ISLANDS]
    for lat in (51, 52, 53):
        _, y = project(lat, 4)
        parts.append(f'<line class="gridline" x1="0" x2="300" y1="{y:.1f}" y2="{y:.1f}"/><text class="grid-label" x="297" y="{y - 4:.1f}" text-anchor="end">{lat}°N</text>')
    for lng in (4, 5, 6, 7):
        x, _ = project(52, lng)
        parts.append(f'<line class="gridline" y1="0" y2="336" x1="{x:.1f}" x2="{x:.1f}"/>')
    for l in sorted(LOCS, key=lambda l: l['slug'] in MAJOR or l['slug'] == current):
        x, y = project(l['lat'], l['lng'])
        is_cur = current == l['slug']
        if l['slug'] in MAJOR and not current:
            dx, dy, anchor = MAJOR[l['slug']]
            lbl = 'lbl'
        else:
            dx, dy, anchor = (-9, 4, 'end') if x > 190 else (9, 4, 'start')
            lbl = 'lbl' if is_cur else 'lbl hover'
        cls = ' class="active"' if is_cur else ''
        parts.append(f'<a href="{l["url"]}"{cls} aria-label="Escape room {esc(l["name"])}"><circle class="halo" cx="{x:.1f}" cy="{y:.1f}" r="6"/>'
                     f'<circle class="dot" cx="{x:.1f}" cy="{y:.1f}" r="{5.5 if is_cur else 4}"/>'
                     f'<text class="{lbl}" x="{x + dx:.1f}" y="{y + dy:.1f}" text-anchor="{anchor}">{esc(l["name"])}</text></a>')
    return f'''<figure class="map" style="margin:0">
<svg viewBox="0 0 300 336" role="img" aria-label="Kaart van Nederland met onze vaste speelsteden">{''.join(parts)}</svg>
<figcaption class="map-caption"><span>Vaste speelsteden</span>{"" if current else "<span>Wijs een stip aan voor de stad</span>"}</figcaption>
</figure>'''


def province_list(exclude=None):
    out = []
    for prov in PROVINCES:
        items = [l for l in LOCS if l['province'] == prov and l['slug'] != exclude]
        if items:
            lis = ''.join(f'<li><a href="{l["url"]}">{esc(l["name"])}</a></li>' for l in items)
            out.append(f'<div class="province"><h3>{prov}</h3><ul>{lis}</ul></div>')
    return '<div class="provinces">%s</div>' % ''.join(out)


def booking(city=None):
    opts = ''.join('<option%s>%s</option>' % (' selected' if city == l['name'] else '', esc(l['name']))
                   for l in sorted(LOCS, key=lambda l: l['name']))
    title = f'Boek The Hunt in {esc(city)}' if city else 'Boek The Hunt'
    return f'''<section class="section dark grid-bg" id="boeken" aria-labelledby="boeken-titel">
<div class="wrap booking">
<div class="stack">
<span class="label">Aanvraag · reactie binnen 1 werkdag</span>
<h2 id="boeken-titel">{title}</h2>
<p class="lede">Laat weten met hoeveel personen jullie komen en wanneer. Je krijgt een duidelijke offerte, zonder verplichtingen.</p>
<div class="contact-lines"><a href="tel:{SITE['phone']}">{SITE['phone_display']}</a><a href="mailto:{SITE['email']}">{SITE['email']}</a></div>
</div>
<form class="form" data-booking data-google="{esc(SITE['google_form_url'])}" action="{SITE['formsubmit']}" method="POST">
<input type="hidden" name="form" value="boeking">
<input type="hidden" name="_subject" value="Aanvraag The Hunt via escapegamethehunt.nl">
<input type="hidden" name="_template" value="table">
<input type="hidden" name="_next" value="{SITE['url']}/bedankt/">
<div class="field"><label for="f-naam">Naam</label><input id="f-naam" name="naam" autocomplete="name" required></div>
<fieldset class="field"><legend>Type aanvraag</legend><div class="choices"><label><input type="radio" name="type" value="Zakelijk" checked> Zakelijk</label><label><input type="radio" name="type" value="Particulier"> Particulier</label></div></fieldset>
<div class="field"><label for="f-mail">E-mailadres</label><input id="f-mail" type="email" name="email" autocomplete="email" required></div>
<div class="field"><label for="f-tel">Telefoonnummer</label><input id="f-tel" type="tel" name="telefoon" autocomplete="tel" required></div>
<div class="field"><label for="f-bedrijf">Bedrijfsnaam <span class="opt">(optioneel)</span></label><input id="f-bedrijf" name="bedrijf" autocomplete="organization"></div>
<div class="field"><label for="f-stad">Stad</label><select id="f-stad" name="stad" required><option value="">Kies een stad</option>{opts}<option>Andere plaats (vermeld hieronder)</option></select></div>
<div class="field"><label for="f-datum">Gewenste datum</label><input id="f-datum" type="date" name="datum" required></div>
<div class="field"><label for="f-tijd">Starttijd <span class="opt">(ongeveer)</span></label><input id="f-tijd" name="starttijd" placeholder="bijv. 15:00"></div>
<div class="field"><label for="f-aantal">Aantal personen</label><input id="f-aantal" type="number" name="personen" min="{P['min_people']}" inputmode="numeric" required></div>
<fieldset class="field"><legend>Soort Hunt</legend><div class="choices"><label><input type="radio" name="soort" value="Regulier" checked> Regulier</label><label><input type="radio" name="soort" value="Op maat (+€125)"> Op maat (+€{P['custom']})</label></div></fieldset>
<div class="field full"><label for="f-info">Overige informatie <span class="opt">(optioneel)</span></label><textarea id="f-info" name="bericht"></textarea></div>
<div class="hp" aria-hidden="true"><label for="f-web">Laat dit veld leeg</label><input id="f-web" name="_honey" tabindex="-1" autocomplete="off"></div>
<div class="full"><button class="btn btn-signal" type="submit">Vraag een offerte aan {ICON_ARROW}</button></div>
</form>
</div>
</section>'''


def nearest(loc, n=5):
    d = lambda l: math.hypot((l['lat'] - loc['lat']), (l['lng'] - loc['lng']) * math.cos(math.radians(52)))
    return sorted((l for l in LOCS if l['slug'] != loc['slug']), key=d)[:n]
