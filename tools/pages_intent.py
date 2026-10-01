"""Landelijke pagina's per doelgroep: teamuitje & bedrijfsuitje, en vrijgezellenfeest. Linken naar alle steden."""
from pages import VIDEO
from pages_more import all_pages, crumb_schema, hero, section
from render import (ICON_ARROW, LOCS, P, SITE, booking, esc, faq_block, faq_schema, nl_map, page, pricing,
                    province_list)

PER_PERSON = [(8, '€49,38', '€59,74'), (12, '€32,92', '€39,83'), (17, '€23,24', '€28,11'), (25, '€22,50', '€27,23')]


U = '/assets/uploads/'
TEAM_PHOTOS = [('2026/09/de-2gemeenten-uit-jirsum-die-the-hunt-in-utrecht-hebben-gedaan-1067x800.jpeg', 'Twee gemeenten speelden The Hunt in Utrecht'),
               ('2026/09/the-hunt-drachten-van-braak-accountants-800.jpg', 'Bedrijfsuitje van een accountantskantoor in Drachten'),
               ('2026/09/the-hunt-uitleg-nijmegen-800.jpg', 'Speluitleg voor een bedrijf in Nijmegen'),
               ('2026/04/Escape-Game-The-Hunt-teamuitje-Menzis-in-Groningen-768x1024.jpeg', 'Teamuitje in Groningen'),
               ('2026/04/peter-print-groningen-toppers-768x576.jpeg', 'Bedrijfsteam in Groningen'),
               ('2026/04/apotheek-groningen-768x1024.jpeg', 'Team van een apotheek in Groningen'),
               ('2026/04/huisartsenpraktijk-de-schelfhoek-in-almelo-768x1024.jpeg', 'Team van een huisartsenpraktijk in Almelo'),
               ('2026/09/Steiger-B-Escape-game-The-Hunt-Hilversum-768x1024.jpeg', 'Teamuitje in Hilversum'),
               ('2026/04/Groningen-teams-768x576.jpeg', 'Teams in Groningen')]
VRIJ_PHOTOS = [('2026/04/Escape-Game-The-Hunt-vrijgezellenfeest-groningen-1067x800.jpeg', 'Vrijgezellenfeest in Groningen'),
               ('2026/04/Groep-Nijmegen-Vrijgezellenfeest-768x576.jpeg', 'Vrijgezellenfeest in Nijmegen'),
               ('2026/09/the-hunt-groningen-team-april-800.jpg', 'Team met gametas in Groningen'),
               ('2026/04/Tilburg-Marjolein-768x576.jpeg', 'Groep in Tilburg'),
               ('2026/09/the-hunt-puzzelen-met-gameboekje-800.jpg', 'Puzzelen met het gameboekje'),
               ('2026/09/the-hunt-tilburg-groep-800.jpg', 'Groep met paraplu’s in Tilburg'),
               ('2026/09/the-hunt-groningen-groep-april-3-800.jpg', 'Teams in Groningen'),
               ('2026/08/Groep-Sofie-Leuven-Belgie-768x1024.jpeg', 'Groep uit Leuven'),
               ('2026/09/the-hunt-groningen-groep-april-1-800.jpg', 'Groep in Groningen')]


def photo_block(label, title, photos):
    imgs = ''.join(f'<img src="{U}{p}" alt="{esc(a)}" loading="lazy" width="768" height="576">' for p, a in photos)
    return section(label, title, f'<div class="gallery">{imgs}</div><p style="margin-top:20px"><a class="btn btn-line" href="/escape-game-the-hunt-fotopagina/">Meer foto’s {ICON_ARROW}</a></p>', 'section paper')


def per_person_table():
    rows = ''.join(f'<tr><td>{n} personen</td><td>{ex}</td><td>{inc}</td></tr>' for n, ex, inc in PER_PERSON)
    return (f'<div class="examples"><span class="label">Prijs per persoon</span><table><thead><tr><th>Groep</th><th>Ex. btw</th>'
            f'<th>Incl. btw</th></tr></thead><tbody>{rows}</tbody></table>'
            f'<p class="price-note" style="color:var(--muted)">Tot en met {P["base_max_people"]} personen betaal je samen €{P["base"]} ex. btw; '
            f'daarboven €{P["per_person"]} per persoon.</p></div>')


def city_blogs(words):
    """Bestaande stadsblogs voor dit onderwerp, als links per stad."""
    out = []
    for p in all_pages():
        kw = (p.get('keyword') or '')
        if p['kind'] == 'post' and any(w in kw.lower() for w in words):
            out.append((kw, p['path']))
    out.sort()
    return '<div class="province"><ul>%s</ul></div>' % ''.join(f'<li><a href="{u}">{esc(k)}</a></li>' for k, u in out)


