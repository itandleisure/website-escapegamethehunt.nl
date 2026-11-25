"""Maakt een los pakket (zip) van de boekje-tool voor een pc zonder Python, Git of cloud.

    python tools/loquiz/maak_pakket.py                    # haalt Python 3.12 (64-bit, Windows) van nuget.org
    python tools/loquiz/maak_pakket.py --python python.3.12.10.nupkg
    python tools/loquiz/maak_pakket.py --zonder-key       # zonder .env; zet de key er dan zelf in
    python tools/loquiz/maak_pakket.py --mac              # versie voor een Mac (gebruikt de python3 van macOS)

Het pakket bevat een eigen Python, de scripts, de huisstijl (logo, letters, foto's) en de .env met de API-key.
Uitpakken, dubbelklikken op "Boekje maken.bat" en klaar. Uitvoer: tools/loquiz/uitvoer/pakket/TheHunt-Fotoboekje.zip.
Met --mac: TheHunt-Fotoboekje-Mac.zip, zonder eigen Python en met "Boekje maken.command" om te dubbelklikken.
Let op: de zip bevat de API-key, dus deel hem alleen met wie hem mag hebben (niet mailen naar klanten).
"""
import argparse
import io
import json
import os
import sys
import time
import urllib.request
import zipfile

HIER = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HIER))
PY_VERSIE = '3.12.10'
NUGET = f'https://api.nuget.org/v3-flatcontainer/python/{PY_VERSIE}/python.{PY_VERSIE}.nupkg'
NAAM = 'TheHunt-Fotoboekje'

# delen van Python die de tool niet nodig heeft (scheelt ruim de helft)
WEG = ('Lib/test/', 'Lib/idlelib/', 'Lib/tkinter/', 'Lib/turtledemo/', 'Lib/lib2to3/', 'Lib/ensurepip/',
       'Lib/site-packages/', 'Lib/unittest/', 'Lib/pydoc_data/', 'tcl/', 'include/', 'libs/', 'Scripts/',
       'DLLs/_tkinter.pyd', 'DLLs/tcl', 'DLLs/tk')

BAT = '\r\n'.join([
    '@echo off',
    'rem Opent het invulscherm voor het fotoboekje in de browser. Sluit dit venster om te stoppen.',
    'cd /d "%~dp0"',
    '"python\\python.exe" "tools\\loquiz\\boekje_tool.py"',
    'if errorlevel 1 pause', ''])

LEESMIJ = '''Fotoboek maken - The Hunt
=======================

1. Dubbelklik op "Boekje maken.bat". Er opent een pagina in je browser (en een zwart venster: laat dat open).
2. Plak de spelleider-URL, bijvoorbeeld https://results.loquiz.com/F3CJ8WVUSC:VANWIJNEN
   Vul eventueel de plaatsnaam in.
3. Teamfoto: sleep de groepsfoto van de spelleider in het vak (één foto, komt groot bovenaan).
   Sla foto's uit WhatsApp eerst op de computer op.
4. Extra foto's (van de spelleider of het social media team): sleep ze in het tweede vak.
5. Laat "Ook online zetten met een wachtwoord" aan staan en klik op "Teams en foto's ophalen".
6. Controleer wat erin komt: vink teams uit die er niet in horen (zoals de spelleiders) en klik op foto's
   die niet in het boekje mogen. Zijn er minder dan 8 foto's, dan vullen we aan met onze eigen sfeerfoto's.
   Klik op "Maak fotoboek".
7. Na een paar minuten zie je de link, het wachtwoord en een kant-en-klare mail. Klik op "Kopieer mail",
   plak hem in een nieuwe mail aan de klant en voeg de PDF toe als bijlage (de map met de PDF gaat vanzelf open).
   Het wachtwoord is elke keer anders. De link werkt na een paar minuten.

De fotoboeken staan ook op deze computer in tools\\loquiz\\uitvoer\\<spel>\\.
Online fotoboeken worden na 90 dagen automatisch weggehaald.
Werkt de PDF niet? Klik op "PDF-versie als webpagina" en kies Afdrukken > Opslaan als PDF.
Zegt het scherm "geen GITHUB_TOKEN" of "GitHub weigert de toegang"? Vraag Frans om een nieuwe .env.
Windows vraagt bij de eerste keer misschien of het programma mag draaien: kies "Meer info" > "Toch uitvoeren".
'''.replace('\n', '\r\n')

