"""Statistiekpagina en wekelijkse e-mail voor escapegamethehunt.nl.

Gebruik:
  python tools/seo/statistiek.py --gsc --push                    (dagelijks: Search Console bijwerken)
  python tools/seo/statistiek.py --posities --gsc --mail --push  (wekelijks: ook posities meten en mailen)
  python tools/seo/statistiek.py --build                         (alleen pagina opnieuw maken)

Instellingen staan in tools/seo/statistiek.local.json (niet in git):
  {"wachtwoord": "...", "gsc_key": "pad/naar/service-account.json",
   "mail_url": "https://script.google.com/macros/s/.../exec", "mail_token": "...",
   "ontvangers": "a@b.nl,c@d.nl", "onderwerp": "Statistieken Escape Game The Hunt website"}

Pagina: docs/statistiek/index.html, versleuteld met AES-GCM (sleutel uit het wachtwoord via PBKDF2).
Historie: tools/seo/metingen/posities-*.csv (posities) en tools/seo/data/gsc-*.json (Search Console).
"""
import argparse, base64, csv, datetime as dt, glob, html, json, os, secrets, subprocess, sys, urllib.request
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CFG_F = os.path.join(HERE, 'statistiek.local.json')
DATA = os.path.join(HERE, 'data')
MET = os.path.join(HERE, 'metingen')
OUT = os.path.join(ROOT, 'docs', 'statistiek', 'index.html')
SITE = 'https://escapegamethehunt.nl/'
KW = ['escaperoom', 'escape room', 'bedrijfsuitje', 'teamuitje', 'vrijgezellenfeest']
E = html.escape


def cfg():
    c = json.load(open(CFG_F, encoding='utf-8')) if os.path.exists(CFG_F) else {}
    changed = False
    if not c.get('wachtwoord'):
        c['wachtwoord'] = secrets.token_urlsafe(9); changed = True
    if not c.get('mail_token'):
        c['mail_token'] = secrets.token_urlsafe(24); changed = True
    c.setdefault('ontvangers', 'frans@badassgames.nl,ronald@badassgames.nl')
    c.setdefault('onderwerp', 'Statistieken Escape Game The Hunt website')
    c.setdefault('gsc_key', ''); c.setdefault('mail_url', '')
    if changed or not os.path.exists(CFG_F):
        json.dump(c, open(CFG_F, 'w', encoding='utf-8'), indent=1)
    return c


# ---------------- Search Console ----------------
def gsc_fetch(c):
    if not c.get('gsc_key') or not os.path.exists(c['gsc_key']):
        print('Search Console: geen sleutelbestand ingesteld, overgeslagen'); return None
    from google.oauth2 import service_account
    from google.auth.transport.requests import AuthorizedSession
    cred = service_account.Credentials.from_service_account_file(c['gsc_key'], scopes=['https://www.googleapis.com/auth/webmasters.readonly'])
    s = AuthorizedSession(cred)
    url = 'https://www.googleapis.com/webmasters/v3/sites/' + urllib.request.quote(SITE, safe='') + '/searchAnalytics/query'
    end = dt.date.today() - dt.timedelta(days=3)

    def q(start, stop, dims, limit=25000):
        r = s.post(url, json={'startDate': str(start), 'endDate': str(stop), 'dimensions': dims, 'rowLimit': limit})
        r.raise_for_status(); return r.json().get('rows', [])
    cur0, prev0 = end - dt.timedelta(days=27), end - dt.timedelta(days=55)
    out = {'datum': str(dt.date.today()), 'tot': str(end),
           'dagen': q(end - dt.timedelta(days=480), end, ['date']),
           'q_nu': q(cur0, end, ['query'], 5000), 'q_voor': q(prev0, cur0 - dt.timedelta(days=1), ['query'], 5000),
           'p_nu': q(cur0, end, ['page'], 1000), 'p_voor': q(prev0, cur0 - dt.timedelta(days=1), ['page'], 1000),
           'q_maand': q(end - dt.timedelta(days=480), end, ['query', 'date'], 25000)}
    os.makedirs(DATA, exist_ok=True)
    json.dump(out, open(os.path.join(DATA, f'gsc-{out["datum"]}.json'), 'w', encoding='utf-8'))
    print('Search Console bijgewerkt t/m', end)
    return out


