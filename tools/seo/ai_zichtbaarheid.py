"""AI-zichtbaarheid: noemen ChatGPT, Perplexity en Gemini Escape Game The Hunt als je naar een uitje vraagt?

Gebruik:  python tools/seo/ai_zichtbaarheid.py
Stelt per stad 3 vragen en 4 algemene vragen aan de drie AI-platforms (via DataForSEO, met zoeken op het web
vanuit Nederland) en bewaart per antwoord: genoemd ja/nee, geciteerd (link naar onze site) ja/nee, het stukje tekst
rond de vermelding en de geciteerde bronnen. Resultaat: tools/seo/metingen/ai-YYYY-MM-DD.json.
Kosten: ongeveer $0,11 per vraag voor de drie platforms samen, dus ongeveer $4 per meting.
Login: omgevingsvariabelen DATAFORSEO_LOGIN en DATAFORSEO_PASSWORD.
"""
import datetime as dt, json, os, re, sys
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
MET = os.path.join(HERE, 'metingen')
API = 'https://api.dataforseo.com/v3/ai_optimization/{}/llm_responses/live'
PLATFORMS = {'ChatGPT': ('chat_gpt', 'gpt-5.4-mini', {'web_search': True, 'web_search_country_iso_code': 'NL'}),
             'Perplexity': ('perplexity', 'sonar', {}),
             'Gemini': ('gemini', 'gemini-3.5-flash', {'web_search': True})}
STEDEN = ['Amsterdam', 'Rotterdam', 'Den Haag', 'Utrecht', 'Eindhoven', 'Groningen', 'Tilburg', 'Nijmegen', 'Zwolle', 'Arnhem']
PER_STAD = [('teamuitje', "Wat is een leuk en actief teamuitje in {s} voor een groep collega's?"),
            ('vrijgezellenfeest', 'Ik zoek een leuke activiteit voor een vrijgezellenfeest in {s}. Wat raad je aan?'),
            ('outdoor escape', 'Is er een outdoor escape room of escape game in de buitenlucht in {s}?')]
ALGEMEEN = [('hunted', 'Waar kan ik zelf Hunted spelen in Nederland, net als in het tv-programma?'),
            ('bedrijven', 'Welke bedrijven organiseren een outdoor escape game door de stad in Nederland voor bedrijfsuitjes?'),
            ('jachtseizoen', 'Wat is een spannend groepsuitje zoals Jachtseizoen of Hunted in Nederland?'),
            ('grote groepen', 'Wat is de beste outdoor escape room in Nederland voor grote groepen?')]
# Sterk: de volledige naam. Zwak: los "The Hunt" (ook andere spellen heten zo, en "Escape Hunt" is een ander bedrijf);
# dat telt alleen als ons domein als bron staat of als er Hunters/achtervolging in de buurt beschreven wordt.
STERK = re.compile(r'escapegamethehunt|escape\s*game\W{0,3}the\s*hunt', re.I)
ZWAK = re.compile(r'(?<!escape )\bthe hunt\b', re.I)
ONS = 'escapegamethehunt.nl'


def herken(txt, bronnen):
    """(genoemd, geciteerd, fragment)"""
    geciteerd = any(ONS in b for b in bronnen) or ONS in txt.lower()
    m = STERK.search(txt)
    if not m:
        for z in ZWAK.finditer(txt):
            om = txt[max(0, z.start() - 200): z.end() + 300].lower()
            if geciteerd or 'hunter' in om or 'achtervolg' in om:
                m = z
                break
    frag = txt[max(0, m.start() - 150): m.end() + 150].replace('\n', ' ') if m else ''
    return bool(m), geciteerd, frag


def vragen():
    out = [{'stad': s, 'soort': k, 'vraag': q.format(s=s)} for s in STEDEN for k, q in PER_STAD]
    return out + [{'stad': '', 'soort': k, 'vraag': q} for k, q in ALGEMEEN]


def domein(a):
    u = a.get('url') or ''
    d = urlparse(u).netloc.lower().removeprefix('www.')
    if not d or 'vertexaisearch' in d:  # Gemini geeft doorverwijzingen; de titel is dan het domein
        d = (a.get('title') or '').lower().removeprefix('www.')
    return d


def vraag_aan(platform, q, auth):
    ep, model, extra = PLATFORMS[platform]
    try:
        r = requests.post(API.format(ep), auth=auth, json=[{'user_prompt': q, 'model_name': model, **extra}], timeout=180).json()
        t = r['tasks'][0]
        res = (t.get('result') or [None])[0]
        if not res:
            return {'fout': t.get('status_message', '?'), 'kosten': t.get('cost', 0)}
        secs = [s for it in res['items'] if it['type'] == 'message' for s in it['sections']]
        txt = '\n'.join(s.get('text', '') for s in secs)
        bronnen = [domein(a) for s in secs for a in (s.get('annotations') or [])]
        bronnen = list(dict.fromkeys(b for b in bronnen if b))
        g, c, frag = herken(txt, bronnen)
        return {'genoemd': g, 'geciteerd': c, 'fragment': frag, 'bronnen': bronnen, 'tekst': txt, 'kosten': t.get('cost', 0)}
    except Exception as e:
        return {'fout': str(e)[:200], 'kosten': 0}


def main():
    auth = (os.environ['DATAFORSEO_LOGIN'], os.environ['DATAFORSEO_PASSWORD'])
    V = vragen()
    jobs = [(v, p) for v in V for p in PLATFORMS]
    with ThreadPoolExecutor(12) as ex:
        res = list(ex.map(lambda j: vraag_aan(j[1], j[0]['vraag'], auth), jobs))
    for (v, p), r in zip(jobs, res):
        v.setdefault('antwoorden', {})[p] = r
    kosten = sum(r.get('kosten', 0) for r in res)
    out = {'datum': str(dt.date.today()), 'platforms': {p: PLATFORMS[p][1] for p in PLATFORMS}, 'kosten': round(kosten, 2), 'vragen': V}
    os.makedirs(MET, exist_ok=True)
    f = os.path.join(MET, f'ai-{out["datum"]}.json')
    json.dump(out, open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for p in PLATFORMS:
        a = [v['antwoorden'][p] for v in V if 'fout' not in v['antwoorden'][p]]
        print(f'{p}: genoemd {sum(x["genoemd"] for x in a)}/{len(a)}, geciteerd {sum(x["geciteerd"] for x in a)}/{len(a)}')
    print('Kosten: $%.2f -> %s' % (kosten, f))


if __name__ == '__main__':
    sys.exit(main())