COMMAND = '\n'.join([
    '#!/bin/bash',
    '# Opent het invulscherm voor het fotoboekje in de browser. Sluit dit venster om te stoppen.',
    'cd "$(dirname "$0")"',
    'if ! /usr/bin/python3 -c "import sys" >/dev/null 2>&1; then',
    '  echo "Python 3 ontbreekt nog. macOS vraagt nu of je de opdrachtregelprogramma\'s wilt installeren:"',
    '  echo "kies Installeren, wacht tot het klaar is en dubbelklik daarna opnieuw op Boekje maken."',
    '  xcode-select --install >/dev/null 2>&1',
    '  read -r -p "Druk op Enter om dit venster te sluiten."',
    '  exit 1',
    'fi',
    '/usr/bin/python3 tools/loquiz/boekje_tool.py || read -r -p "Er ging iets mis. Druk op Enter om te sluiten."',
    ''])

LEESMIJ_MAC = '''Fotoboek maken op een Mac - The Hunt
====================================

Eenmalig:
- Installeer Google Chrome of Microsoft Edge (nodig voor de PDF).
- De eerste keer weigert macOS "Boekje maken.command", omdat het niet uit de App Store komt.
  Klik op Gereed, ga naar Systeeminstellingen > Privacy en beveiliging, scrol naar beneden en kies
  "Open toch" bij Boekje maken.command. Daarna werkt dubbelklikken gewoon.
- Vraagt macOS om de "opdrachtregelprogramma's" te installeren: kies Installeren (dat is Python),
  wacht tot het klaar is en dubbelklik opnieuw op Boekje maken.command.

Elke keer:
1. Dubbelklik op "Boekje maken.command". Er opent een pagina in je browser (en een Terminal-venster: laat dat open).
2. Plak de spelleider-URL, bijvoorbeeld https://results.loquiz.com/F3CJ8WVUSC:VANWIJNEN
   Vul eventueel de plaatsnaam in.
3. Teamfoto: sleep de groepsfoto van de spelleider in het vak (één foto, komt groot bovenaan).
4. Extra foto's (van de spelleider of het social media team): sleep ze in het tweede vak.
5. Laat "Ook online zetten met een wachtwoord" aan staan en klik op "Teams en foto's ophalen".
6. Controleer wat erin komt: vink teams uit die er niet in horen (zoals de spelleiders) en klik op foto's
   die niet in het boekje mogen. Zijn er minder dan 8 foto's, dan vullen we aan met onze eigen sfeerfoto's.
   Klik op "Maak fotoboek".
7. Na een paar minuten zie je de link, het wachtwoord en een kant-en-klare mail. Klik op "Kopieer mail",
   plak hem in een nieuwe mail aan de klant en voeg de PDF toe als bijlage (de map met de PDF gaat vanzelf open).
   Het wachtwoord is elke keer anders. De link werkt na een paar minuten.

De fotoboeken staan ook op deze Mac in tools/loquiz/uitvoer/<spel>/.
Online fotoboeken worden na 90 dagen automatisch weggehaald.
Werkt de PDF niet? Klik op "PDF-versie als webpagina" en kies Afdrukken > Bewaar als PDF.
Zegt het scherm "geen GITHUB_TOKEN" of "GitHub weigert de toegang"? Vraag Frans om een nieuwe .env.
Stoppen: sluit het Terminal-venster.
'''


def uitvoerbaar(z, naam, inhoud):
    """Zet een bestand in de zip met uitvoerrechten (Unix), zodat de Mac het met een dubbelklik start."""
    info = zipfile.ZipInfo(naam, time.localtime()[:6])
    info.create_system = 3
    info.external_attr = 0o100755 << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    z.writestr(info, inhoud)