def gsc_latest():
    f = sorted(glob.glob(os.path.join(DATA, 'gsc-*.json')))
    return json.load(open(f[-1], encoding='utf-8')) if f else None


# ---------------- posities ----------------
def rankings():
    """{datum: {(stad, kw): positie of None}}"""
    out = {}
    for f in sorted(glob.glob(os.path.join(MET, 'posities-*.csv'))):
        d = os.path.basename(f)[9:19]
        rows = list(csv.DictReader(open(f, encoding='utf-8-sig'), delimiter=';'))
        m = {}
        for r in rows:
            kw = r['zoekwoord'][:-len(r['stad']) - 1] if r['zoekwoord'].lower().endswith(r['stad'].lower()) else r['zoekwoord']
            m[(r['stad'], kw.strip())] = int(r['positie']) if r['positie'] else None
        out[d] = m
    return out


# ---------------- helpers ----------------
def agg(rows, key=0):
    return {r['keys'][key]: r for r in rows}


def tot(rows):
    c = sum(r['clicks'] for r in rows); i = sum(r['impressions'] for r in rows)
    p = sum(r['position'] * r['impressions'] for r in rows) / i if i else 0
    return c, i, p, (c / i * 100 if i else 0)


def arrow(new, old, lower_is_better=False):
    if old in (None, '') or new in (None, ''):
        return ''
    d = (old - new) if lower_is_better else (new - old)
    if abs(d) < 1e-9:
        return '<span class="eq">=</span>'
    return f'<span class="{"up" if d > 0 else "down"}">{"▲" if d > 0 else "▼"} {abs(d):.{0 if float(d).is_integer() else 1}f}</span>'


