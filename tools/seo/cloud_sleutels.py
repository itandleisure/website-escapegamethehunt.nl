"""Eenmalig: toon de waarden die als GitHub-secrets in de cloud moeten komen, zodat de statistieken
zonder deze laptop kunnen draaien (.github/workflows/statistiek.yml).

Gebruik (op de laptop waar de statistieken nu draaien):  python tools/seo/cloud_sleutels.py

Het script laat per secret de naam en de waarde zien. Kopieer die naar GitHub:
Settings > Secrets and variables > Actions > New repository secret. Er wordt niets verstuurd of opgeslagen.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
c = {}
f = os.path.join(HERE, 'statistiek.local.json')
if os.path.exists(f):
    c = json.load(open(f, encoding='utf-8'))


def lees(pad):
    try:
        return open(pad, encoding='utf-8-sig').read().strip()
    except OSError:
        return ''


sleutel = c.get('gsc_key') or os.environ.get('GSC_SLEUTEL', '')
waarden = [
    ('GSC_SLEUTEL_JSON', lees(sleutel) if sleutel else '', 'serviceaccount voor Search Console, Analytics en Google Ads'),
    ('STATISTIEK_WACHTWOORD', c.get('wachtwoord', ''), 'wachtwoord van de statistiekpagina'),
    ('STATISTIEK_MAIL_URL', c.get('mail_url', ''), 'adres van het mailscript (wekelijkse e-mail)'),
    ('STATISTIEK_MAIL_TOKEN', c.get('mail_token', ''), 'code voor het mailscript'),
    ('CLARITY_TOKEN', os.environ.get('CLARITY_TOKEN', '') or lees(os.path.join(HERE, 'clarity.token')), 'Microsoft Clarity'),
    ('DATAFORSEO_LOGIN', os.environ.get('DATAFORSEO_LOGIN', ''), 'posities meten (maandag)'),
    ('DATAFORSEO_PASSWORD', os.environ.get('DATAFORSEO_PASSWORD', ''), 'posities meten (maandag)'),
]
for i, (naam, waarde, uitleg) in enumerate(waarden, 1):
    print('=' * 70)
    print(f'{i}. Naam:  {naam}   ({uitleg})')
    if not waarde:
        print('   Niet gevonden op deze laptop; sla deze over.')
        continue
    print('   Waarde (alles tussen de streepjes kopiëren):')
    print('-' * 70)
    print(waarde)
    print('-' * 70)
    input('   Druk op Enter voor de volgende...')
print('Klaar. Sluit dit venster; de waarden zijn nergens opgeslagen.')
