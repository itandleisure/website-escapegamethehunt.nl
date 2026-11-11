"""Overige paginatypes: blogs, losse pagina's, nieuwsoverzicht, categorieën."""
import glob
import json
import os

from pages import VIDEO  # noqa: F401  (hergebruikt op sommige pagina's)
from render import (ADS_CONVERSIE_HEAD, ICON_ARROW, with_field_map, LOCS, OUT, P, ROOT, SITE, booking, esc, faq_block, faq_schema, nl_map, page, post_card,
                    pricing, province_list)

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
    return small if os.path.exists(os.path.join(OUT, small.lstrip('/'))) else src


def post_cards(posts):
    return '<div class="posts">%s</div>' % ''.join(
        post_card(p['path'], short_title(p), p.get('keyword') or short_title(p)) for p in posts)


def hero(title, lede, crumbs, label=None, cta=True, img=None):
    trail = '<span aria-hidden="true">/</span>'.join(
        (f'<a href="{h}">{esc(t)}</a>' if h else f'<span>{esc(t)}</span>') for t, h in crumbs)
    lbl = f'<span class="coords"><span class="ping" aria-hidden="true"></span>{label}</span>' if label else ''
    buttons = (f'<div class="hero-cta"><a class="btn btn-signal" href="#boeken">Boek The Hunt {ICON_ARROW}</a>'
               f'<a class="btn btn-ghost" href="/#locaties">Kies je stad</a></div>') if cta else ''
    lede_html = f'<p class="lede">{esc(lede)}</p>' if lede else ''
    return f'''<section class="hero compact grid-bg">
<div class="hero-media"><img src="{img or '/assets/uploads/2026/09/the-hunt-juichende-groep-1600.jpg'}" alt="{'Een Hunter en teams tijdens The Hunt' if img and 'hunter' in img else 'Een juichende groep na het spelen van The Hunt'}" fetchpriority="high" width="1600" height="1201"></div>
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
<dl><dt>Speeltijd</dt><dd>90 minuten</dd><dt>Groep</dt><dd>{P['min_people']} tot {P['max_people']}+ personen</dd><dt>Prijs</dt><dd>€{P['base']} ex. btw (€{P['base_incl']} incl.) t/m {P['base_max_people']} pers.</dd></dl>
{buttons}
</div>'''


def post(p, pages_):
    city = p['city']
    date = (p['published'] or '')[:10]
    shown = '%s-%s-%s' % (date[8:10], date[5:7], date[:4]) if date else ''
    crumbs = [('Home', '/'), ('Nieuws', '/escape-game-the-hunt-nieuws/'), (short_title(p), p['path'])]
    label = f'The Hunt in {esc(city["name"])}' if city else 'Nieuws'
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
{with_field_map(city, p['body'])}{post_faq(p)}
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
                schema=[crumb_schema(crumbs), art] + ([faq_schema(p['faq'])] if p.get('faq') else []), active='/escape-game-the-hunt-nieuws/')


def post_faq(p):
    if not p.get('faq'):
        return ''
    return f'\n<h2>Veelgestelde vragen</h2>\n{faq_block(p["faq"])}'


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
    return simple(p, extra_before=section('Prijzen', f'Eén vaste prijs t/m {P["base_max_people"]} personen', pricing()), body_html=rest,
                  lede=f'Tot en met {P["base_max_people"]} personen betaal je €{P["base"]}. Daarboven €{P["per_person"]} per extra persoon. Exclusief btw (inclusief: €{P["base_incl"]} en €{P["per_person_incl"]} per extra persoon). Ook groepen van 100 personen of meer zijn welkom, tot ongeveer {P["max_people"]} deelnemers.')


