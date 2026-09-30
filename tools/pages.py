"""Paginatypes van de nieuwe site: homepage en locatiepagina's."""
from render import (ICON_ARROW, keywords, post_card, LOCS, P, SITE, booking, clock, content, coords, esc, facts, faq_block, faq_schema,
                    nearest, nl_map, page, pricing, province_list)

GENERAL_FAQ = [
    ('Wat is een outdoor escape room?',
     '<p>Bij een outdoor escape room los je escape-puzzels op in de stad in plaats van in een afgesloten kamer. Bij The Hunt krijgt elk team een gametas met puzzels en een GameApp. Wie alle puzzels oplost, vindt het geheime extractiepunt, terwijl de Hunters jullie proberen te pakken.</p>'),
    ('Met hoeveel personen kun je The Hunt spelen?',
     f'<p>Vanaf {P["min_people"]} personen. We verdelen de groep in teams van ongeveer zes. We hebben al groepen van meer dan 100 personen begeleid; tot ongeveer {P["max_people"]} deelnemers is mogelijk.</p>'),
    ('Wat kost The Hunt?',
     f'<p>Tot en met {P["base_max_people"]} personen betaal je €{P["base"]}. Daarboven rekenen we €{P["per_person"]} per persoon. Opdrachten op maat kosten €{P["custom"]} extra. Alle prijzen zijn exclusief btw; inclusief btw is dat €{P["base_incl"]}, €{P["per_person_incl"]} per persoon en €{P["custom_incl"]}.</p>'),
    ('Hoe lang duurt het spel?', '<p>Het spel duurt 90 minuten. Reken inclusief ontvangst, uitleg en afronding op ongeveer twee uur.</p>'),
    ('Gaat The Hunt door als het regent?', '<p>Ja. The Hunt is een actief uitje waarbij je de hele tijd in beweging blijft. Trek wel kleding aan die tegen een buitje kan.</p>'),
    ('Is The Hunt geschikt voor kinderen?', '<p>Ja. De puzzels variëren van eenvoudig tot moeilijk, dus kinderen vanaf 8 jaar kunnen goed meedoen. En als boefje opgejaagd worden door de Hunters vinden ze vaak extra spannend.</p>'),
    ('Lijkt The Hunt op Hunted of Jachtseizoen?', '<p>Ja, daar is het spel op geïnspireerd. Jullie zijn op de vlucht. Onze Hunters krijgen elke 10 minuten jullie locatie door en gaan op basis daarvan jagen op jullie.</p>'),
    ('Werken jullie met live Hunters?', '<p>Ja, dat klopt. De spelleider(s) die de uitleg doet, wordt na 10 minuten de Hunter die op jullie gaat jagen. Wellicht is het slim om die persoon te vriend te houden ;-)</p>'),
    ('Is er ook een winnaar?', '<p>Jazeker. Wanneer het spel voorbij is en elk team op het extractiepunt is aangekomen, gaan we over tot het bekronen van het winnende team.</p>'),
]

GALLERY = ['2026/09/the-hunt-hunter-en-groepen-1600.jpg', '2026/09/the-hunt-spelen-in-de-regen-800.jpg',
           '2026/09/the-hunt-nijmegen-centrum-800.jpg', '2026/09/the-hunt-nijmegen-waalkade-waalbrug-800.jpg',
           '2026/09/the-hunt-drachten-speluitleg-800.jpg', '2026/04/16-april-Escape-Game-The-Hunt-Groningen-768x576.jpeg',
           '2026/04/Groep-utrecht-toppers-768x576.jpeg', '2026/04/Escape-Game-The-Hunt-Eindhoven-768x576.jpeg']
GALLERY_ALT = ['Een Hunter houdt de groepen in de gaten', 'Een Hunter in de regen: het spel gaat gewoon door',
               'Speluitleg in het centrum van Nijmegen', 'Groep aan de Waalkade in Nijmegen', 'Speluitleg in Drachten',
               'Teams in Groningen', 'Groep in Utrecht', 'The Hunt in Eindhoven']

VIDEO = '''<div class="media-frame trailer" data-vimeo="1113340430">
<img src="/assets/uploads/2026/09/the-hunt-team-puzzelt-800.jpg" alt="Een team puzzelt onder tijdsdruk" loading="lazy" width="800" height="602">
<button type="button" class="play" aria-label="Bekijk de trailer van The Hunt"><span class="play-icon" aria-hidden="true"></span>Bekijk de trailer</button>
<p class="trailer-note">De video wordt pas geladen als je op afspelen klikt (Vimeo).</p>
</div>'''