def svg_line(series, w=760, h=180, labels=None, invert=False):
    """series: list of (naam, kleur, [(x_label, waarde)])"""
    allv = [v for _, _, pts in series for _, v in pts if v is not None]
    if not allv:
        return '<p class="muted">Nog geen gegevens.</p>'
    lo, hi = min(allv), max(allv)
    if hi == lo: hi = lo + 1
    n = max(len(pts) for _, _, pts in series)
    X = lambda i: 40 + i * (w - 60) / max(1, n - 1)
    Y = (lambda v: 15 + (v - lo) / (hi - lo) * (h - 40)) if invert else (lambda v: h - 25 - (v - lo) / (hi - lo) * (h - 40))
    g = [f'<svg viewBox="0 0 {w} {h}" class="chart" role="img">']
    for t in range(5):
        v = lo + (hi - lo) * t / 4; y = Y(v)
        g.append(f'<line x1="40" x2="{w-20}" y1="{y:.1f}" y2="{y:.1f}" class="grid"/><text x="34" y="{y+4:.1f}" class="ax" text-anchor="end">{v:.0f}</text>')
    for name, col, pts in series:
        d = ' '.join(f'{"M" if j == 0 else "L"}{X(j):.1f},{Y(v):.1f}' for j, (_, v) in enumerate(pts) if v is not None)
        g.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="2.2"/>')
    pts = series[0][2]
    step = max(1, len(pts) // 8)
    for j in range(0, len(pts), step):
        g.append(f'<text x="{X(j):.1f}" y="{h-6}" class="ax" text-anchor="middle">{E(str(pts[j][0]))}</text>')
    g.append('</svg>')
    leg = ''.join(f'<span class="leg"><i style="background:{col}"></i>{E(n)}</span>' for n, col, _ in series)
    return ''.join(g) + f'<div class="legend">{leg}</div>'


def cls(p):
    return '' if p is None else 'top' if p <= 3 else 'ok' if p <= 10 else 'low'


# ---------------- dashboard ----------------
def dashboard(g, R):
    today = dt.date.today().strftime('%d-%m-%Y')
    parts = [f'<header><h1>Statistieken escapegamethehunt.nl</h1><p class="muted">Bijgewerkt op {today}. Search Console loopt 2 à 3 dagen achter; posities worden wekelijks gemeten (mobiel, vanaf het centrum van elke stad, top 30).</p></header>']
    # KPI
    if g:
        c1, i1, p1, r1 = tot(g['p_nu']); c0, i0, p0, r0 = tot(g['p_voor'])
        parts.append('<section><h2>Laatste 28 dagen <small>t.o.v. de 28 dagen daarvoor</small></h2><div class="kpis">'
                     f'<div><b>{c1:,}</b><span>klikken</span>{arrow(c1, c0)}</div>'
                     f'<div><b>{i1:,}</b><span>vertoningen</span>{arrow(i1, i0)}</div>'
                     f'<div><b>{p1:.1f}</b><span>gem. positie</span>{arrow(p1, p0, True)}</div>'
                     f'<div><b>{r1:.1f}%</b><span>CTR</span>{arrow(r1, r0)}</div></div></section>'.replace(',', '.'))
        wk = defaultdict(lambda: [0, 0])
        for r in g['dagen']:
            d = dt.date.fromisoformat(r['keys'][0]); k = d - dt.timedelta(days=d.weekday())
            wk[k][0] += r['clicks']; wk[k][1] += r['impressions']
        ks = sorted(wk)[:-1] if len(wk) > 1 else sorted(wk)
        parts.append('<section><h2>Klikken en vertoningen per week</h2>'
                     + svg_line([('Klikken', '#f29222', [(k.strftime('%d-%m-%y'), wk[k][0]) for k in ks])])
                     + svg_line([('Vertoningen', '#29394a', [(k.strftime('%d-%m-%y'), wk[k][1]) for k in ks])]) + '</section>')
    else:
        parts.append('<section><h2>Search Console</h2><p class="muted">Search Console is nog niet gekoppeld aan dit dashboard. Zodra de sleutel is ingesteld, verschijnen hier klikken, vertoningen, posities en kansen.</p></section>')
    # posities overzicht in de tijd
    dates = sorted(R)
    if dates:
        cnt = {d: [sum(1 for v in R[d].values() if v and v <= lim) for lim in (3, 10, 30)] for d in dates}
        lab = lambda d: dt.date.fromisoformat(d).strftime('%d-%m')
        parts.append('<section><h2>Aantal zoekwoorden in de top 3, top 10 en top 30</h2><p class="muted">33 steden × 5 zoekwoorden = 165 zoekopdrachten.</p>'
                     + svg_line([('Top 3', '#2e7d32', [(lab(d), cnt[d][0]) for d in dates]), ('Top 10', '#f29222', [(lab(d), cnt[d][1]) for d in dates]),
                                 ('Top 30', '#29394a', [(lab(d), cnt[d][2]) for d in dates])])
                     + '<table class="small"><tr><th>Meting</th><th>Top 3</th><th>Top 10</th><th>Top 30</th></tr>'
                     + ''.join(f'<tr><td>{lab(d)}-{d[:4]}</td><td>{cnt[d][0]}</td><td>{cnt[d][1]}</td><td>{cnt[d][2]}</td></tr>' for d in reversed(dates)) + '</table></section>')
        last = dates[-1]; prev = dates[-2] if len(dates) > 1 else None
        cities = sorted({s for s, _ in R[last]})
        head = ''.join(f'<th>{E(k)}</th>' for k in KW)
        body = []
        for s in cities:
            cells = []
            for k in KW:
                p = R[last].get((s, k)); hist = [R[d].get((s, k)) for d in dates]
                tip = ' → '.join('–' if v is None else str(v) for v in hist)
                a = arrow(p, R[prev].get((s, k)), True) if prev and p and R[prev].get((s, k)) else ('<span class="up">nieuw</span>' if prev and p and not R[prev].get((s, k)) else '')
                cells.append(f'<td class="{cls(p)}" title="Historie: {tip}">{p or "–"} {a}<div class="hist">{tip}</div></td>')
            body.append(f'<tr><th>{E(s)}</th>{"".join(cells)}</tr>')
        parts.append(f'<section><h2>Posities per stad</h2><p class="muted">Laatste meting {lab(last)}-{last[:4]}. Groen = top 3, geel = 4-10, oranje = 11-30, streepje = niet in de top 30. Onder elk getal staat de historie van oud naar nieuw.</p>'
                     f'<div class="scroll"><table class="rank"><tr><th>Stad</th>{head}</tr>{"".join(body)}</table></div></section>')
    if g:
        qn, qv = agg(g['q_nu']), agg(g['q_voor'])
        kans = sorted([r for r in g['q_nu'] if 4 <= r['position'] <= 15 and r['impressions'] >= 20], key=lambda r: -r['impressions'])[:25]
        parts.append('<section><h2>Kansen: positie 4 tot 15 met veel vertoningen</h2><p class="muted">Hier levert een paar plekken stijgen het meeste extra klikken op.</p><table><tr><th>Zoekwoord</th><th>Positie</th><th>Vertoningen</th><th>Klikken</th></tr>'
                     + ''.join(f'<tr><td>{E(r["keys"][0])}</td><td>{r["position"]:.1f}</td><td>{r["impressions"]}</td><td>{r["clicks"]}</td></tr>' for r in kans) + '</table></section>')
        ch = []
        for k, r in qn.items():
            if k in qv and r['impressions'] >= 15:
                ch.append((qv[k]['position'] - r['position'], k, r['position'], qv[k]['position'], r['impressions']))
        ch.sort()
        rows = lambda L: ''.join(f'<tr><td>{E(k)}</td><td>{o:.1f} → {n:.1f}</td><td>{i}</td></tr>' for _, k, n, o, i in L)
        parts.append('<section class="two"><div><h2>Stijgers</h2><table><tr><th>Zoekwoord</th><th>Positie</th><th>Vert.</th></tr>' + rows(list(reversed(ch[-10:]))) + '</table></div>'
                     '<div><h2>Dalers</h2><table><tr><th>Zoekwoord</th><th>Positie</th><th>Vert.</th></tr>' + rows(ch[:10]) + '</table></div></section>')
        pv = agg(g['p_voor'])
        top = sorted(g['p_nu'], key=lambda r: -r['clicks'])[:20]
        parts.append('<section><h2>Beste pagina\'s</h2><table><tr><th>Pagina</th><th>Klikken</th><th>Vertoningen</th><th>Positie</th></tr>'
                     + ''.join(f'<tr><td>{E(r["keys"][0].replace(SITE[:-1], "") or "/")}</td><td>{r["clicks"]} {arrow(r["clicks"], pv.get(r["keys"][0], {}).get("clicks"))}</td><td>{r["impressions"]}</td><td>{r["position"]:.1f}</td></tr>' for r in top) + '</table></section>')
        # historie per stad uit Search Console (maandelijks, escaperoom/escape room + stad)
        cities = [l['name'] for l in json.load(open(os.path.join(ROOT, 'src', 'data', 'locations.json'), encoding='utf-8'))]
        mon = defaultdict(lambda: defaultdict(lambda: [0, 0.0]))
        for r in g['q_maand']:
            q, d = r['keys'][0].lower(), r['keys'][1][:7]
            for s in cities:
                if s.lower() in q and 'escape' in q:
                    m = mon[s][d]; m[0] += r['impressions']; m[1] += r['position'] * r['impressions']
        months = sorted({d for s in mon for d in mon[s]})[-12:]
        rowsm = []
        for s in cities:
            cells = []
            for d in months:
                i, pw = mon[s].get(d, [0, 0])
                p = pw / i if i else None
                cells.append(f'<td class="{cls(round(p) if p else None)}">{f"{p:.1f}" if p else "–"}</td>')
            rowsm.append(f'<tr><th>{E(s)}</th>{"".join(cells)}</tr>')
        parts.append('<section><h2>Historie uit Search Console: gemiddelde positie per maand</h2><p class="muted">Zoekopdrachten met "escape" en de stadsnaam, gewogen naar vertoningen. Zo zie je ook hoe hoog we vóór de nieuwe site stonden.</p>'
                     f'<div class="scroll"><table class="rank"><tr><th>Stad</th>{"".join(f"<th>{m[5:]}-{m[2:4]}</th>" for m in months)}</tr>{"".join(rowsm)}</table></div></section>')
    return '\n'.join(parts)


CSS = '''body{font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:0;background:#f3f5f7;color:#1c2834}
main{max-width:1100px;margin:0 auto;padding:24px 16px}header h1{margin:0 0 4px;font-size:1.6rem}h2{font-size:1.15rem;margin:0 0 8px}h2 small{font-weight:400;color:#5a6878;font-size:.85rem}
section{background:#fff;border:1px solid #dbe2e9;border-radius:10px;padding:18px;margin:16px 0}.muted{color:#5a6878;font-size:.9rem;margin:0 0 10px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px}.kpis div{background:#f3f5f7;border-radius:8px;padding:12px}.kpis b{display:block;font-size:1.6rem}.kpis span{color:#5a6878;margin-right:8px}
.up{color:#2e7d32;font-weight:600;font-size:.85em}.down{color:#c62828;font-weight:600;font-size:.85em}.eq{color:#5a6878;font-size:.85em}
table{border-collapse:collapse;width:100%}th,td{padding:6px 8px;border-bottom:1px solid #eef1f4;text-align:left;vertical-align:top}table.rank td{text-align:center;min-width:90px}
td.top{background:#d9f2dc}td.ok{background:#fff3c4}td.low{background:#fde3cf}.hist{font-size:11px;color:#5a6878}.scroll{overflow-x:auto}
.two{display:grid;grid-template-columns:1fr 1fr;gap:20px}@media(max-width:760px){.two{grid-template-columns:1fr}}
.chart{width:100%;height:auto}.chart .grid{stroke:#eef1f4}.chart .ax{font-size:11px;fill:#5a6878}.legend{display:flex;gap:16px;font-size:.85rem;margin-bottom:8px}.leg i{display:inline-block;width:12px;height:12px;border-radius:2px;margin-right:6px;vertical-align:-1px}
table.small{width:auto;margin-top:8px;font-size:.9rem}
#lock{max-width:380px;margin:12vh auto;background:#fff;border:1px solid #dbe2e9;border-radius:10px;padding:24px;text-align:center}#lock input{width:100%;padding:10px;font-size:1rem;margin:12px 0;border:1px solid #dbe2e9;border-radius:6px}#lock button{background:#f29222;border:0;color:#fff;padding:10px 18px;border-radius:6px;font-weight:700;cursor:pointer}'''


def encrypt(content, password):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    import hashlib
    salt, iv = secrets.token_bytes(16), secrets.token_bytes(12)
    key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 200000, 32)
    ct = AESGCM(key).encrypt(iv, content.encode('utf-8'), None)
    b = lambda x: base64.b64encode(x).decode()
    return b(salt), b(iv), b(ct)