def contact(p):
    inner = f'''<div class="cards">
<a class="card" href="tel:{SITE['phone']}"><span class="label">Bellen</span><h3>{SITE['phone_display']}</h3><p>Voor vragen en snelle afspraken.</p></a>
<a class="card" href="mailto:{SITE['email']}"><span class="label">Mailen</span><h3>{SITE['email']}</h3><p>We reageren binnen 24 uur.</p></a>
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
                  lede='Antwoorden over het spel, groepen en prijzen.')


def photos(p):
    imgs = ''.join(f'<img src="{i["src"] if n == 0 else thumb(i["src"])}" alt="{esc(i["alt"])}" loading="lazy" width="533" height="400">'
                   for n, i in enumerate(p['images']))
    return simple(p, extra_before=section('Sfeerimpressie', 'Groepen die jullie voorgingen', f'<div class="gallery">{imgs}</div>'),
                  body_html='', lede='Een greep uit de teams die The Hunt al speelden.')


def about(p):
    text = f'''<img src="/assets/uploads/2026/09/the-hunt-spelleiders-1600.jpg" alt="Spelleiders van Escape Game The Hunt" width="1600" height="901">
<h2>Wie zitten er achter The Hunt?</h2>
<p>Escape Game The Hunt is onderdeel van {SITE['company']} uit Giethoorn. Sinds 2020 laten we groepen door steden in heel Nederland vluchten voor onze Hunters.</p>
<p>The Hunt is geïnspireerd op tv-programma's als Hunted en Jachtseizoen. Wij maakten er een eigen spel van: de zes escape-puzzels, de GameApp, de gametassen en het speelveld in elke stad zijn door ons bedacht en worden door ons onderhouden. The Hunt speel je dus alleen bij ons.</p>
<h2>Ontwikkeld in Giethoorn, gespeeld in jullie stad</h2>
<p>Vanuit Giethoorn ontwikkelen we het spel en zorgen we dat het in elke stad op dezelfde manier wordt gespeeld. De begeleiding op de dag zelf doen spelleiders uit jullie stad of regio. Zo kent de Hunter die achter jullie aan zit de stad op zijn duimpje.</p>
<h2>Iedere spelleider door ons opgeleid</h2>
<p>Of jullie nu in Den Haag, Groningen of Maastricht spelen: elke spelleider is door ons getraind, werkt met ons spelmateriaal en volgt hetzelfde draaiboek. In een aantal steden doen we dat samen met een vaste lokale partner, die The Hunt in zijn of haar eigen stad runt. Hetzelfde spel en dezelfde kwaliteit, met iemand die de stad echt kent.</p>
<p>We spelen in principe overal waar we een speelveld kunnen maken. Voor grote groepen combineren we The Hunt met onze andere spellen.</p>
<h2>Samenwerken met ons?</h2>
<p>We zoeken <a href="/werken-bij/">spelleiders en locatie-eigenaren</a> die The Hunt in hun eigen regio willen spelen.</p>'''
    return simple(p, body_html=text, lede='Ons eigen spel, begeleid door spelleiders uit jullie stad.')


def locations_overview(p):
    inner = f'<div class="locations">{nl_map()}{province_list()}</div>'
    return simple(p, extra_before=section('Speelsteden', 'Te spelen in heel Nederland', inner),
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


def apply_block(path=''):
    """Sollicitatieformulier onder de vacaturepagina's. Zelfde verzending als het boekingsformulier
    (Google Sheet + e-mail via data-google, FormSubmit als reserve), maar zonder Ads-conversie."""
    keuzes = ['Spelleider (bijbaan / part-time)', 'Spelleider (full-time)', 'Locatie-eigenaar']
    gekozen = keuzes[2] if 'locatie-eigenaar' in path else keuzes[0]
    radios = ''.join(f'<label><input type="radio" name="functie" value="{esc(k)}"{" checked" if k == gekozen else ""}> {esc(k)}</label>'
                     for k in keuzes)
    return f'''<section class="section dark grid-bg" id="solliciteren" aria-labelledby="solliciteren-titel"><div class="wrap booking">