def home():
    q = ''.join(f'<figure class="quote"><span class="stars" aria-label="5 sterren">★★★★★</span><blockquote><p>{esc(t)}</p></blockquote><figcaption>{esc(h)}</figcaption></figure>'
                for h, t in SITE['reviews'])
    gal = ''.join(f'<img src="/assets/uploads/{g}" alt="{a}" loading="lazy" width="768" height="576">' for g, a in zip(GALLERY, GALLERY_ALT))
    body = f'''
<section class="hero grid-bg">
<div class="hero-media right"><img src="/assets/uploads/2026/09/the-hunt-hunter-rugtas-1600.jpg" alt="Een Hunter met rugtas kijkt naar de groepen" fetchpriority="high" width="1200" height="1600" style="object-position:center 55%"></div>
<div class="wrap">
<span class="coords"><span class="ping" aria-hidden="true"></span>Outdoor escape room · te spelen in heel Nederland</span>
<h1>Ontsnap aan de <em>Hunters</em>. Midden in jullie stad.</h1>
<p class="lede">The Hunt is de escape game die je buiten speelt. Los in teams zes puzzels op, kraak de GPS-code van het extractiepunt en blijf 90 minuten uit handen van de Hunters. Geïnspireerd op Hunted en Jachtseizoen.</p>
<div class="hero-cta"><a class="btn btn-signal" href="#boeken">Boek The Hunt {ICON_ARROW}</a><a class="btn btn-ghost" href="#locaties">Kies je stad</a></div>
{facts([('90 min', 'speeltijd'), ('8+', 'personen'), ('€' + str(P['base']), 'ex. btw · t/m 17 pers.'), ('Heel NL', 'speelgebied')])}
</div>
</section>

<section class="section dark grid-bg" id="zo-werkt-het" aria-labelledby="werkt-titel">
<div class="wrap">
<div class="head"><span class="label">De spelklok</span><h2 id="werkt-titel">Zo verloopt een Hunt</h2>
<p class="lede">Een kat-en-muisspel van 90 minuten. Jullie puzzelen en rennen, de Hunters kijken elke tien minuten waar jullie zijn.</p></div>
{clock()}
</div>
</section>

<section class="section" aria-labelledby="stad-titel">
<div class="wrap split">
<div class="stack">
<span class="label">Geen kamer, wel een speelveld</span>
<h2 id="stad-titel">De hele stad is jullie escape room</h2>
<p>Jullie worden niet opgesloten. Jullie bewegen vrij door het centrum en kiezen zelf je route, terwijl de Hunters steeds dichterbij komen. Wie slim puzzelt maar vergeet om uit het zicht te blijven, wordt alsnog gepakt.</p>
<ul class="checks">
<li>Alles zit in de gametas en op je telefoon. Er liggen geen puzzels verstopt in de stad.</li>
<li>In de GameApp zien jullie het speelveld, voeren jullie antwoorden in en kopen jullie hints.</li>
<li>Puzzels van eenvoudig tot moeilijk, dus ook leuk met kinderen vanaf 8 jaar.</li>
<li>Het spel gaat gewoon door als het regent.</li>
</ul>
</div>
{VIDEO}
</div>
</section>

<section class="section paper" aria-labelledby="wie-titel">
<div class="wrap">
<div class="head"><span class="label">Voor wie</span><h2 id="wie-titel">Voor elke groep vanaf 8 personen</h2></div>
<div class="cards four">
<div class="card has-img"><img src="/assets/uploads/2026/09/the-hunt-uitleg-nijmegen-800.jpg" alt="Speluitleg voor een bedrijf in Nijmegen" loading="lazy" width="600" height="800"><h3>Teamuitje en bedrijfsuitje</h3><p>Samenwerken onder druk, met een eindstand die nog weken besproken wordt. Ook voor personeelsuitjes en grote afdelingen.</p></div>
<div class="card has-img"><img src="/assets/uploads/2026/04/Groep-Nijmegen-Vrijgezellenfeest-768x576.jpeg" alt="Vrijgezellenfeest in Nijmegen" loading="lazy" width="768" height="576"><h3>Vrijgezellenfeest</h3><p>Actief, competitief en goed te combineren met een borrel of diner in de stad.</p></div>
<div class="card has-img"><img src="/assets/uploads/2026/04/Groningen-teams-768x576.jpeg" alt="Teams in Groningen" loading="lazy" width="768" height="576"><h3>Vrienden en familie</h3><p>Puzzelaars en lopers hebben allebei een rol. Kinderen vanaf 8 jaar kunnen meedoen.</p></div>
<a class="card has-img" href="/op-maat-gemaakt/"><img src="/assets/uploads/2026/05/groep-escape-game-the-hunt-op-maat-gemaakt-800.jpg" alt="Groep die een op maat gemaakte Hunt speelde" loading="lazy" width="800" height="600"><h3>Op maat gemaakt</h3><p>Wij verwerken vragen over jullie eigen bedrijf of groep in de opdrachten, voor €{P['custom']} extra.</p><span class="more">Hoe werkt dat →</span></a>
</div>
</div>
</section>

<section class="section" id="prijzen" aria-labelledby="prijs-titel">
<div class="wrap">
<div class="head"><span class="label">Prijzen</span><h2 id="prijs-titel">Eén vaste prijs tot 17 personen</h2></div>
{pricing()}
</div>
</section>

<section class="section navy" aria-labelledby="review-titel">
<div class="wrap">
<div class="head"><span class="label">Ervaringen</span><h2 id="review-titel">Wat groepen zeggen na hun Hunt</h2></div>
<div class="quotes">{q}</div>
</div>
</section>

<section class="section" id="locaties" aria-labelledby="loc-titel">
<div class="wrap">
<div class="head"><span class="label">Speelsteden</span><h2 id="loc-titel">Te spelen in heel Nederland</h2>
<p class="lede">We spelen in principe overal, zolang we er een speelveld kunnen maken. Hieronder staan onze vaste speelsteden met startlocatie, route en voorbeeldprogramma. Staat jullie plaats er niet tussen? Dan komen we naar jullie toe.</p></div>
<div class="locations">{nl_map()}{province_list()}</div>
</div>
</section>

<section class="section paper" aria-labelledby="foto-titel">
<div class="wrap">
<div class="head"><span class="label">Sfeerimpressie</span><h2 id="foto-titel">Groepen die jullie voorgingen</h2></div>
<div class="gallery">{gal}</div>
<p style="margin-top:20px"><a class="btn btn-line" href="/escape-game-the-hunt-fotopagina/">Meer foto's {ICON_ARROW}</a></p>
</div>
</section>

<section class="section" aria-labelledby="faq-titel">
<div class="wrap">
<div class="head"><span class="label">Veelgestelde vragen</span><h2 id="faq-titel">Goed om te weten</h2></div>
{faq_block(GENERAL_FAQ)}
<p style="margin-top:20px"><a href="/veelgestelde-vragen/">Alle veelgestelde vragen</a></p>
</div>
</section>

{booking()}'''
    return page(path='/', title='Escape Game The Hunt | Outdoor escape room in heel Nederland',
                description='The Hunt is de outdoor escape room geïnspireerd op Hunted en Jachtseizoen. Ontsnap in 90 minuten aan de Hunters, te spelen in heel Nederland. Vanaf 8 personen.',
                body=body, schema=[faq_schema(GENERAL_FAQ),
                                   {'@context': 'https://schema.org', '@type': 'WebSite', 'name': SITE['name'], 'url': SITE['url']}],
                head_extra='<meta name="google-site-verification" content="GNl7i1eW7qRSl_ednpGUEVZconmYRnp_xq_5k6pT__M">\n')