def page(content, password):
    salt, iv, ct = encrypt(content, password)
    return f'''<!doctype html><html lang="nl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow"><title>Statistieken</title><style>{CSS}</style></head><body>
<div id="lock"><h1 style="font-size:1.3rem;margin:0">Statistieken</h1><p class="muted">Alleen voor het team van Escape Game The Hunt.</p>
<form id="f"><input id="pw" type="password" placeholder="Wachtwoord" autocomplete="current-password"><label style="font-size:.85rem"><input type="checkbox" id="rem" style="width:auto;margin:0 6px 0 0">Onthouden op dit apparaat</label><br><br><button>Openen</button><p id="err" style="color:#c62828"></p></form></div>
<main id="app" hidden></main>
<script>
const S="{salt}",I="{iv}",C="{ct}";const d=s=>Uint8Array.from(atob(s),c=>c.charCodeAt(0));
async function open_(pw){{const k=await crypto.subtle.importKey("raw",new TextEncoder().encode(pw),"PBKDF2",false,["deriveKey"]);
const key=await crypto.subtle.deriveKey({{name:"PBKDF2",salt:d(S),iterations:200000,hash:"SHA-256"}},k,{{name:"AES-GCM",length:256}},false,["decrypt"]);
const pt=await crypto.subtle.decrypt({{name:"AES-GCM",iv:d(I)}},key,d(C));document.getElementById("app").innerHTML=new TextDecoder().decode(pt);
document.getElementById("app").hidden=false;document.getElementById("lock").remove();}}
document.getElementById("f").addEventListener("submit",async e=>{{e.preventDefault();const pw=document.getElementById("pw").value;
try{{await open_(pw);if(document.getElementById("rem").checked)try{{localStorage.setItem("stat_pw",pw)}}catch(_){{}}}}catch(_){{document.getElementById("err").textContent="Onjuist wachtwoord."}}}});
try{{const s=localStorage.getItem("stat_pw");if(s)open_(s).catch(()=>localStorage.removeItem("stat_pw"))}}catch(_){{}}
</script></body></html>'''