def cities_block(title, lede, words):
    return f'''<section class="section" id="steden" aria-labelledby="steden-titel">
<div class="wrap">
<div class="head"><span class="label">Kies jullie stad</span><h2 id="steden-titel">{title}</h2><p class="lede">{lede}</p></div>
<div class="locations">{nl_map()}{province_list()}</div>
<div class="head" style="margin-top:40px"><span class="label">Meer per stad</span><h3>Lees verder over jullie stad</h3></div>
{city_blogs(words)}
</div>
</section>'''


def programme(kind):
    return f'''<div class="examples">
<span class="label">Voorbeeldprogramma</span>
<table><tbody>
<tr><td>14:30</td><td>Ontvangst met koffie en appelgebak{', of een drankje voor de vrijgezellen' if kind == 'vrijgezellen' else ''}</td></tr>
<tr><td>15:00</td><td>Speluitleg door jullie spelleider</td></tr>
<tr><td>15:15</td><td>Start The Hunt: 10 minuten voorsprong, daarna gaan de Hunters op jacht</td></tr>
<tr><td>16:45</td><td>Einde van het spel, bekendmaking van het winnende team</td></tr>
<tr><td>17:00</td><td>{'Borrel of diner in de stad' if kind == 'team' else 'Samen eten, borrelen of verder feesten in de stad'}</td></tr>
</tbody></table>
<p class="price-note" style="color:var(--muted)">De starttijd bepalen we samen met jullie. Een borrel of diner reserveer je zelf in de buurt; wij stemmen de starttijd erop af.</p>
</div>'''


TEAM_FAQ = [
    ('Met hoeveel personen kunnen we The Hunt spelen?',
     f'<p>Vanaf {P["min_people"]} personen. We verdelen de groep in teams van ongeveer zes. We hebben al groepen van meer dan 100 personen begeleid; tot ongeveer {P["max_people"]} deelnemers is mogelijk. Willen jullie meerdere spellen spelen? Dan maken we een wisselprogramma met onze andere spellen.</p>'),
    ('Wat kost een teamuitje met The Hunt per persoon?',
     f'<p>Tot en met {P["base_max_people"]} personen betaal je samen €{P["base"]} ex. btw (€{P["base_incl"]} incl. btw). Met 12 personen is dat €32,92 per persoon ex. btw. Vanaf 18 personen betaal je €{P["per_person"]} per persoon ex. btw (€{P["per_person_incl"]} incl.).</p>'),
    ('Moet iedereen sportief zijn?',
     '<p>Nee. Jullie bepalen zelf hoe je je door de stad beweegt. Naast bewegen zijn puzzelen, navigeren, communiceren en strategisch nadenken net zo belangrijk.</p>'),
    ('Kunnen we het teamuitje combineren met eten of een borrel?',
     '<p>Ja. Een borrel of diner voor of na het spel reserveer je zelf bij een café of restaurant in de buurt; wij stemmen de starttijd erop af.</p>'),
    ('Kunnen jullie het spel op maat maken voor ons bedrijf?',
     f'<p>Ja. Jullie leveren vooraf vragen en antwoorden aan over jullie bedrijf, collega’s of kernwaarden. Die verwerken wij in de opdrachten. Dat kost €{P["custom"]} extra (€{P["custom_incl"]} incl. btw). Lees meer over <a href="/op-maat-gemaakt/">The Hunt op maat</a>.</p>'),
    ('In welke steden kunnen we spelen?',
     '<p>In principe overal waar we een speelveld kunnen maken. Op deze pagina staan onze vaste speelsteden; staat jullie plaats er niet tussen, dan komen we naar jullie toe.</p>'),
    ('Gaat het teamuitje door als het regent?',
     '<p>Ja. The Hunt is een actief uitje waarbij je de hele tijd in beweging blijft. Trek wel kleding aan die tegen een buitje kan.</p>'),
]

