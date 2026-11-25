"""Eigenaren zoeken voor de horecalijst van een stad.

Gebruik:  python tools/seo/horeca_eigenaar.py groningen

Per zaak in tools/seo/horeca/horeca-<stad>-uitgebreid.xlsx:
1. Leest de eigen website opnieuw, nu gericht op over ons, team, ons verhaal, colofon, privacy en voorwaarden:
   namen bij "eigenaar", "uitbater", "opgericht door", "gerund door", "wij zijn ... en ...", plus KvK-nummer en
   bedrijfsnaam (B.V., V.O.F., Holding).
2. Zoekt in Google (DataForSEO) op "<naam zaak>" <stad> eigenaar en leest titels en fragmenten, vaak lokaal nieuws.
3. Zet vijf kolommen achteraan: Eigenaar (gevonden), Bron, KvK-nummer, Bedrijfsnaam / rechtsvorm, E-mailen toegestaan?

Alles is automatisch gevonden en moet gecontroleerd worden (bijv. via kvk.nl of een belletje).
"""
import base64, concurrent.futures as cf, json, os, re, sys, urllib.parse, urllib.request
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from horeca_verrijk import get, text_of  # noqa: E402

SUB = re.compile(r'over-?ons|about|team|verhaal|story|wie-?zijn|historie|geschiedenis|colofon|privacy|voorwaarden|disclaimer|impressum|contact|wij-zijn|ons-|eigenaar', re.I)
NM = r"([A-Z][a-zà-ÿ'\-]+(?: (?:van|de|der|den|ten|ter|van der|van den|van de|el|al))? [A-Z][a-zà-ÿ'\-]+|[A-Z][a-zà-ÿ]+)"
ROLE = r'(?:eigenaar|eigenaresse|eigenaren|uitbater|uitbaters|oprichter|oprichters|initiatiefnemer|owner|owners|founder|founders)'
PATS = [
    NM + r'(?: \(\d+\))?,? (?:is |zijn )?(?:de |onze |trotse )?(?:nieuwe )?' + ROLE,
    ROLE + r'(?: van [^.,]{2,40})?[\s:,\-–]{1,4}' + NM + r'(?: en ' + NM + ')?',
    r'(?:opgericht|gerund|gestart|geopend|overgenomen|uitgebaat)(?: in \d{4})? door ' + NM + r'(?: en ' + NM + ')?',
    r'(?:[Ww]ij zijn|[Mm]ijn naam is|[Ww]e are|[Ii]k ben) ' + NM + r'(?: en ' + NM + ')?',
]
STOP = set('''Cadeaukaart Vacatures Vandaag Nederland Zuid Noord Oost West Nieuws Menu Contact Home Reserveren Groningen Restaurant Cafe Café De Het Een
Onze Ons Wij Bij Van Voor Met Welkom Ook Als Over Deze Dit In Op Wie Wat Waar The And Our We Team Keuken Bar Lunch Diner Grand Hotel Stad Stadjers
Google Instagram Facebook Privacy Cookie Algemene Voorwaarden Website Eigenaar Uitbater Sinds Samen Jullie Alle Elke Iedereen Gasten Groep Groepen
Brasserie Bistro Pizzeria Eetcafé Proeflokaal Koffie Bier Wijn Huis Plein Markt Straat Kade Uw Jouw Je Zij Hij Zo Nu Dan Maar Want Dus Tot Om Na Uit Zijn'''.split())
KVK = re.compile(r'(?:kvk|k\.v\.k\.|kamer van koophandel|coc|chamber of commerce)[\s.:\-–#nummer]{0,20}(\d{8})', re.I)
ENT = re.compile(r"([A-Z0-9][\w&'\-. ]{1,50}?\s(?:B\.?V\.?|V\.?O\.?F\.?|Holding(?: B\.?V\.?)?|C\.?V\.?))(?=[\s,.;)]|$)")


NIET = re.compile(r'(?i)(straat|weg|plein|markt|kade|diep|gracht|singel|laan|steeg|stichting|werelderfgoed|waddenzee|groningen|vriendelijke|bereikbare|gastvrije|leuke|nieuwe|bekijk|directeur|doorstart|jumbo|valora|hoeve|cirkel|tijden|smederij|smaakaron|world|nord|kop|out|bart|albert|liana|chaya|culvertson)$')


def namen(text, alleen_rol=False):
    out = []
    for p in (PATS[:3] if alleen_rol else PATS):
        for m in re.finditer(p, text):
            for g in m.groups():
                if not g:
                    continue
                w = g.split()
                if len(w) < 2 or any(x in STOP for x in w) or any(NIET.search(x) for x in w):
                    continue
                ctx = text[max(0, m.start() - 60): m.end() + 60]
                out.append((g, ctx))
    return out


def crawl(url):
    pages = []
    try:
        h, final = get(url)
    except Exception:
        return pages
    pages.append((final, h))
    base = urllib.parse.urlparse(final).netloc.replace('www.', '')
    links = []
    for href in re.findall(r'href=["\']([^"\'#]+)', h):
        u = urllib.parse.urljoin(final, href)
        p = urllib.parse.urlparse(u)
        if p.netloc.replace('www.', '') == base and SUB.search(p.path) and u not in links:
            links.append(u)
    for u in links[:10]:
        try:
            pages.append((u, get(u)[0]))
        except Exception:
            pass
    return pages


def google(auth, naam, stad):
    q = f'"{naam}" {stad} eigenaar'
    body = json.dumps([{'keyword': q, 'location_code': 2528, 'language_code': 'nl', 'depth': 10}]).encode()
    req = urllib.request.Request('https://api.dataforseo.com/v3/serp/google/organic/live/advanced', data=body,
                                 headers={'Authorization': 'Basic ' + auth, 'Content-Type': 'application/json'})
    try:
        r = json.load(urllib.request.urlopen(req, timeout=120))
        items = (r['tasks'][0].get('result') or [{}])[0].get('items') or []
    except Exception:
        return []
    return [(i.get('url', ''), (i.get('title') or '') + '. ' + (i.get('description') or '')) for i in items if i.get('type') == 'organic']