# ---------------- e-mail ----------------
def email_html(g, R):
    st = 'font-family:Arial,Helvetica,sans-serif;color:#1c2834'
    td = 'padding:6px 8px;border-bottom:1px solid #eef1f4;font-size:14px'
    col = {'top': '#d9f2dc', 'ok': '#fff3c4', 'low': '#fde3cf', '': '#ffffff'}
    p = [f'<div style="{st};max-width:680px;margin:0 auto"><h1 style="font-size:22px;margin:0 0 4px">Statistieken escapegamethehunt.nl</h1>'
         f'<p style="color:#5a6878;font-size:13px;margin:0 0 16px">Week {dt.date.today().isocalendar()[1]}, {dt.date.today().strftime("%d-%m-%Y")}</p>']
    plain = lambda s: s.replace('class="up"', 'style="color:#2e7d32;font-weight:bold"').replace('class="down"', 'style="color:#c62828;font-weight:bold"').replace('class="eq"', 'style="color:#5a6878"')
    if g:
        c1, i1, p1, r1 = tot(g['p_nu']); c0, i0, p0, r0 = tot(g['p_voor'])
        cell = lambda v, l, a: f'<td style="background:#f3f5f7;padding:12px;border-radius:8px;width:25%"><div style="font-size:22px;font-weight:bold">{v}</div><div style="color:#5a6878;font-size:12px">{l}</div><div style="font-size:12px">{plain(a)}</div></td>'
        p.append('<h2 style="font-size:16px">Laatste 28 dagen (Search Console)</h2><table cellspacing="6" style="width:100%"><tr>'
                 + cell(f'{c1}', 'klikken', arrow(c1, c0)) + cell(f'{i1}', 'vertoningen', arrow(i1, i0)) + cell(f'{p1:.1f}', 'gem. positie', arrow(p1, p0, True)) + cell(f'{r1:.1f}%', 'CTR', arrow(r1, r0)) + '</tr></table>')
    dates = sorted(R)
    if dates:
        last = dates[-1]; prev = dates[-2] if len(dates) > 1 else None
        cnt = lambda d: [sum(1 for v in R[d].values() if v and v <= lim) for lim in (3, 10, 30)]
        cl, cp = cnt(last), (cnt(prev) if prev else None)
        p.append('<h2 style="font-size:16px">Posities (165 zoekopdrachten, 33 steden)</h2><table style="border-collapse:collapse"><tr>'
                 + ''.join(f'<td style="{td}"><b>{lab}</b>: {v} {plain(arrow(v, cp[i])) if cp else ""}</td>' for i, (lab, v) in enumerate(zip(['Top 3', 'Top 10', 'Top 30'], cl))) + '</tr></table>')
        if prev:
            mv = []
            for k, v in R[last].items():
                o = R[prev].get(k)
                if v and o and v != o: mv.append((o - v, k, o, v))
                elif v and not o: mv.append((31 - v, k, None, v))
            mv.sort(reverse=True)
            rows = lambda L: ''.join(f'<tr><td style="{td}">{E(k[1])} {E(k[0].lower())}</td><td style="{td}">{o or "–"} → {v}</td></tr>' for _, k, o, v in L)
            p.append('<h3 style="font-size:14px">Grootste stijgers</h3><table style="border-collapse:collapse;width:100%">' + rows(mv[:5]) + '</table>')
            dn = [x for x in reversed(mv) if x[0] < 0][:5]
            if dn: p.append('<h3 style="font-size:14px">Grootste dalers</h3><table style="border-collapse:collapse;width:100%">' + rows(dn) + '</table>')
        cities = sorted({s for s, _ in R[last]})
        head = ''.join(f'<th style="{td};text-align:center">{E(k)}</th>' for k in KW)
        body = ''.join('<tr><td style="' + td + '"><b>' + E(s) + '</b></td>' + ''.join(
            f'<td style="{td};text-align:center;background:{col[cls(R[last].get((s, k)))]}">{R[last].get((s, k)) or "–"}</td>' for k in KW) + '</tr>' for s in cities)
        p.append(f'<h2 style="font-size:16px">Posities per stad</h2><table style="border-collapse:collapse;width:100%"><tr><th style="{td}">Stad</th>{head}</tr>{body}</table>')
    if g:
        kans = sorted([r for r in g['q_nu'] if 4 <= r['position'] <= 15 and r['impressions'] >= 20], key=lambda r: -r['impressions'])[:5]
        p.append('<h2 style="font-size:16px">Top 5 kansen</h2><table style="border-collapse:collapse;width:100%">' + ''.join(
            f'<tr><td style="{td}">{E(r["keys"][0])}</td><td style="{td}">positie {r["position"]:.1f}</td><td style="{td}">{r["impressions"]} vert.</td></tr>' for r in kans) + '</table>')
    p.append(f'<p style="margin-top:20px"><a href="{SITE}statistiek/" style="background:#f29222;color:#fff;padding:10px 16px;border-radius:6px;text-decoration:none;font-weight:bold">Bekijk het volledige dashboard</a></p>'
             '<p style="color:#5a6878;font-size:12px">Het dashboard is beveiligd met een wachtwoord. Search Console loopt 2 à 3 dagen achter; posities worden wekelijks gemeten.</p></div>')
    return ''.join(p)


