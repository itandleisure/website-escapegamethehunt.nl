"""Eenmalig: zet de waarden die als GitHub-secrets in de cloud moeten komen in één Kladblok-bestand, zodat de
statistieken zonder deze laptop kunnen draaien (.github/workflows/statistiek.yml).

Gebruik (op de laptop waar de statistieken nu draaien):  python tools/seo/cloud_sleutels.py

Het bestand tools/seo/data/sleutels-voor-github.txt (niet in git) gaat vanzelf open in Kladblok. Kopieer per blok
de naam en de waarde naar GitHub: Settings > Secrets and variables > Actions > New repository secret.
Verwijder het bestand daarna. Er wordt niets verstuurd.
"""
import json, os, subprocess, sys

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
gsc = lees(sleutel) if sleutel else ''
if gsc:
    try:
        gsc = json.dumps(json.loads(gsc), separators=(',', ':'))   # één regel: makkelijker in één keer te selecteren
    except ValueError:
        pass
waarden = [
    ('GSC_SLEUTEL_JSON', gsc, 'serviceaccount voor Search Console, Analytics en Google Ads'),
    ('STATISTIEK_WACHTWOORD', c.get('wachtwoord', ''), 'wachtwoord van de statistiekpagina'),
    ('STATISTIEK_MAIL_URL', c.get('mail_url', ''), 'adres van het mailscript (wekelijkse e-mail)'),
    ('STATISTIEK_MAIL_TOKEN', c.get('mail_token', ''), 'code voor het mailscript'),
    ('CLARITY_TOKEN', os.environ.get('CLARITY_TOKEN', '') or lees(os.path.join(HERE, 'clarity.token')), 'Microsoft Clarity'),
    ('DATAFORSEO_LOGIN', os.environ.get('DATAFORSEO_LOGIN', ''), 'posities meten (maandag)'),
    ('DATAFORSEO_PASSWORD', os.environ.get('DATAFORSEO_PASSWORD', ''), 'posities meten (maandag)'),
]
regels = ['SLEUTELS VOOR GITHUB',
          'Open https://github.com/itandleisure/website-escapegamethehunt.nl/settings/secrets/actions',
          'Per blok: klik "New repository secret", plak de NAAM bij Name en de WAARDE bij Secret, klik "Add secret".',
          'Tip: klik 3 keer snel op een regel om de hele regel te selecteren, dan Ctrl+C.',
          'VERWIJDER DIT BESTAND ALS JE KLAAR BENT.', '']
for i, (naam, waarde, uitleg) in enumerate(waarden, 1):
    regels += ['=' * 60, f'{i}. {uitleg}', 'NAAM:', naam, 'WAARDE:',
               waarde if waarde else '(niet gevonden op deze laptop, sla deze over)', '']
os.makedirs(os.path.join(HERE, 'data'), exist_ok=True)
uit = os.path.join(HERE, 'data', 'sleutels-voor-github.txt')
with open(uit, 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(regels))
print('Geschreven:', uit)
if sys.platform == 'win32':
    subprocess.Popen(['notepad.exe', uit])
