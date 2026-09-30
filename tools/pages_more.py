"""Overige paginatypes: blogs, losse pagina's, nieuwsoverzicht, categorieën."""
import glob
import json
import os

from pages import VIDEO  # noqa: F401  (hergebruikt op sommige pagina's)
from render import (ICON_ARROW, LOCS, P, ROOT, SITE, booking, esc, faq_block, faq_schema, nl_map, page, pricing,
                    province_list)

LOC_BY_SLUG = {l['slug']: l for l in LOCS}


def all_pages():
    out = []
    for fp in sorted(glob.glob(os.path.join(ROOT, 'src', 'content', 'pages', '*.json'))):
        d = json.load(open(fp, encoding='utf-8'))
        d['city'] = next((LOC_BY_SLUG[c] for c in d['categories'] if c in LOC_BY_SLUG), None)
        d['kind'] = 'post' if d['categories'] else 'page'
        out.append(d)
    return out


def posts_sorted(pages_):
    return sorted((p for p in pages_ if p['kind'] == 'post'), key=lambda p: p['published'], reverse=True)


def short_title(p):
    return p['title'].replace(' - Escape Game The Hunt', '')


def thumb(src):
    """533x400-variant van een WordPress-upload als die bestaat."""
    if not src:
        return SITE['og_image']
    base, ext = os.path.splitext(src)
    small = base + '-533x400' + ext
    return small if os.path.exists(os.path.join(ROOT, small.lstrip('/'))) else src


def post_cards(posts):
    return '<div class="posts">%s</div>' % ''.join(
        f'<a class="post" href="{p["path"]}"><img src="{thumb(p["og_image"])}" alt="" loading="lazy" width="533" height="400">'
        f'<span>{esc(short_title(p))}</span></a>' for p in posts)


def hero(title, lede, crumbs, label=None, cta=True):
    trail = '<span aria-hidden="true">/</span>'.join(
        (f'<a href="{h}">{esc(t)}</a>' if h else f'<span>{esc(t)}</span>') for t, h in crumbs)
    lbl = f'<span class="coords"><span class="ping" aria-hidden="true"></span>{label}</span>' if label else ''
    buttons = (f'<div class="hero-cta"><a class="btn btn-signal" href="#boeken">Boek The Hunt {ICON_ARROW}</a>'
               f'<a class="btn btn-ghost" href="/#locaties">Kies je stad</a></div>') if cta else ''
    lede_html = f'<p class="lede">{esc(lede)}</p>' if lede else ''
    return f'''<section class="hero compact grid-bg">
<div class="hero-media"><img src="/assets/uploads/2025/06/escape-the-hunt-juichend-team-game-kleiner.jpg" alt="" fetchpriority="high" width="1292" height="969"></div>
<div class="wrap">
<nav class="crumbs" aria-label="Kruimelpad">{trail}</nav>
{lbl}
<h1>{esc(title)}</h1>
{lede_html}
{buttons}
</div>
</section>'''


def crumb_schema(items):
    return {'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': i + 1, 'name': t, 'item': SITE['url'] + (h or '')}
        for i, (t, h) in enumerate(items) if h or i == len(items) - 1]}


def facts_card(title, label, buttons):
    return f'''<div class="aside-card">
<span class="label">{label}</span>
<h3>{title}</h3>
<dl><dt>Speeltijd</dt><dd>90 minuten</dd><dt>Groep</dt><dd>vanaf {P['min_people']} personen</dd><dt>Prijs</dt><dd>€{P['base']} t/m {P['base_max_people']} pers.</dd></dl>
{buttons}
</div>'''


def post(p, pages_):
    city = p['city']
    date = (p['published'] or '')[:10]
    shown = '%s-%s-%s' % (date[8:10], date[5:7], date[:4]) if date else ''
    crumbs = [('Home', '/'), ('Nieuws', '/escape-game-the-hunt-nieuws/'), (short_title(p), p['path'])]
    label = (f'{esc(city["name"])} · ' if city else '') + (f'<time datetime="{date}">{shown}</time>' if date else 'Nieuws')
    if city:
        card = facts_card(f'Escape room {esc(city["name"])}', f'Speel in {esc(city["name"])}',
                          f'<a class="btn btn-signal" href="{city["url"]}">Alles over {esc(city["name"])}</a>'
                          f'<a class="btn btn-ghost" href="#boeken">Vraag een offerte aan</a>')
    else:
        card = facts_card('Speel The Hunt', 'The Hunt', '<a class="btn btn-signal" href="#boeken">Vraag een offerte aan</a>'
                                                        '<a class="btn btn-ghost" href="/#locaties">Kies je stad</a>')
    related = [q for q in posts_sorted(pages_) if q is not p and city and q['city'] is city][:6]
    rel_html = ''
    if related:
        rel_html = f'''<section class="section paper" aria-labelledby="rel-titel"><div class="wrap">
<div class="head"><span class="label">Meer over {esc(city["name"])}</span><h2 id="rel-titel">Andere uitjes in {esc(city["name"])}</h2></div>
{post_cards(related)}</div></section>'''
    img = p['og_image']
    body = f'''{hero(p['h1'] or short_title(p), p['description'], crumbs[:2] + [(short_title(p), None)], label, cta=False)}
<section class="section">
<div class="wrap article">
<article class="prose">
{p['body']}
</article>
<aside class="aside" aria-label="Boeken">{card}{nl_map(city['slug']) if city else ''}</aside>
</div>
</section>
{rel_html}
{booking(city['name'] if city else None)}'''
    art = {'@context': 'https://schema.org', '@type': 'BlogPosting', 'headline': short_title(p), 'description': p['description'],
           'datePublished': p['published'], 'dateModified': p['modified'] or p['published'],
           'image': SITE['url'] + (img or SITE['og_image']), 'mainEntityOfPage': SITE['url'] + p['path'],
           'publisher': {'@id': SITE['url'] + '/#organization'}}
    return page(path=p['path'], title=p['title'], description=p['description'], body=body, og_image=img or None,
                schema=[crumb_schema(crumbs), art], active='/escape-game-the-hunt-nieuws/')