<div class="stack"><span class="label">Solliciteren</span><h2 id="solliciteren-titel">Word ook onderdeel van ons team</h2>
<p class="lede">Vul het formulier in met een korte motivatie. We nemen zo snel mogelijk contact met je op.</p>
<p>Liever eerst even bellen of mailen? Dat kan ook.</p>
<div class="contact-lines"><a href="tel:{SITE['phone']}">{SITE['phone_display']}</a><a href="mailto:{SITE['email']}?subject=Sollicitatie%20The%20Hunt">{SITE['email']}</a></div>
</div>
<form class="form" data-booking data-google="{esc(SITE['google_form_url'])}" data-next="/werken-bij/bedankt/" method="POST">
<input type="hidden" name="form" value="sollicitatie">
<div class="field"><label for="s-naam">Naam</label><input id="s-naam" name="naam" autocomplete="name" required></div>
<div class="field"><label for="s-leeftijd">Leeftijd</label><input id="s-leeftijd" type="number" name="leeftijd" min="15" max="99" inputmode="numeric" required></div>
<div class="field"><label for="s-mail">E-mailadres</label><input id="s-mail" type="email" name="email" autocomplete="email" required></div>
<div class="field"><label for="s-tel">Telefoonnummer</label><input id="s-tel" type="tel" name="telefoon" autocomplete="tel" required></div>
<fieldset class="field full"><legend>Functie</legend><div class="choices">{radios}</div></fieldset>
<div class="field"><label for="s-woonplaats">Woonplaats</label><input id="s-woonplaats" name="woonplaats" autocomplete="address-level2" required></div>
<div class="field"><label for="s-stad">Voorkeursstad <span class="opt">(optioneel)</span></label><input id="s-stad" name="stad" placeholder="Waar wil je The Hunt spelen?"></div>
<div class="field full"><label for="s-motivatie">Korte motivatie</label><textarea id="s-motivatie" name="bericht" placeholder="Wat lijkt je zo leuk om bij ons aan de slag te gaan?" required></textarea></div>
<div class="hp" aria-hidden="true"><label for="s-web">Laat dit veld leeg</label><input id="s-web" name="_honey" tabindex="-1" autocomplete="off"></div>
<p class="form-note error full" data-form-error hidden role="alert">Versturen is niet gelukt. Probeer het nog eens, of bel <a href="tel:{SITE['phone']}">{SITE['phone_display']}</a> of mail naar <a href="mailto:{SITE['email']}">{SITE['email']}</a>.</p>
<div class="full"><button class="btn btn-signal" type="submit">Verstuur je sollicitatie {ICON_ARROW}</button><p class="form-note">We gebruiken je gegevens alleen voor je sollicitatie. Lees de <a href="/privacyverklaring/">privacyverklaring</a>.</p></div>
</form>
</div></section>'''


def review():
    """Reviewpagina voor klanten (link in het fotoboek). Google-review als eerste keus (google_review_url in
    src/data/site.json), daarnaast een eigen formulier dat via het Apps Script in het tabblad Reviews belandt."""
    crumbs = [('Home', '/'), ('Review', None)]
    google = SITE.get('google_review_url') or ''
    sterren = ''.join(f'<label><input type="radio" name="cijfer" value="{n}"{" checked" if n == 5 else ""} required> {"★" * n}</label>'
                      for n in range(5, 0, -1))
    google_blok = (f'''<div class="stack"><span class="label">Op Google</span><h2>Laat een Google-review achter</h2>
<p>Een review op Google helpt andere groepen het meest bij het kiezen van hun uitje. Het kost je een minuutje.</p>
<p><a class="btn btn-signal" href="{esc(google)}" target="_blank" rel="noopener">Schrijf een Google-review {ICON_ARROW}</a></p>
<p class="form-note">Liever niet via Google? Vul dan hiernaast het formulier in.</p></div>''' if google else
        '''<div class="stack"><span class="label">Jullie mening</span><h2>Hoe was jullie Hunt?</h2>
<p>Vertel ons wat je ervan vond. Goede punten horen we graag, verbeterpunten nog liever.</p></div>''')
    body = f'''{hero('Bedankt voor het spelen!', 'Hoe vonden jullie The Hunt? Laat een review achter, dat helpt ons enorm.', crumbs, cta=False)}
