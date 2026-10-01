"""Tekent een kaart in Google-Maps-stijl met het speelveld erop, uit OpenStreetMap-data."""
import json, math, sys
from PIL import Image, ImageDraw, ImageFont

SRC, OUT = sys.argv[1], sys.argv[2]
FIELD = [(53.21963, 6.55682), (53.21905, 6.55739), (53.21764, 6.55917), (53.21554, 6.55908), (53.21403, 6.56336),
         (53.21378, 6.56599), (53.21506, 6.57071), (53.21674, 6.573), (53.22136, 6.56998), (53.22264, 6.56629)]
if len(sys.argv) > 3:
    FIELD = [tuple(p) for p in json.load(open(sys.argv[3]))]
START = ('Start: Forum Groningen', 53.21891, 6.57018)
LABELS = ['Grote Markt', 'Vismarkt', 'Martinitoren', 'Prinsentuin', 'Herestraat', 'Folkingestraat', 'Oude Ebbingestraat',
          'Oosterstraat', 'Akerkhof', 'Poelestraat', 'Zuiderdiep', 'Noorderhaven', 'Turfsingel', 'Schuitendiep', 'Brugstraat']
W, H, S = 1600, 1200, 2  # uitvoer, supersampling
ORANGE = (242, 146, 34)

lats = [p[0] for p in FIELD]; lons = [p[1] for p in FIELD]
def merc(lat, lon):
    return lon, math.degrees(math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)))
cx, cy = merc((max(lats) + min(lats)) / 2, (max(lons) + min(lons)) / 2)
x0, y0 = merc(min(lats), min(lons)); x1, y1 = merc(max(lats), max(lons))
scale = min(W * 0.84 / (x1 - x0), H * 0.84 / (y1 - y0)) * S
def px(lat, lon):
    x, y = merc(lat, lon)
    return ((x - cx) * scale + W * S / 2, (cy - y) * scale + H * S / 2)

data = json.load(open(SRC, encoding='utf-8'))['elements']
img = Image.new('RGB', (W * S, H * S), (245, 243, 240))
d = ImageDraw.Draw(img)
def pts(g): return [px(p['lat'], p['lon']) for p in g]
def geoms(e):
    if e['type'] == 'way': return [e.get('geometry') or []]
    return [m['geometry'] for m in e.get('members', []) if m.get('geometry') and m.get('role') == 'outer']

layers = {'green': [], 'water': [], 'canal': [], 'building': [], 'roads': []}
for e in data:
    t = e.get('tags') or {}
    if t.get('leisure') in ('park', 'garden') or t.get('landuse') in ('grass', 'cemetery'): layers['green'].append(e)
    elif t.get('natural') == 'water': layers['water'].append(e)
    elif t.get('waterway') in ('canal', 'river'): layers['canal'].append(e)
    elif t.get('building'): layers['building'].append(e)
    elif t.get('highway'): layers['roads'].append(e)

for e in layers['green']:
    for g in geoms(e):
        if len(g) > 2: d.polygon(pts(g), fill=(206, 234, 214))
for e in layers['water']:
    for g in geoms(e):
        if len(g) > 2: d.polygon(pts(g), fill=(170, 218, 255))
for e in layers['canal']:
    d.line(pts(e['geometry']), fill=(170, 218, 255), width=14 * S // 2)
for e in layers['building']:
    for g in geoms(e):
        if len(g) > 2: d.polygon(pts(g), fill=(232, 233, 237), outline=(220, 222, 227))

WID = {'primary': 16, 'secondary': 15, 'tertiary': 13, 'residential': 10, 'unclassified': 10, 'living_street': 9,
       'pedestrian': 10, 'service': 6, 'footway': 4, 'cycleway': 4, 'path': 3}
roads = sorted(layers['roads'], key=lambda e: WID.get(e['tags']['highway'], 0))
for casing in (True, False):
    for e in roads:
        hw = e['tags']['highway']; w = WID.get(hw)
        if not w or e['tags'].get('area') == 'yes': continue
        if hw in ('footway', 'cycleway', 'path', 'service') and casing: continue
        fill = (255, 255, 255) if hw not in ('primary', 'secondary') else (255, 242, 175)
        if hw in ('footway', 'cycleway', 'path'): fill = (250, 250, 250)
        d.line(pts(e['geometry']), fill=(214, 216, 222) if casing else fill, width=(w + 3 if casing else w) * S // 2, joint='curve')

# speelveld
ov = Image.new('RGBA', img.size, (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
poly = [px(*p) for p in FIELD]
od.polygon(poly, fill=ORANGE + (40,))
img.paste(ov, (0, 0), ov)
d.line(poly + [poly[0]], fill=ORANGE, width=7 * S, joint='curve')

font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 22 * S)
bold = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 26 * S)
def label(text, x, y, f=font, color=(80, 86, 96)):
    d.text((x, y), text, font=f, fill=color, anchor='mm', stroke_width=4 * S, stroke_fill=(255, 255, 255))
seen = {}
for e in data:
    n = (e.get('tags') or {}).get('name')
    if n in LABELS and e.get('geometry'):
        seen.setdefault(n, []).extend(e['geometry'])
for n, g in seen.items():
    g = sorted(g, key=lambda p: p['lon'])[len(g) // 2]
    label(n, *px(g['lat'], g['lon']))

# startpunt
sx, sy = px(START[1], START[2]); r = 18 * S
d.ellipse((sx - r, sy - r, sx + r, sy + r), fill=(41, 57, 74), outline=(255, 255, 255), width=5 * S)
tw = d.textlength(START[0], font=bold)
bx, by = sx + 26 * S, sy - 22 * S
d.rounded_rectangle((bx, by, bx + tw + 28 * S, by + 44 * S), radius=10 * S, fill=(41, 57, 74))
d.text((bx + 14 * S, by + 22 * S), START[0], font=bold, fill=(255, 255, 255), anchor='lm')

small = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 15 * S)
d.text((W * S - 12 * S, H * S - 10 * S), '© OpenStreetMap-bijdragers', font=small, fill=(110, 116, 126), anchor='rd',
       stroke_width=3 * S, stroke_fill=(255, 255, 255))
img.resize((W, H), Image.LANCZOS).save(OUT, quality=85, optimize=True)
print('ok', OUT)
