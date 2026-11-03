"""Maakt van elke JPG/PNG in docs/assets/uploads een kleinere WebP-versie en laat de pagina's die gebruiken.

Gebruik:  python tools/afbeeldingen.py     (vereist Pillow: pip install pillow)

- Naast elk bestand komt een .webp met dezelfde naam (foto.jpg -> foto.webp). Het origineel blijft staan,
  want dat wordt nog gebruikt voor de deelafbeelding op social media (og:image) en in Google (schema).
- Foto's breder dan MAX_BREEDTE worden in de WebP-versie verkleind; op de site worden ze nooit breder getoond.
- Een WebP wordt alleen bewaard als die echt kleiner is dan het origineel.
- Bestaande WebP's worden overgeslagen, tenzij het origineel nieuwer is.

tools/build.py roept dit automatisch aan als Pillow is geïnstalleerd, en zet daarna in elke <img> de .webp
in plaats van de .jpg/.png (zie webp_in_html). Zonder Pillow bouwt de site gewoon met de bestaande WebP's.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, 'docs')
UPLOADS = os.path.join(DOCS, 'assets', 'uploads')
EXT = ('.jpg', '.jpeg', '.png')
MAX_BREEDTE = 1920
KWALITEIT = 80
# Afbeeldingen waarvan de WebP niet kleiner werd (of die niet te openen zijn): niet elke build opnieuw proberen.
GROTER = os.path.join(ROOT, 'tools', 'afbeeldingen-geen-webp.txt')


def webp_pad(pad):
    return os.path.splitext(pad)[0] + '.webp'


def omzetten(verbose=True):
    from PIL import Image, ImageOps

    nieuw = voor = na = 0
    overslaan = set(open(GROTER, encoding='utf-8').read().split('\n')) if os.path.exists(GROTER) else set()
    erbij = []
    for map_, _, bestanden in os.walk(UPLOADS):
        for naam in bestanden:
            if not naam.lower().endswith(EXT):
                continue
            bron = os.path.join(map_, naam)
            doel = webp_pad(bron)
            rel = os.path.relpath(bron, DOCS).replace(os.sep, '/')
            if rel in overslaan:
                continue
            if os.path.exists(doel) and os.path.getmtime(doel) >= os.path.getmtime(bron):
                continue
            # Twee bestanden met dezelfde naam maar een andere extensie (foto.jpg en foto.png) zouden
            # dezelfde .webp krijgen: dan alleen de JPG omzetten.
            stam = os.path.splitext(bron)[0]
            if naam.lower().endswith('.png') and any(os.path.exists(stam + e) for e in ('.jpg', '.jpeg')):
                continue
            try:
                with Image.open(bron) as im:
                    im = ImageOps.exif_transpose(im)
                    if im.width > MAX_BREEDTE:
                        im = im.resize((MAX_BREEDTE, round(im.height * MAX_BREEDTE / im.width)), Image.LANCZOS)
                    if im.mode not in ('RGB', 'RGBA'):
                        im = im.convert('RGBA' if 'A' in im.getbands() or 'transparency' in im.info else 'RGB')
                    im.save(doel, 'WEBP', quality=KWALITEIT, method=6)
            except Exception as fout:  # kapot of vreemd bestand: origineel blijft gewoon in gebruik
                print(f'  overgeslagen: {os.path.relpath(bron, ROOT)} ({fout})')
                erbij.append(rel)
                continue
            if os.path.getsize(doel) >= os.path.getsize(bron):
                os.remove(doel)
                erbij.append(rel)
                continue
            nieuw += 1
            voor += os.path.getsize(bron)
            na += os.path.getsize(doel)
    if erbij:
        with open(GROTER, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write('\n'.join(sorted(overslaan - {''} | set(erbij))) + '\n')
    if verbose and nieuw:
        print('%d WebP-afbeeldingen gemaakt: %.1f MB -> %.1f MB' % (nieuw, voor / 1e6, na / 1e6))
    return nieuw


_IMG = re.compile(r'<img\b[^>]*>', re.I)
_URL = re.compile(r'(/assets/uploads/[^\s"\'<>,]+?)\.(?:jpe?g|png)(?=[\s"\',])', re.I)


def webp_in_html(html):
    """Vervangt in <img src/srcset> elke upload-afbeelding door de .webp-versie, als die bestaat.

    Alleen binnen <img>-tags: og:image, schema en links naar het origineel blijven ongewijzigd."""
    def url(m):
        pad = os.path.join(DOCS, m.group(1).lstrip('/').replace('/', os.sep)) + '.webp'
        return m.group(1) + '.webp' if os.path.exists(pad) else m.group(0)

    return _IMG.sub(lambda m: _URL.sub(url, m.group(0)), html)


if __name__ == '__main__':
    try:
        import PIL  # noqa: F401
    except ImportError:
        sys.exit('Pillow ontbreekt: pip install pillow')
    n = omzetten()
    print('Klaar.' if n else 'Alle afbeeldingen hadden al een WebP-versie.')