def zoek(row, auth, stad):
    naam, site = row['naam'], row['website']
    res = {'eigenaar': '', 'bron': '', 'kvk': '', 'entiteit': ''}
    kandidaten = []
    if site:
        for u, h in crawl(site):
            t = text_of(h)
            for n, ctx in namen(t):
                kandidaten.append((n, 'website: ' + u))
            if not res['kvk']:
                m = KVK.search(t)
                if m:
                    res['kvk'] = m.group(1)
            if not res['entiteit']:
                for m in ENT.finditer(t):
                    e = m.group(1).strip()
                    if not re.match(r'(?i)(kvk|btw|iban|copyright|©|alle rechten)', e):
                        res['entiteit'] = e; break
    if not kandidaten:
        kort = re.sub(r'\s*[\-–|(].*$', '', naam).strip()
        sleutel = [w.lower() for w in re.findall(r'\w{4,}', kort) if w.lower() not in ('café', 'cafe', 'restaurant', 'grand', 'brasserie', 'bistro', 'hotel', 'groningen')] or [kort.lower()]
        for u, t in google(auth, kort, stad):
            low = t.lower()
            if not any(s in low for s in sleutel) or stad.lower() not in (low + u.lower()):
                continue
            if re.search(r'telefoonboek|deals\.|tripadvisor|werkzoeken|vacature|quotenet|maptons|hotelcentrum|fok\.nl|issuu|companyinfo|bedrijvenregister', u):
                continue
            for n, ctx in namen(t, alleen_rol=True):
                kandidaten.append((n, 'Google: ' + u))
    if kandidaten:
        seen = []
        for n, b in kandidaten:
            if n not in [s[0] for s in seen]:
                seen.append((n, b))
        res['eigenaar'] = ', '.join(s[0] for s in seen[:2])
        res['bron'] = seen[0][1][:200]
    return res


def toegestaan(ent, naam):
    t = (ent + ' ' + naam).upper().replace('.', '')
    if re.search(r'\bBV\b|HOLDING', t):
        return 'ja (BV): mailen mag, met afmeldlink'
    if re.search(r'\bVOF\b|\bCV\b', t):
        return 'nee (vof): bellen, langsgaan of LinkedIn'
    return 'onbekend: eerst bellen of KvK checken'


def main(slug):
    stad = slug.replace('-', ' ').title()
    f = os.path.join(HERE, 'horeca', f'horeca-{slug}-uitgebreid.xlsx')
    wb = load_workbook(f); ws = wb[wb.sheetnames[0]]
    hr = next(r for r in range(1, 20) if ws.cell(r, 3).value == 'Naam')
    col = {ws.cell(hr, c).value: c for c in range(1, ws.max_column + 1)}
    rows = []
    for r in range(hr + 1, ws.max_row + 1):
        if ws.cell(r, col['Naam']).value:
            rows.append({'r': r, 'naam': ws.cell(r, col['Naam']).value, 'website': ws.cell(r, col['Website']).value or ''})
    auth = base64.b64encode(f"{os.environ['DATAFORSEO_LOGIN']}:{os.environ['DATAFORSEO_PASSWORD']}".encode()).decode()
    with cf.ThreadPoolExecutor(12) as ex:
        res = list(ex.map(lambda x: zoek(x, auth, stad), rows))
    new = ['Eigenaar (gevonden, controleren)', 'Bron eigenaar', 'KvK-nummer (van site)', 'Bedrijfsnaam / rechtsvorm (van site)', 'E-mailen toegestaan?']
    start = col.get(new[0]) or ws.max_column + 1
    for i, h in enumerate(new):
        x = ws.cell(hr, start + i, h); x.font = Font(bold=True, color='FFFFFF'); x.fill = PatternFill('solid', fgColor='29394A')
        x.alignment = Alignment(wrap_text=True, vertical='top')
        ws.column_dimensions[x.column_letter].width = (28, 40, 14, 30, 30)[i]
    n = 0
    for row, r in zip(rows, res):
        vals = [r['eigenaar'], r['bron'], r['kvk'], r['entiteit'], toegestaan(r['entiteit'], row['naam'])]
        for i, v in enumerate(vals):
            ws.cell(row['r'], start + i, v).alignment = Alignment(wrap_text=True, vertical='top')
        n += bool(r['eigenaar'])
    ws.cell(hr - 1, 1, 'EIGENAAR (laatste kolommen): automatisch gezocht op de eigen website (over ons, team, colofon, privacy) en in Google (lokaal nieuws). '
                       'Altijd controleren. E-mailen: alleen naar een BV ongevraagd mailen; eenmanszaak/vof bellen, langsgaan of LinkedIn.').font = Font(italic=True)
    try:
        wb.save(f); out = f
    except PermissionError:
        out = f.replace('.xlsx', '-nieuw.xlsx'); wb.save(out)
    print(f'{n} van {len(rows)} eigenaren gevonden, {sum(bool(r["kvk"]) for r in res)} KvK-nummers, '
          f'{sum(bool(r["entiteit"]) for r in res)} bedrijfsnamen -> {out}')
    return res, rows


if __name__ == '__main__':
    res, rows = main(sys.argv[1] if len(sys.argv) > 1 else 'groningen')
    for row, r in zip(rows, res):
        if r['eigenaar']:
            print(' ', row['naam'][:35], '|', r['eigenaar'], '|', r['bron'][:90])