def section(label, title, inner, cls='section'):
    return f'<section class="{cls}"><div class="wrap"><div class="head"><span class="label">{label}</span><h2>{title}</h2></div>{inner}</div></section>'


def simple(p, extra_before='', extra_after='', body_html=None, schema=(), lede=None, form=True, active=None, city=None):
    title = p['h1'] or short_title(p)
    crumbs = [('Home', '/'), (title, p['path'])]
    html_ = p['body'] if body_html is None else body_html
    prose = f'<section class="section"><div class="wrap"><div class="prose">{html_}</div></div></section>' if html_ else ''
    body = f'''{hero(title, p['description'] if lede is None else lede, [('Home', '/'), (title, None)])}
{extra_before}
{prose}
{extra_after}
{booking(city) if form else ''}'''
    return page(path=p['path'], title=p['title'], description=p['description'], body=body, og_image=p['og_image'] or None,
                robots=p['robots'] if 'noindex' in (p['robots'] or '') else None,
                schema=[crumb_schema(crumbs), *schema], active=active or p['path'])


def prices(p):
    rest = p['body'][p['body'].find('<h2>Maak'):] if '<h2>Maak' in p['body'] else ''
    return simple(p, extra_before=section('Prijzen', 'Eén vaste prijs tot 17 personen', pricing()), body_html=rest,
                  lede=f'Tot en met {P["base_max_people"]} personen betaal je €{P["base"]}. Daarboven €{P["per_person"]} per persoon. Alle prijzen exclusief btw.')


def contact(p):
    inner = f'''<div class="cards">
<a class="card" href="tel:{SITE['phone']}"><span class="label">Bellen</span><h3>{SITE['phone_display']}</h3><p>Voor vragen en snelle afspraken.</p></a>
<a class="card" href="mailto:{SITE['email']}"><span class="label">Mailen</span><h3>{SITE['email']}</h3><p>We reageren binnen 1 werkdag.</p></a>
<div class="card"><span class="label">Adres</span><h3>Giethoorn</h3><p>{SITE['address']}<br>KvK {SITE['kvk']}</p></div>
</div>'''
    return simple(p, extra_before=section('Contact', 'Neem contact met ons op', inner), body_html='',
                  lede='Vragen over The Hunt of een offerte nodig? Bel, mail of vul het formulier in.')


def faq_page(p):
    blocks, allq = [], []
    for title, items in p['faq_groups']:
        allq += items
        blocks.append(section('Veelgestelde vragen', esc(title), faq_block(items), 'section tight'))
    return simple(p, extra_before=''.join(blocks), body_html='', schema=[faq_schema(allq)],
                  lede='Antwoorden over de GameApp, het spel, groepen en prijzen.')


def photos(p):
    imgs = ''.join(f'<img src="{i["src"] if n == 0 else thumb(i["src"])}" alt="{esc(i["alt"])}" loading="lazy" width="533" height="400">'
                   for n, i in enumerate(p['images']))
    return simple(p, extra_before=section('Sfeerimpressie', 'Groepen die jullie voorgingen', f'<div class="gallery">{imgs}</div>'),
                  body_html='', lede='Een greep uit de teams die The Hunt al speelden.')


def about(p):
    text = f'''<h2>Wie zijn wij?</h2>
<p>Escape Game The Hunt is onderdeel van {SITE['company']} uit Giethoorn. Sinds 2020 laten we groepen door steden in heel Nederland vluchten voor onze Hunters.</p>
<p>The Hunt is geïnspireerd op tv-programma's als Hunted en Jachtseizoen. Wij maakten er een spel van dat je met je eigen groep speelt: zes escape-puzzels, een GameApp en Hunters die elke tien minuten jullie locatie doorkrijgen.</p>
<p>We spelen in principe overal waar we een speelveld kunnen maken. Voor grote groepen combineren we The Hunt met onze andere spellen.</p>
<h2>Samenwerken met ons?</h2>
<p>We zoeken <a href="/werken-bij/">spelleiders en locatie-eigenaren</a> die The Hunt in hun eigen regio willen spelen.</p>'''
    return simple(p, body_html=text, lede='Het team achter Escape Game The Hunt.')


