"""Uitgebreide horecalijst per stad voor de salespersoon.

Gebruik:  python tools/seo/horeca_verrijk.py groningen

1. Haalt via DataForSEO (Google Maps) restaurants, cafés, bars, lunchrooms en grand cafés rond de start.
2. Leest van elke zaak de eigen website (homepage + pagina's over groepen, arrangementen, zaal, contact, over ons).
3. Schrijft tools/seo/horeca/horeca-<stad>-uitgebreid.xlsx met kansscore, belscript-hint en lege kolommen voor sales.
"""
import base64, concurrent.futures as cf, html, json, math, os, re, sys, urllib.parse, urllib.request
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import FormulaRule

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUTDIR = os.path.join(HERE, 'horeca')
API = 'https://api.dataforseo.com/v3/serp/google/maps/live/advanced'
QUERIES = ['restaurant', 'café', 'bar', 'lunchroom', 'grand café']
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36'
SUB = re.compile(r'groep|arrangement|zaal|feest|besloten|private|event|partij|bedrijf|zakelijk|reserv|contact|over-ons|overons|about|team|wie-zijn', re.I)


# ---------------- Google Maps ----------------
def maps(auth, kw, lat, lon):
    body = json.dumps([{'keyword': kw, 'location_coordinate': f'{lat},{lon},17', 'language_code': 'nl', 'depth': 60}]).encode()
    req = urllib.request.Request(API, data=body, headers={'Authorization': 'Basic ' + auth, 'Content-Type': 'application/json'})
    r = json.load(urllib.request.urlopen(req, timeout=300))
    return (r['tasks'][0].get('result') or [{}])[0].get('items') or [], r.get('cost') or 0


def inside(lat, lon, poly):
    c = False
    for (a1, b1), (a2, b2) in zip(poly, poly[1:] + poly[:1]):
        if (b1 > lon) != (b2 > lon) and lat < (a2 - a1) * (lon - b1) / (b2 - b1) + a1:
            c = not c
    return c


def dist(a, b):
    return math.hypot((a[0] - b[0]) * 111000, (a[1] - b[1]) * 111000 * math.cos(math.radians(a[0])))


def open_at_17(wh):
    """Aantal dagen (ma-za) dat de zaak om 17:00 open is, volgens Google."""
    tt = (wh or {}).get('timetable') or {}
    n = 0
    for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']:
        for s in tt.get(day) or []:
            o, c = s.get('open') or {}, s.get('close') or {}
            om = o.get('hour', 0) * 60 + o.get('minute', 0)
            cm = c.get('hour', 0) * 60 + c.get('minute', 0)
            if cm <= om:
                cm += 24 * 60
            if om <= 17 * 60 < cm:
                n += 1
                break
    return n if tt else None


# ---------------- website ----------------
def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Language': 'nl,en;q=0.8'})
    with urllib.request.urlopen(req, timeout=15) as r:
        if 'html' not in (r.headers.get('Content-Type') or ''):
            return '', r.geturl()
        return r.read(1_500_000).decode(r.headers.get_content_charset() or 'utf-8', 'replace'), r.geturl()


def text_of(h):
    h = re.sub(r'(?is)<(script|style|noscript)[^>]*>.*?</\1>', ' ', h)
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', h)))


def crawl(url):
    out = {'pages': [], 'error': ''}
    if not url:
        out['error'] = 'geen website'; return out
    try:
        h, final = get(url)
    except Exception as e:
        out['error'] = f'niet bereikbaar ({type(e).__name__})'; return out
    out['pages'].append((final, h))
    base = urllib.parse.urlparse(final)
    links = []
    for href in re.findall(r'href=["\']([^"\'#]+)', h):
        u = urllib.parse.urljoin(final, href)
        p = urllib.parse.urlparse(u)
        if p.netloc.replace('www.', '') == base.netloc.replace('www.', '') and SUB.search(p.path) and u not in links:
            links.append(u)
    for u in links[:7]:
        try:
            out['pages'].append(get(u)[::-1][::-1] if False else (u, get(u)[0]))
        except Exception:
            pass
    return out