<section class="section dark grid-bg" id="review" aria-labelledby="review-titel"><div class="wrap booking">
{google_blok}
<form class="form" data-booking data-google="{esc(SITE['google_form_url'])}" data-next="/review/bedankt/" method="POST">
<input type="hidden" name="form" value="review">
<h2 id="review-titel" class="full" style="margin:0;font-size:1.3rem">Review via onze website</h2>
<fieldset class="field full"><legend>Je cijfer</legend><div class="choices">{sterren}</div></fieldset>
<div class="field full"><label for="r-review">Je review</label><textarea id="r-review" name="review" placeholder="Wat vond je van The Hunt? Wat was het mooiste moment?" required></textarea></div>
<div class="field"><label for="r-naam">Naam</label><input id="r-naam" name="naam" autocomplete="name" required></div>
<div class="field"><label for="r-groep">Bedrijf of groep <span class="opt">(optioneel)</span></label><input id="r-groep" name="groep" autocomplete="organization"></div>
<div class="field"><label for="r-stad">Gespeeld in <span class="opt">(optioneel)</span></label><input id="r-stad" name="stad" placeholder="Bijvoorbeeld Amersfoort"></div>
<div class="field"><label for="r-datum">Datum gespeeld</label><input id="r-datum" type="date" name="datum" required></div>
<div class="field"><label for="r-spelleider">Spelleider(s) <span class="opt">(optioneel)</span></label><input id="r-spelleider" name="spelleider" placeholder="Wie was jullie spelleider?"></div>
<div class="field"><label for="r-mail">E-mailadres <span class="opt">(optioneel)</span></label><input id="r-mail" type="email" name="email" autocomplete="email"></div>
<div class="field full"><label for="r-tips">Tips of verbeterpunten <span class="opt">(optioneel, alleen voor ons)</span></label><textarea id="r-tips" name="tips" placeholder="Wat kunnen we nog beter doen?"></textarea></div>
<div class="field full"><div class="choices"><label><input type="checkbox" name="publiceren" value="ja" checked> Jullie mogen mijn review (met voornaam) op de website zetten</label></div></div>
<div class="hp" aria-hidden="true"><label for="r-web">Laat dit veld leeg</label><input id="r-web" name="_honey" tabindex="-1" autocomplete="off"></div>
<p class="form-note error full" data-form-error hidden role="alert">Versturen is niet gelukt. Probeer het nog eens, of mail je review naar <a href="mailto:{SITE['email']}">{SITE['email']}</a>.</p>
<div class="full"><button class="btn btn-signal" type="submit">Verstuur je review {ICON_ARROW}</button><p class="form-note">We gebruiken je gegevens alleen voor je review. Lees de <a href="/privacyverklaring/">privacyverklaring</a>.</p></div>
</form>
</div></section>'''
    return page(path='/review/', title='Laat een review achter - Escape Game The Hunt',
                description='Vertel ons hoe je The Hunt vond: via Google of via onze website.', body=body, robots='noindex, follow')


def thanks_review():
    crumbs = [('Home', '/'), ('Review', '/review/'), ('Bedankt', None)]
    google = SITE.get('google_review_url') or ''
    vraag = (f'''<div class="stack"><h2>Wil je ons ook helpen op Google?</h2>
<p>Je review staat nu bij ons. Wil je hem ook op Google zetten? Dan zien andere groepen hem ook, en dat helpt ons enorm. Je kunt je tekst gewoon kopiëren.</p>
<p><a class="btn btn-signal" href="{esc(google)}" target="_blank" rel="noopener">Zet je review op Google {ICON_ARROW}</a></p></div>'''
             if google else '')
    body = f'''{hero('Bedankt voor je review!', 'Fijn dat je de tijd nam. We lezen elke review, ook de tips.', crumbs, cta=False)}