def send(c, body):
    if not c.get('mail_url'):
        print('E-mail: nog geen mail_url ingesteld, overgeslagen'); return
    data = json.dumps({'token': c['mail_token'], 'to': c['ontvangers'], 'subject': c['onderwerp'], 'html': body}).encode()
    req = urllib.request.Request(c['mail_url'], data=data, headers={'Content-Type': 'application/json'})
    print('E-mail:', urllib.request.urlopen(req, timeout=60).read().decode()[:200])


def push():
    g = lambda *a: subprocess.run(['git', '-C', ROOT, *a], capture_output=True, text=True)
    g('add', 'docs/statistiek', 'tools/seo/metingen')
    if not g('diff', '--cached', '--quiet').returncode:
        print('Geen wijzigingen om te pushen'); return
    g('commit', '-m', f'Statistieken bijgewerkt {dt.date.today()}')
    g('pull', '--rebase', 'origin', 'claude/redesign')
    r = g('push', 'origin', 'claude/redesign')
    print('Push:', 'ok' if r.returncode == 0 else r.stderr[-300:])


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    for a in ('posities', 'gsc', 'mail', 'push', 'build'):
        ap.add_argument('--' + a, action='store_true')
    a = ap.parse_args()
    c = cfg()
    if a.posities:
        sys.path.insert(0, HERE)
        import posities_meten
        posities_meten.main()
    g = gsc_fetch(c) if a.gsc else None
    g = g or gsc_latest()
    R = rankings()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(page(dashboard(g, R), c['wachtwoord']))
    print('Dashboard:', OUT)
    if a.mail:
        send(c, email_html(g, R))
    if a.push:
        push()