def location(loc):
    c = content('locaties', loc['slug'])
    city = loc['name']
    start = loc['start'] or f'Centrum van {city}'
    posts = ''
    if c['posts']:
        kw = keywords()
        cards = ''.join(post_card(p['url'], p['title'], kw.get(p['url'], p['title'])) for p in c['posts'] if p['url'] in kw)
        posts = f'''<section class="section paper" aria-labelledby="posts-titel"><div class="wrap">
<div class="head"><span class="label">Uitjes in {esc(city)}</span><h2 id="posts-titel">Meer over The Hunt in {esc(city)}</h2></div>
<div class="posts">{cards}</div></div></section>'''
    near = ''.join(f'<li><a href="{l["url"]}">{esc(l["name"])}</a></li>' for l in nearest(loc))
    crumbs = {'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': 1, 'name': 'Home', 'item': SITE['url'] + '/'},
        {'@type': 'ListItem', 'position': 2, 'name': 'Locaties', 'item': SITE['url'] + '/escape-game-the-hunt-locaties/'},
        {'@type': 'ListItem', 'position': 3, 'name': city, 'item': SITE['url'] + loc['url']}]}
    hero_img = c['og_image'] or SITE['og_image']
    body = f'''
<section class="hero compact grid-bg">
<div class="hero-media"><img src="/assets/uploads/2026/09/the-hunt-hunter-en-groepen-1600.jpg" alt="" fetchpriority="high" width="1600" height="1200"></div>
<div class="wrap">
<nav class="crumbs" aria-label="Kruimelpad"><a href="/">Home</a><span aria-hidden="true">/</span><a href="/escape-game-the-hunt-locaties/">Locaties</a><span aria-hidden="true">/</span><span>{esc(city)}</span></nav>
<span class="coords"><span class="ping" aria-hidden="true"></span>{coords(loc)} · {esc(loc['province'])}</span>
<h1>{esc(c['h1'])}</h1>
<p class="lede">{esc(c['description'])}</p>
<div class="hero-cta"><a class="btn btn-signal" href="#boeken">Boek in {esc(city)} {ICON_ARROW}</a><a class="btn btn-ghost" href="#prijzen">Bekijk prijzen</a></div>
{facts([('90 min', 'speeltijd'), ('8+', 'personen'), ('€' + str(P['base']), 'ex. btw · t/m 17 pers.'), (esc(start if len(start) < 22 else city + ' centrum'), 'startlocatie')])}
</div>
</section>

<section class="section">
<div class="wrap article">
<div class="prose">{f'<img class="city-photo" src="{loc["image"]}" alt="Escape Game The Hunt in {esc(city)}" width="800" height="600">' if loc["image"] else ''}{c['body']}</div>
<aside class="aside" aria-label="Boeken in {esc(city)}">
<div class="aside-card">
<span class="label">The Hunt {esc(city)}</span>
<h3>Jullie missie in {esc(city)}</h3>
<dl><dt>Start</dt><dd>{esc(start)}</dd><dt>Speeltijd</dt><dd>90 minuten</dd><dt>Groep</dt><dd>vanaf {P['min_people']} personen</dd><dt>Prijs</dt><dd>€{P['base']} ex. btw (€{P['base_incl']} incl.) t/m {P['base_max_people']} pers.</dd></dl>
<a class="btn btn-signal" href="#boeken">Vraag een offerte aan</a>
<a class="btn btn-ghost" href="tel:{SITE['phone']}">Bel {SITE['phone_display']}</a>
</div>
{nl_map(loc['slug'])}
</aside>
</div>
</section>

<section class="section tight paper" aria-labelledby="trailer-titel">
<div class="wrap split">
<div class="stack"><span class="label">Trailer</span><h2 id="trailer-titel">Zo ziet een Hunt eruit</h2>
<p>Teams met een gametas, puzzels onder tijdsdruk en Hunters die steeds dichterbij komen. Bekijk in de trailer hoe het spel in de stad werkt.</p>
<p><a class="btn btn-signal" href="#boeken">Boek in {esc(city)} {ICON_ARROW}</a></p></div>
{VIDEO}
</div>
</section>

<section class="section dark grid-bg" aria-labelledby="werkt-titel">
<div class="wrap">
<div class="head"><span class="label">De spelklok</span><h2 id="werkt-titel">Zo verloopt The Hunt in {esc(city)}</h2></div>
{clock(loc['start'], city)}
</div>
</section>

<section class="section" id="prijzen" aria-labelledby="prijs-titel">
<div class="wrap">
<div class="head"><span class="label">Prijzen</span><h2 id="prijs-titel">Wat kost een escape room in {esc(city)}?</h2></div>
{pricing(city)}
</div>
</section>

<section class="section paper" aria-labelledby="faq-titel">
<div class="wrap">
<div class="head"><span class="label">Veelgestelde vragen</span><h2 id="faq-titel">Vragen over The Hunt {esc(city)}</h2></div>
{faq_block(c['faq'])}
<p style="margin-top:20px"><a href="/veelgestelde-vragen/">Alle veelgestelde vragen</a>: over live Hunters, de winnaar, maatwerk, groepen en eten en drinken.</p>
</div>
</section>
{posts}
<section class="section tight" aria-labelledby="buurt-titel">
<div class="wrap">
<div class="head"><span class="label">In de buurt</span><h2 id="buurt-titel">Ook te spelen in de buurt van {esc(city)}</h2></div>
<div class="province"><ul>{near}</ul></div>
<p style="margin-top:16px"><a href="/#locaties">Bekijk alle speelsteden</a></p>
</div>
</section>

{booking(city)}'''
    return page(path=loc['url'], title=c['title'], description=c['description'], body=body, og_image=hero_img,
                schema=[crumbs, faq_schema(c['faq'])], active='/escape-game-the-hunt-locaties/')