<section class="section"><div class="wrap stack">
{vraag}
<p>Zin in een volgende missie? Bekijk <a href="/">alle locaties van The Hunt</a> of bel ons op <a href="tel:{SITE['phone']}">{SITE['phone_display']}</a>.</p>
<p><a class="btn btn-line" href="/">Terug naar de homepage</a></p>
</div></section>'''
    return page(path='/review/bedankt/', title='Bedankt voor je review - Escape Game The Hunt',
                description='Bedankt voor je review van Escape Game The Hunt.', body=body, robots='noindex, follow')


def thanks_apply():
    crumbs = [('Home', '/'), ('Werken bij', '/werken-bij/'), ('Bedankt', None)]
    body = f'''{hero('Bedankt voor je sollicitatie!', 'We hebben je sollicitatie ontvangen en nemen zo snel mogelijk contact met je op.', crumbs, cta=False)}
<section class="section"><div class="wrap stack">
<p>Wil je nog iets toevoegen? Bel ons op <a href="tel:{SITE['phone']}">{SITE['phone_display']}</a> of mail naar <a href="mailto:{SITE['email']}">{SITE['email']}</a>.</p>
<p><a class="btn btn-line" href="/werken-bij/">Terug naar werken bij</a></p>
</div></section>'''
    return page(path='/werken-bij/bedankt/', title='Bedankt voor je sollicitatie - Escape Game The Hunt',
                description='Bedankt voor je sollicitatie bij Escape Game The Hunt.', body=body, robots='noindex, follow')


def thanks():
    crumbs = [('Home', '/'), ('Bedankt', None)]
    body = f'''{hero('Bedankt voor je aanvraag!', 'We hebben je aanvraag ontvangen en nemen binnen 24 uur contact met je op met een offerte op maat.', crumbs, cta=False)}
<section class="section"><div class="wrap stack">
<p>Heb je haast of wil je nog iets toevoegen? Bel ons op <a href="tel:{SITE['phone']}">{SITE['phone_display']}</a> of mail naar <a href="mailto:{SITE['email']}">{SITE['email']}</a>.</p>
<p><a class="btn btn-line" href="/">Terug naar de homepage</a></p>
</div></section>'''
    return page(path='/bedankt/', title='Bedankt voor je aanvraag - Escape Game The Hunt',
                description='Bedankt voor je aanvraag voor Escape Game The Hunt.', body=body, robots='noindex, follow',
                head_extra=ADS_CONVERSIE_HEAD)


def not_found():
    """404-pagina. GitHub Pages leest _redirects/.htaccess niet; dit script stuurt bekende oude adressen door."""
    script = r"""<script>
(function () {
  var p = location.pathname, rules = [
    [/^\/wp-content\/uploads\/(.*)$/, '/assets/uploads/$1'],
    [/^\/escape-game-the-hunt-locaties\/escape-game-the-hunt-locaties\/(.*)$/, '/escape-game-the-hunt-locaties/$1'],
    [/^\/escape-game-locaties\/(.*)$/, '/escape-game-the-hunt-locaties/$1'],
    [/^\/(feed|comments\/feed|wp-login\.php|wp-admin)(\/.*)?$/, '/'],
    [/^\/category\/[^\/]+\/feed\/?$/, '/escape-game-the-hunt-nieuws/']
  ];
  for (var i = 0; i < rules.length; i++) {
    if (rules[i][0].test(p)) { location.replace(p.replace(rules[i][0], rules[i][1])); return; }
  }
})();
</script>"""
    body = f'''{hero('Deze pagina bestaat niet (meer)', 'Misschien is de pagina verhuisd. Kies hieronder je stad of ga naar de homepage.', [('Home', '/'), ('Niet gevonden', None)], cta=False)}
<section class="section"><div class="wrap">
<div class="locations">{nl_map()}{province_list()}</div>
<p style="margin-top:24px"><a class="btn btn-signal" href="/">Naar de homepage {ICON_ARROW}</a></p>
</div></section>'''
    return page(path='/404.html', title='Pagina niet gevonden - Escape Game The Hunt', description='Deze pagina bestaat niet (meer).',
                body=body, robots='noindex, follow', head_extra=script + '\n')