def locations_overview(p):
    cards = ''.join(
        f'<a class="card" href="{l["url"]}"><span class="label">{esc(l["province"])}</span><h3>Escape room {esc(l["name"])}</h3>'
        f'<p>{"Start: " + esc(l["start"]) if l["start"] else "Start in het centrum van " + esc(l["name"])}</p>'
        f'<span class="more">Bekijk {esc(l["name"])} →</span></a>'
        for l in sorted(LOCS, key=lambda l: l['name']))
    inner = f'<div class="locations">{nl_map()}{province_list()}</div>'
    return simple(p, extra_before=section('Speelsteden', 'Te spelen in heel Nederland', inner)
                  + section('Alle steden', 'Kies jullie speelstad', f'<div class="cards">{cards}</div>', 'section paper'),
                  body_html='', lede='We spelen overal waar we een speelveld kunnen maken. Dit zijn onze vaste speelsteden.',
                  active='/escape-game-the-hunt-locaties/')


def news(n, total, posts):
    path = '/escape-game-the-hunt-nieuws/' + (f'page/{n}/' if n > 1 else '')
    crumbs = [('Home', '/'), ('Nieuws', '/escape-game-the-hunt-nieuws/')] + ([(f'Pagina {n}', path)] if n > 1 else [])
    shown = [(t, h if i < len(crumbs) - 1 else None) for i, (t, h) in enumerate(crumbs)]
    links = []
    for i in range(1, total + 1):
        href = '/escape-game-the-hunt-nieuws/' + (f'page/{i}/' if i > 1 else '')
        cur = ' aria-current="page"' if i == n else ''
        links.append(f'<a class="btn {"btn-signal" if i == n else "btn-line"}" href="{href}"{cur}>{i}</a>')
    body = f'''{hero('Nieuws en uitjes' + (f' · pagina {n}' if n > 1 else ''), 'Tips voor teamuitjes, bedrijfsuitjes en vrijgezellenfeesten met The Hunt, per stad.', shown, cta=False)}
<section class="section"><div class="wrap">{post_cards(posts)}
<nav class="pager" aria-label="Paginering">{''.join(links)}</nav></div></section>
{booking()}'''
    return page(path=path, title='Nieuws' + (f' - pagina {n}' if n > 1 else '') + ' - Escape Game The Hunt',
                description='Nieuws, tips en ideeën voor uitjes met Escape Game The Hunt in heel Nederland.',
                body=body, schema=[crumb_schema(crumbs)], active='/escape-game-the-hunt-nieuws/')


def category(slug, name, posts):
    loc = LOC_BY_SLUG.get(slug)
    crumbs = [('Home', '/'), ('Nieuws', '/escape-game-the-hunt-nieuws/'), (name, None)]
    link = (f'<p style="margin-bottom:24px"><a class="btn btn-signal" href="{loc["url"]}">Speel The Hunt in {esc(name)} {ICON_ARROW}</a></p>'
            if loc else '')
    body = f'''{hero(name, f'Berichten over The Hunt in {name}.' if loc else 'Algemeen nieuws over The Hunt.', crumbs, cta=False)}
<section class="section"><div class="wrap">{link}{post_cards(posts)}</div></section>
{booking(loc['name'] if loc else None)}'''
    return page(path=f'/category/{slug}/', title=f'{name} - Escape Game The Hunt',
                description=(f'Nieuws en blogs over Escape Game The Hunt in {name}.' if loc
                             else 'Algemeen nieuws over Escape Game The Hunt.'),
                body=body, robots='noindex, follow', active='/escape-game-the-hunt-nieuws/')


def apply_block():
    return f'''<section class="section dark grid-bg"><div class="wrap booking">
<div class="stack"><span class="label">Solliciteren</span><h2>Interesse? Neem contact op</h2>
<p class="lede">Stuur een korte motivatie en je woonplaats. We nemen snel contact met je op.</p></div>
<div class="stack contact-lines"><a href="mailto:{SITE['email']}?subject=Sollicitatie%20The%20Hunt">{SITE['email']}</a><a href="tel:{SITE['phone']}">{SITE['phone_display']}</a></div>
</div></section>'''


def thanks():
    crumbs = [('Home', '/'), ('Bedankt', None)]
    body = f'''{hero('Bedankt voor je aanvraag!', 'We hebben je aanvraag ontvangen en nemen binnen 1 werkdag contact met je op met een offerte op maat.', crumbs, cta=False)}
<section class="section"><div class="wrap stack">
<p>Heb je haast of wil je nog iets toevoegen? Bel ons op <a href="tel:{SITE['phone']}">{SITE['phone_display']}</a> of mail naar <a href="mailto:{SITE['email']}">{SITE['email']}</a>.</p>
<p><a class="btn btn-line" href="/">Terug naar de homepage</a></p>
</div></section>'''
    return page(path='/bedankt/', title='Bedankt voor je aanvraag - Escape Game The Hunt',
                description='Bedankt voor je aanvraag voor Escape Game The Hunt.', body=body, robots='noindex, follow')
