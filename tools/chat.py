"""Kennisbank voor de chat op de website (vraag en antwoord, zonder AI en zonder server).

Wordt door tools/build.py aangeroepen en schrijft docs/assets/chat.json. Alle antwoorden komen uit wat al op de site
staat: de veelgestelde vragen, de vragen op de stadspagina's, de prijzen en de lijst met steden. Zo blijft de chat
gelijk met de website. De browser zoekt in deze lijst het antwoord dat het best bij de vraag past (assets/js/chat.js).
"""
import glob
import json
import os
import re

from render import LOCS, OUT, ROOT, SITE

P = SITE['prices']


def tekst(q):
    """Woorden van een vraag, zonder leestekens."""
    return re.sub(r'[^a-z0-9à-ü ]', ' ', q.lower())


def items():
    out = []
    faq = json.load(open(os.path.join(ROOT, 'src', 'content', 'pages', 'veelgestelde-vragen.json'), encoding='utf-8'))
    for _, groep in faq.get('faq_groups') or []:
        for q, a in groep:
            out.append({'q': q, 'a': a})
    # per stad: start, duur, drinken na afloop enz. (vragen die op alle stadspagina's hetzelfde zijn, staan al in de FAQ)
    algemeen = {i['q'] for i in out} | {'Gaat The Hunt door als het regent?', 'Is The Hunt een escape room?', 'Is The Hunt geschikt voor kinderen?'}
    for loc in LOCS:
        f = os.path.join(ROOT, 'src', 'content', 'locaties', loc['slug'] + '.json')
        if not os.path.exists(f):
            continue
        for q, a in json.load(open(f, encoding='utf-8')).get('faq') or []:
            if q not in algemeen:
                out.append({'q': q, 'a': a, 'stad': loc['name']})
    # vaste antwoorden die niet als vraag op de site staan
    steden = ', '.join(f'<a href="{l["url"]}">{l["name"]}</a>' for l in LOCS)
    out += [
        {'q': 'In welke steden kun je The Hunt spelen? Waar locaties', 'a': f'<p>The Hunt speel je in {len(LOCS)} steden: {steden}. '
         'Staat jullie stad er niet bij? Dan organiseren we The Hunt daar ook graag. Samen kijken we wat wel en niet kan, '
         'en daar zitten geen extra kosten aan.</p>'},
        {'q': 'Wat kost het per persoon? Prijs grote groep tarief', 'a': f'<p>Tot en met {P["base_max_people"]} personen betaal je €{P["base"]} ex. btw '
         f'(€{P["base_incl"]} incl. btw) voor de hele groep. Daarboven is het €{P["per_person"]} ex. btw (€{P["per_person_incl"]} incl. btw) per persoon. '
         'Alle bedragen staan op de <a href="/escape-game-the-hunt-prijzen/">prijzenpagina</a>.</p>'},
        {'q': 'Hoe kan ik boeken of reserveren? Is er plek beschikbaar op een datum?', 'a': '<p>Vul het <a href="#boeken">aanvraagformulier</a> in met de stad, '
         'datum en het aantal personen. We laten je snel weten of het kan, meestal dezelfde werkdag. Liever bellen? '
         f'<a href="tel:{SITE["phone"]}">{SITE["phone_display"]}</a>.</p>'},
        {'q': 'Kunnen we The Hunt spelen als vrijgezellenfeest?', 'a': '<p>Zeker, The Hunt is een populair vrijgezellenuitje: samen puzzelen, '
         'rennen voor de Hunters en daarna door naar de borrel. Lees meer op de <a href="/vrijgezellenfeest/">pagina over vrijgezellenfeesten</a>.</p>'},
        {'q': 'Hoe kan ik contact opnemen? Telefoonnummer e-mail bellen mailen', 'a': f'<p>Bel ons op <a href="tel:{SITE["phone"]}">{SITE["phone_display"]}</a> '
         f'of mail naar <a href="mailto:{SITE["email"]}">{SITE["email"]}</a>.</p>'},
    ]
    for i in out:
        i['k'] = tekst(i['q'])
    return out


def build():
    data = {'steden': [{'n': l['name'], 'u': l['url'], 's': l.get('start') or ''} for l in LOCS], 'items': items(),
            'tel': SITE['phone'], 'tel_tekst': SITE['phone_display'], 'mail': SITE['email'], 'google': SITE.get('google_form_url', '')}
    with open(os.path.join(OUT, 'assets', 'chat.json'), 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(data, fh, ensure_ascii=False, separators=(',', ':'))
    return len(data['items'])


if __name__ == '__main__':
    print(build(), 'antwoorden in docs/assets/chat.json')