CAP = re.compile(r'(?:tot|max(?:imaal)?\.?|maximum|voor|ruimte voor|plek voor|plaats voor|capaciteit(?: van)?|t/m)\s*(?:wel\s*)?(\d{2,3})\s*(?:personen|pers\.?|gasten|mensen|people|guests|zitplaatsen|couverts)', re.I)
CAP2 = re.compile(r'(\d{2,3})\s*(?:personen|gasten|zitplaatsen|couverts)', re.I)
CITY = ''
ROLE = r'(?:eigenaar|eigenaresse|eigenaren|uitbater|bedrijfsleider|manager|gastheer|gastvrouw|chef-kok|eventmanager|event manager)'
NAME = r'([A-Z][a-zà-ü]+(?: (?:van|de|der|den|ten|ter|van der|van den))? [A-Z][a-zà-ü]+)'


def analyse(c):
    joined = ' '.join(text_of(h) for _, h in c['pages'])
    low = joined.lower()
    raw = ' '.join(h for _, h in c['pages'])
    r = {}
    grp_pages = [u for u, _ in c['pages'][1:] if re.search(r'groep|arrangement|feest|besloten|event|zakelijk|partij', u, re.I)]
    r['groepen'] = 'ja' if re.search(r'groepsarrangement|arrangement|groepsmenu|groepsdiner|met een groep|grote groep|groepen (?:zijn|tot|vanaf|welkom)|voor groepen', low) else 'nee'
    r['groepen_link'] = grp_pages[0] if grp_pages else ''
    r['zaal'] = 'ja' if re.search(r'besloten|zaal|private dining|afhuren|exclusief gebruik|bovenverdieping|serre|feestruimte|vergaderruimte', low) else 'nee'
    caps = [int(x) for x in CAP.findall(joined)] or [int(x) for x in CAP2.findall(joined)]
    caps = [x for x in caps if 10 <= x <= 600]
    r['capaciteit'] = max(caps) if caps else ''
    r['buffet'] = 'ja' if re.search(r'buffet|groepsmenu|shared dining|walking dinner|borrelplank|bittergarnituur|hapjesarrangement', low) else 'nee'
    r['activiteiten'] = 'ja' if re.search(r'escape ?room|workshop|bowlen|activiteit|kookworkshop|stadswandeling|rondvaart|teamuitje|bedrijfsuitje|vrijgezellen', low) else 'nee'
    r['terras'] = 'ja' if 'terras' in low else 'nee'
    mails = sorted(set(m.lower() for m in re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', raw) if not re.search(r'\.(png|jpg|jpeg|gif|webp|svg)$|sentry|wixpress|example|domain', m, re.I)))
    pref = [m for m in mails if re.match(r'(info|reserver|events?|groep|sales|contact|hallo|hello)', m)]
    local = [m for m in mails if CITY and CITY in m.split('@')[0]]
    others = [m for m in mails if not re.match(r'(amsterdam|rotterdam|utrecht|apeldoorn|zwolle|leeuwarden|groningen|eindhoven|arnhem|nijmegen|den-?haag|haarlem|tilburg|breda|maastricht|enschede|amersfoort|almere|deventer)@', m)]
    pref = [m for m in others if re.match(r'(info|reserver|events?|groep|sales|contact|hallo|hello)', m)]
    r['email'] = (local or pref or others or [''])[0]
    forms = [u for u, h in c['pages'] if re.search(r'contact|reserv', u, re.I) and '<form' in h.lower()]
    r['formulier'] = forms[0] if forms else ''
    names = []
    stop = {'Cadeaukaart', 'Vacatures', 'Vandaag', 'Nederland', 'Zuid', 'Noord', 'Oost', 'West', 'Doc', 'Drama', 'Nieuws', 'Engels', 'Aantal', 'Frivolo', 'Evento', 'Menu', 'Contact', 'Home', 'Reserveren', 'Groningen', 'Restaurant', 'Cafe', 'Café', 'De', 'Het', 'Een', 'Onze', 'Ons', 'Wij', 'Bij', 'Van', 'Voor', 'Met', 'Welkom', 'Ook', 'Als', 'Over', 'Deze', 'Dit', 'In', 'Op'}
    for pat in (NAME + r'[\s,(\-–|]{1,4}(?:onze |de |is )?(?i:' + ROLE + ')', '(?i:' + ROLE + r')[\s:,\-–|]{1,4}' + NAME):
        for m in re.finditer(pat, joined):
            nm = m.group(1)
            if any(w in stop for w in nm.split()):
                continue
            names.append(f'{nm} ({re.search(ROLE, m.group(0), re.I).group(0).lower()})')
    r['contactpersoon'] = '; '.join(dict.fromkeys(names[:2]))
    ig = re.findall(r'https?://(?:www\.)?instagram\.com/[A-Za-z0-9_.]+', raw)
    li = re.findall(r'https?://(?:[a-z]+\.)?linkedin\.com/company/[A-Za-z0-9_\-%]+', raw)
    r['instagram'] = ig[0] if ig else ''
    r['linkedin'] = li[0] if li else ''
    r['website_status'] = c['error'] or f'gelezen ({len(c["pages"])} pagina\'s)'
    return r


# ---------------- score ----------------
def kans(r):
    p = 0.0
    if r['groepen'] == 'ja': p += 1.5
    if r['zaal'] == 'ja': p += 1.0
    cap = r['capaciteit'] or 0
    if cap >= 40: p += 1.5
    elif cap >= 20: p += 1.0
    if r['buffet'] == 'ja': p += 0.5
    if r['activiteiten'] == 'ja': p += 0.5
    if (r['score'] or 0) >= 4.3: p += 0.5
    if (r['reviews'] or 0) >= 300: p += 0.5
    if r['in_speelveld'] == 'ja' or r['afstand'] <= 300: p += 0.5
    if (r['open17'] or 0) >= 4: p += 0.5
    # max 7,5 punten -> 1 t/m 5 sterren
    return 1 if p < 1.5 else 2 if p < 3 else 3 if p < 4.5 else 4 if p < 6 else 5, p


def hint(r):
    bits = []
    if r['groepen'] == 'ja' and r['capaciteit']:
        bits.append(f'Doet al groepen (tot {r["capaciteit"]} pers.): aanbieden als vaste afsluiter na The Hunt.')
    elif r['groepen'] == 'ja':
        bits.append('Doet al groepen/arrangementen: vragen tot hoeveel personen en aanbieden als afsluiter na The Hunt.')
    elif r['zaal'] == 'ja':
        bits.append('Heeft een zaal of besloten ruimte: interessant voor grote bedrijfsgroepen.')
    else:
        bits.append('Groepen niet zichtbaar op de site: eerst vragen of ze groepen aankunnen.')
    if r['activiteiten'] == 'ja':
        bits.append('Noemt al activiteiten/uitjes op de site, dus kent het concept.')
    if r['in_speelveld'] == 'ja':
        bits.append('Ligt in het speelveld: kan ook als extractie- of eindpunt dienen.')
    if (r['open17'] or 0) < 3 and r['open17'] is not None:
        bits.append('Let op: rond 17:00 vaak dicht.')
    return ' '.join(bits)


# ---------------- excel ----------------
COLS = [('kans', 'Kansscore (1-5)', 11), ('punten', 'Punten', 8), ('naam', 'Naam', 30), ('soort', 'Soort', 18),
        ('adres', 'Adres', 34), ('telefoon', 'Telefoon', 15), ('website', 'Website', 30), ('score', 'Google-score', 10),
        ('reviews', 'Reviews', 9), ('prijs', 'Prijsniveau', 10), ('afstand', 'Afstand tot start (m)', 12),
        ('in_speelveld', 'In speelveld', 10), ('open17', 'Open om 17:00 (dagen ma-za)', 12),
        ('groepen', 'Groepen/arrangementen op site', 13), ('groepen_link', 'Link groepspagina', 30), ('zaal', 'Zaal / besloten ruimte', 11),
        ('capaciteit', 'Max. groepsgrootte (site)', 11), ('buffet', 'Buffet / groepsmenu', 10), ('activiteiten', 'Noemt activiteiten/uitjes', 11),
        ('terras', 'Terras', 8), ('categorie', 'Geschikt voor', 14), ('email', 'E-mail', 28), ('formulier', 'Contactformulier', 30),
        ('contactpersoon', 'Contactpersoon (van site, controleren)', 28), ('instagram', 'Instagram', 26), ('linkedin', 'LinkedIn', 26),
        ('website_status', 'Website gelezen?', 16), ('hint', 'Belscript-hint', 60),
        ('s1', 'Benaderd op', 12), ('s2', 'Via (bel/mail/langs)', 14), ('s3', 'Gesproken met', 18), ('s4', 'Status', 13),
        ('s5', 'Afspraken (korting, link over en weer)', 30), ('s6', 'Notities', 40)]
UITLEG = [
    'Horecalijst {stad} voor horecapartners van Escape Game The Hunt. Gemaakt op {datum}. Bronnen: Google Maps (via DataForSEO) en de eigen website van elke zaak.',
    'KANSSCORE (1-5) is gebaseerd op punten (max. 7,5): groepen/arrangementen op de site +1,5 · zaal of besloten ruimte +1 · groepsgrootte 40+ +1,5 (20-39: +1) · buffet of groepsmenu +0,5 · noemt activiteiten/uitjes +0,5 · Google-score 4,3 of hoger +0,5 · 300+ reviews +0,5 · in het speelveld of binnen 300 m van de start +0,5 · minstens 4 dagen (ma-za) open om 17:00 +0,5.',
    'Punten naar sterren: minder dan 1,5 = 1 · 1,5-2,9 = 2 · 3-4,4 = 3 · 4,5-5,9 = 4 · 6 of meer = 5. De lijst is gesorteerd op kansscore en daarbinnen op punten.',
    'LET OP: groepen, zaal, groepsgrootte, buffet, e-mail en contactpersoon komen van de website van de zaak zelf. Staat het daar niet, dan staat er "nee" of is het leeg. Dat betekent niet altijd dat het niet kan: altijd navragen. Contactpersonen zijn automatisch gevonden en moeten gecontroleerd worden.',
    'GESCHIKT VOOR: groot = 40+ personen genoemd, middel = 15-39 of zaal/groepen zonder getal, klein = geen groepsinformatie. De kolommen rechts (Benaderd op t/m Notities) zijn voor de salespersoon.',
]


def write(slug, city, rows, out):
    import datetime
    wb = Workbook()
    ws = wb.active; ws.title = city[:30]
    ncol = len(COLS)
    for i, t in enumerate(UITLEG, 1):
        ws.cell(row=i, column=1, value=t.format(stad=city, datum=datetime.date.today().strftime('%d-%m-%Y')))
        ws.merge_cells(start_row=i, start_column=1, end_row=i, end_column=14)
        ws.cell(row=i, column=1).alignment = Alignment(wrap_text=True, vertical='top')
        ws.row_dimensions[i].height = 32 if i > 1 else 20
    ws.cell(row=1, column=1).font = Font(bold=True, size=12)
    hr = len(UITLEG) + 2
    for j, (_, h, w) in enumerate(COLS, 1):
        c = ws.cell(row=hr, column=j, value=h)
        c.font = Font(bold=True, color='FFFFFF'); c.fill = PatternFill('solid', fgColor='29394A')
        c.alignment = Alignment(wrap_text=True, vertical='top')
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.row_dimensions[hr].height = 45
    for r in rows:
        ws.append([r.get(k, '') for k, _, _ in COLS])
    last = hr + len(rows)
    ws.freeze_panes = ws.cell(row=hr + 1, column=4)
    ws.auto_filter.ref = f'A{hr}:{get_column_letter(ncol)}{last}'
    status_col = get_column_letter([k for k, _, _ in COLS].index('s4') + 1)
    dv = DataValidation(type='list', formula1='"Nog niet benaderd,Interesse,Afspraak,Partner,Geen interesse,Later terugbellen"', allow_blank=True)
    ws.add_data_validation(dv); dv.add(f'{status_col}{hr + 1}:{status_col}{last + 200}')
    for val, color in [('Partner', 'C6EFCE'), ('Interesse', 'FFF2B3'), ('Afspraak', 'FFF2B3'), ('Geen interesse', 'F4CCCC')]:
        ws.conditional_formatting.add(f'A{hr + 1}:{get_column_letter(ncol)}{last + 200}',
                                      FormulaRule(formula=[f'${status_col}{hr + 1}="{val}"'], fill=PatternFill('solid', fgColor=color)))
    kc = PatternFill('solid', fgColor='FCE4C8')
    for i in range(hr + 1, last + 1):
        if (ws.cell(row=i, column=1).value or 0) >= 4:
            ws.cell(row=i, column=1).fill = kc
    top = wb.create_sheet('Top 10')
    top.append(['De 10 zaken met de hoogste kansscore in ' + city + '. Begin hier.'])
    top.append([])
    keep = ['kans', 'naam', 'soort', 'telefoon', 'email', 'capaciteit', 'groepen', 'hint']
    top.append([dict((k, h) for k, h, _ in COLS)[k] for k in keep])
    for c in top[3]:
        c.font = Font(bold=True, color='FFFFFF'); c.fill = PatternFill('solid', fgColor='29394A')
    for r in rows[:10]:
        top.append([r.get(k, '') for k in keep])
    for j, w in enumerate([11, 30, 18, 15, 28, 12, 13, 70], 1):
        top.column_dimensions[get_column_letter(j)].width = w
    try:
        wb.save(out)
    except PermissionError:  # bestand staat open in Excel
        out = out.replace('.xlsx', '-nieuw.xlsx'); wb.save(out)
    return out


def run(slug):
    auth = base64.b64encode(f"{os.environ['DATAFORSEO_LOGIN']}:{os.environ['DATAFORSEO_PASSWORD']}".encode()).decode()
    cfg = json.load(open(os.path.join(ROOT, 'tools', 'kaarten', f'speelveld-{slug}.json'), encoding='utf-8'))
    global CITY
    CITY = slug.replace('-', '')
    city = next(l['name'] for l in json.load(open(os.path.join(ROOT, 'src', 'data', 'locations.json'), encoding='utf-8')) if l['slug'] == slug)
    poly = [tuple(p) for p in cfg['field']]
    lat, lon = cfg['start'][1], cfg['start'][2]
    seen, rows, cost = set(), [], 0
    for q in QUERIES:
        items, c = maps(auth, q, lat, lon); cost += c
        for i in items:
            key = i.get('place_id') or i.get('title')
            if key in seen or not i.get('latitude'):
                continue
            seen.add(key)
            pos = (i['latitude'], i['longitude'])
            rt = i.get('rating') or {}
            d = round(dist(pos, (lat, lon)))
            ins = 'ja' if inside(pos[0], pos[1], poly) else 'nee'
            if ins == 'nee' and d >= 600:
                continue
            rows.append(dict(naam=i.get('title'), soort=i.get('category') or '', adres=i.get('address') or '',
                             telefoon=i.get('phone') or '', website=i.get('url') or '', score=rt.get('value'),
                             reviews=rt.get('votes_count') or 0, prijs=i.get('price_level') or '', afstand=d,
                             in_speelveld=ins, open17=open_at_17(i.get('work_hours'))))
    print(f'{city}: {len(rows)} zaken uit Google Maps (${cost:.3f}), websites lezen...')
    with cf.ThreadPoolExecutor(12) as ex:
        crawled = list(ex.map(lambda r: crawl(r['website']), rows))
    for r, c in zip(rows, crawled):
        r.update(analyse(c))
        r['kans'], r['punten'] = kans(r)
        cap = r['capaciteit'] or 0
        r['categorie'] = 'groot (40+)' if cap >= 40 else 'middel (15-39)' if cap >= 15 or r['groepen'] == 'ja' or r['zaal'] == 'ja' else 'klein / onbekend'
        r['hint'] = hint(r)
        if r['open17'] is None:
            r['open17'] = 'onbekend'
    rows.sort(key=lambda r: (-r['kans'], -r['punten'], r['afstand']))
    os.makedirs(OUTDIR, exist_ok=True)
    out = os.path.join(OUTDIR, f'horeca-{slug}-uitgebreid.xlsx')
    out = write(slug, city, rows, out)
    print('klaar:', out)
    return rows


if __name__ == '__main__':
    for s in sys.argv[1:]:
        run(s)