VRIJ_FAQ = [
    ('Met hoeveel personen kunnen we een vrijgezellenfeest met The Hunt vieren?',
     f'<p>Vanaf {P["min_people"]} personen. Tot en met {P["base_max_people"]} personen betaal je één vaste prijs. Grotere groepen spelen in meerdere teams van ongeveer zes tegen elkaar.</p>'),
    ('Wat kost een vrijgezellenfeest met The Hunt per persoon?',
     f'<p>Tot en met {P["base_max_people"]} personen betaal je samen €{P["base_incl"]} inclusief btw. Met 10 personen is dat €47,80 per persoon, met 17 personen €28,11 per persoon. Vanaf 18 personen is het €{P["per_person_incl"]} per persoon inclusief btw.</p>'),
    ('Kunnen er vragen over de bruid of bruidegom in het spel?',
     f'<p>Ja. Bij een Hunt op maat verwerken we jullie eigen vragen over de vrijgezel in de opdrachten: verhalen, foto’s, eerste ontmoeting of bekende uitspraken. Dat kost €{P["custom"]} extra (€{P["custom_incl"]} incl. btw). Lees meer over <a href="/op-maat-gemaakt/">The Hunt op maat</a>.</p>'),
    ('Kunnen we na afloop eten of borrelen?',
     '<p>Ja. The Hunt speel je in het centrum, dus eten, borrelen of verder feesten ligt op loopafstand. We denken graag mee over de planning.</p>'),
    ('Is The Hunt geschikt voor een vrouwen-, mannen- of gemengde groep?',
     '<p>Ja. Puzzelaars en lopers hebben allebei een rol, dus iedereen doet mee. Er is aan het eind een winnend team, dus het wordt vanzelf competitief.</p>'),
    ('Gaat het door als het regent?',
     '<p>Ja. The Hunt is een actief uitje waarbij je de hele tijd in beweging blijft. Trek wel kleding aan die tegen een buitje kan.</p>'),
]


def teamuitje():
    path = '/teamuitje-bedrijfsuitje/'
    crumbs = [('Home', '/'), ('Teamuitje & bedrijfsuitje', path)]
    body = f'''{hero('Teamuitje & bedrijfsuitje: The Hunt', 'Een actief teamuitje midden in de stad. Samen zes puzzels oplossen, de route bepalen en 90 minuten uit handen blijven van de Hunters. Voor teams van 8 tot ±200 personen, in heel Nederland.', [('Home', '/'), ('Teamuitje & bedrijfsuitje', None)], 'Teamuitje · bedrijfsuitje · personeelsuitje', img='/assets/uploads/2026/09/the-hunt-drachten-speluitleg-1600.jpg')}

<section class="section" aria-labelledby="waarom-titel">
<div class="wrap split">
<div class="stack">
<span class="label">Waarom The Hunt</span>
<h2 id="waarom-titel">Samenwerken ontstaat vanzelf</h2>
<p>Bij The Hunt is er geen trainer die vertelt dat jullie beter moeten communiceren. Zodra de klok loopt, ontdekken jullie dat zelf. Elk team krijgt een gametas met zes escape-puzzels en de GameApp, en moet binnen 90 minuten het geheime extractiepunt bereiken. Ondertussen krijgen de Hunters elke 10 minuten jullie locatie door.</p>
<p>Binnen elk team komen vanzelf rollen naar voren. De puzzelaar ziet verbanden die anderen missen. De navigator kiest de route. Iemand bewaakt de tijd, een ander houdt de Hunters in de gaten. Zo heeft iedereen een rol, ook collega’s die niet van rennen houden.</p>
<ul class="checks">
<li>Actief en buiten, in het centrum van de stad</li>
<li>Meerdere teams tegen elkaar, met een winnaar aan het eind</li>
<li>Voor elke groepsgrootte: vanaf 8 tot ongeveer 200 personen</li>
<li>Goed te combineren met een borrel of diner</li>
</ul>
</div>
<div class="media-frame"><img src="/assets/uploads/2026/09/the-hunt-team-puzzelt-800.jpg" alt="Een team puzzelt samen tijdens The Hunt" loading="lazy" width="800" height="602"></div>
</div>
</section>

<section class="section dark grid-bg" aria-labelledby="groot-titel">
<div class="wrap split">
<div class="media-frame"><img src="/assets/uploads/2026/09/the-hunt-spelleider-uitleg-800.jpg" alt="De spelleider geeft uitleg aan een grote groep" loading="lazy" width="800" height="586"></div>
<div class="stack">
<span class="label">Personeelsuitje en grote groepen</span>
<h2 id="groot-titel">Van een klein team tot de hele organisatie</h2>
<p>We verdelen de groep in teams van ongeveer zes personen die tegelijk spelen. Zo organiseren we The Hunt net zo makkelijk voor een afdeling van 12 als voor een personeelsuitje met 150 collega’s. We hebben al groepen van meer dan 100 personen begeleid; tot ongeveer 200 deelnemers is mogelijk. Willen jullie meerdere spellen spelen? Dan maken we een wisselprogramma met onze andere spellen.</p>
<p>Wil je het extra persoonlijk? Bij <a href="/op-maat-gemaakt/" style="color:var(--signal)">The Hunt op maat</a> verwerken we vragen over jullie bedrijf, collega’s of kernwaarden in de puzzels.</p>
</div>
</div>
</section>

{photo_block('Zij gingen jullie voor', 'Bedrijven en teams die The Hunt speelden', TEAM_PHOTOS)}

{section('Programma en prijzen', 'Zo ziet jullie teamuitje eruit', f'<div class="pricing">{programme("team")}{per_person_table()}</div>')}

{section('Prijzen', 'Eén vaste prijs tot 17 personen', pricing(), 'section paper')}

{cities_block('Teamuitje in 33 steden', 'We spelen overal waar we een speelveld kunnen maken. Kies jullie stad voor de startlocatie en een voorbeeldprogramma.', ('teamuitje', 'bedrijfsuitje', 'bedrijfsfeest', 'groepsuitje', 'groepsactiviteit'))}

{section('Veelgestelde vragen', 'Vragen over een teamuitje met The Hunt', faq_block(TEAM_FAQ), 'section paper')}

{booking()}'''
    return page(path=path, title='Teamuitje & bedrijfsuitje | Outdoor escape game The Hunt',
                description='Actief teamuitje of bedrijfsuitje in de stad: los samen puzzels op en ontsnap aan de Hunters. Voor 8 tot ±200 personen, in heel Nederland. Vanaf €395.',
                body=body, schema=[crumb_schema(crumbs), faq_schema(TEAM_FAQ)], active=path)