def bestanden():
    site = json.load(open(os.path.join(ROOT, 'src', 'data', 'site.json'), encoding='utf-8'))
    sys.path.insert(0, HIER)
    import boekje
    lijst = [f'tools/loquiz/{n}' for n in ('resultaten.py', 'boekje.py', 'boekje_tool.py', 'fotoboek_web.py')]
    lijst += ['src/data/site.json', 'src/data/locations.json']
    lijst += ['docs/assets/fonts/' + f for f in os.listdir(os.path.join(ROOT, 'docs', 'assets', 'fonts'))]
    lijst += ['docs' + p for p in (site['logo'], boekje.VOORKANT_FOTO, boekje.VIDEO_POSTER, boekje.REVIEW_FOTO, boekje.HUNTER_FOTO, boekje.BADASS_LOGO)]
    lijst += ['docs' + s['foto'] for s in boekje.SPELLEN if s.get('foto', '').startswith('/')]
    lijst += ['docs' + p for p in boekje.EIGEN_FOTOS if p not in lijst and 'docs' + p not in lijst]
    eigen = os.path.join(HIER, 'eigen-fotos')
    if os.path.isdir(eigen):
        lijst += [f'tools/loquiz/eigen-fotos/{f}' for f in sorted(os.listdir(eigen)) if f.lower().endswith(boekje.FOTO_EXT)]
    return lijst


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--python', help='pad naar python.<versie>.nupkg (anders van nuget.org)')
    ap.add_argument('--zonder-key', action='store_true', help='.env niet meenemen')
    ap.add_argument('--mac', action='store_true', help='pakket voor een Mac (zonder eigen Python)')
    ap.add_argument('--uit', default=os.path.join(HIER, 'uitvoer', 'pakket'))
    a = ap.parse_args()

    if a.mac:
        nupkg = None
    elif a.python:
        nupkg = open(a.python, 'rb').read()
    else:
        print(f'Python {PY_VERSIE} ophalen van nuget.org...')
        nupkg = urllib.request.urlopen(NUGET, timeout=120).read()
    env = os.path.join(ROOT, '.env')
    if not a.zonder_key and not os.path.exists(env):
        sys.exit('Geen .env gevonden. Maak die eerst aan of gebruik --zonder-key.')

    os.makedirs(a.uit, exist_ok=True)
    doel = os.path.join(a.uit, NAAM + ('-Mac' if a.mac else '') + '.zip')
    n_py = 0
    with zipfile.ZipFile(doel, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        with zipfile.ZipFile(io.BytesIO(nupkg or b'PK\x05\x06' + bytes(18))) as pk:
            for info in pk.infolist():
                if not info.filename.startswith('tools/') or info.is_dir():
                    continue
                rel = info.filename[len('tools/'):]
                if rel.startswith(WEG) or '__pycache__' in rel:
                    continue
                z.writestr(f'{NAAM}/python/{rel}', pk.read(info))
                n_py += 1
        for rel in bestanden():
            z.write(os.path.join(ROOT, *rel.split('/')), f'{NAAM}/{rel}')
        if not a.zonder_key:
            z.write(env, f'{NAAM}/.env')
        if a.mac:
            uitvoerbaar(z, f'{NAAM}/Boekje maken.command', COMMAND)
            z.writestr(f'{NAAM}/LEES MIJ.txt', LEESMIJ_MAC)
        else:
            z.writestr(f'{NAAM}/Boekje maken.bat', BAT)
            z.writestr(f'{NAAM}/LEES MIJ.txt', LEESMIJ)
    print(('Mac-pakket, ' if a.mac else '') + f'{n_py} Python-bestanden, {len(bestanden())} eigen bestanden'
          + ('' if a.zonder_key else ', met API-key') + f'\nPakket: {doel} ({os.path.getsize(doel) // 1024 // 1024} MB)')


if __name__ == '__main__':
    main()