def vrijgezellenfeest():
    path = '/vrijgezellenfeest/'
    crumbs = [('Home', '/'), ('Vrijgezellenfeest', path)]
    body = f'''{hero('Vrijgezellenfeest: The Hunt', 'Een actief en origineel vrijgezellenfeest: ontsnap in teams aan de Hunters, los puzzels op en bereik het extractiepunt. Vanaf 8 personen, in heel Nederland.', [('Home', '/'), ('Vrijgezellenfeest', None)], 'Vrijgezellenfeest · vrouwen · mannen · gemengd', img='/assets/uploads/2026/04/Escape-Game-The-Hunt-vrijgezellenfeest-groningen.jpeg')}

<section class="section" aria-labelledby="waarom-titel">
<div class="wrap split">
<div class="stack">
<span class="label">Waarom The Hunt</span>
<h2 id="waarom-titel">Geen standaard vrijgezellenfeest</h2>
<p>Een hapje eten, wat drankjes en de stad in: leuk, maar voorspelbaar. Met The Hunt kiezen jullie voor iets waar iedereen nog lang over napraat. Jullie gaan in teams op pad met een rugtas vol puzzels en de GameApp, en proberen binnen 90 minuten het extractiepunt te bereiken. De Hunters krijgen elke 10 minuten jullie locatie door, en komen steeds dichterbij.</p>
<p>Het mooiste moment: als er ineens vragen verschijnen over de bruid of bruidegom. Met <a href="/op-maat-gemaakt/">The Hunt op maat</a> verwerken we jullie eigen vragen, verhalen en foto’s in de opdrachten.</p>
<ul class="checks">
<li>Actief en buiten, midden in de stad</li>
<li>Teams tegen elkaar, met een winnaar aan het eind</li>
<li>Voor vrouwen, mannen en gemengde groepen vanaf 8 personen</li>
<li>Eten, borrelen of verder feesten ligt op loopafstand</li>
</ul>
</div>
<div class="media-frame"><img src="/assets/uploads/2026/09/the-hunt-extractiepunt-gehaald-800.jpg" alt="Een groep juicht bij het extractiepunt" loading="lazy" width="800" height="715"></div>
</div>
</section>

<section class="section tight paper" aria-labelledby="trailer-titel">
<div class="wrap split">
<div class="stack"><span class="label">Trailer</span><h2 id="trailer-titel">Zo ziet een Hunt eruit</h2>
<p>Puzzelen onder tijdsdruk, samen de route kiezen en uit het zicht blijven van de Hunters. Bekijk in de trailer hoe het spel werkt.</p></div>
{VIDEO}
</div>
</section>

{photo_block('Zij gingen jullie voor', 'Groepen die The Hunt speelden', VRIJ_PHOTOS)}

{section('Programma en prijzen', 'Zo ziet jullie vrijgezellenfeest eruit', f'<div class="pricing">{programme("vrijgezellen")}{per_person_table()}</div>')}

{section('Prijzen', 'Eén vaste prijs tot 17 personen', pricing(), 'section paper')}

{cities_block('Vrijgezellenfeest in 33 steden', 'We spelen overal waar we een speelveld kunnen maken. Kies de stad voor jullie vrijgezellenfeest.', ('vrijgezellen',))}

{section('Veelgestelde vragen', 'Vragen over een vrijgezellenfeest met The Hunt', faq_block(VRIJ_FAQ), 'section paper')}

{booking()}'''
    return page(path=path, title='Vrijgezellenfeest | Outdoor escape game The Hunt',
                description='Origineel en actief vrijgezellenfeest: ontsnap in teams aan de Hunters, met vragen over de bruid of bruidegom. Vanaf 8 personen, in heel Nederland.',
                body=body, schema=[crumb_schema(crumbs), faq_schema(VRIJ_FAQ)], active=path)
