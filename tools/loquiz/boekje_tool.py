"""Invulscherm voor het fotoboekje: spelleider-URL plakken, groepsfoto's erin slepen, PDF krijgen.

Start met "Boekje maken.bat" (of: python tools/loquiz/boekje_tool.py). Er opent een pagina in de browser op
http://127.0.0.1:8765. Alles draait op deze computer; de API-key blijft in .env. Sluit het zwarte venster om te stoppen.
"""
import email.parser
import email.policy
import json
import os
import re
import socket
import sys
import threading
import traceback
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import boekje  # noqa: E402
from resultaten import HIER, e  # noqa: E402

UITVOER = os.path.join(HIER, 'uitvoer')
BEZIG = threading.Lock()

PAGINA = '''<!doctype html>
<html lang="nl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Fotoboekje maken · The Hunt</title>
<style>
:root{--night:#141e29;--navy:#29394a;--signal:#f29222;--paper:#f3f5f7;--ink:#1c2834;--muted:#5a6878;--line:#dbe2e9}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font:400 16px/1.5 system-ui,-apple-system,'Segoe UI',Roboto,sans-serif}
header{background:var(--night);color:#fff;padding:18px 0}
.wrap{max-width:640px;margin:0 auto;padding:0 16px}
header b{font-size:20px}
header span{color:#a9b6c4;font-size:14px;margin-left:8px}
main{padding:28px 0 60px}
.kaart{background:#fff;border:1px solid var(--line);border-radius:12px;padding:22px}
label{display:block;font-weight:700;margin:0 0 6px}
.hulp{color:var(--muted);font-size:14px;margin:-2px 0 8px}
input[type=text]{width:100%;font:inherit;padding:11px 12px;border:1px solid var(--line);border-radius:8px}
input[type=text]:focus{outline:3px solid rgba(242,146,34,.35);border-color:var(--signal)}
.veld{margin-bottom:20px}
.drop{border:2px dashed var(--line);border-radius:10px;padding:22px;text-align:center;color:var(--muted);cursor:pointer}
.drop.over{border-color:var(--signal);background:#fff8ef}
.drop input{display:none}
.duimen{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
.duimen img{width:84px;height:84px;object-fit:cover;border-radius:6px}
button{font-family:inherit;font-weight:700;font-size:16px;line-height:1;background:var(--signal);color:var(--night);border:0;border-radius:999px;padding:14px 26px;cursor:pointer}
button[disabled]{opacity:.6;cursor:wait}
.uitslag{margin-top:20px;padding:16px;border-radius:10px;display:none}
.uitslag.ok{display:block;background:#eef8f0;border:1px solid #bfe3c7}
.uitslag.fout{display:block;background:#fdeeee;border:1px solid #f1c2c2}
.uitslag a{color:#a85600;font-weight:700}
.draai{display:inline-block;width:16px;height:16px;border:3px solid rgba(20,30,41,.25);border-top-color:var(--night);border-radius:50%;
  animation:d 1s linear infinite;vertical-align:-3px;margin-right:8px}
@keyframes d{to{transform:rotate(360deg)}}
</style></head>
<body>
<header><div class="wrap"><b>Fotoboekje maken</b><span>The Hunt</span></div></header>
<main class="wrap">
<form class="kaart" id="f">
  <div class="veld">
    <label for="url">Spelleider-URL</label>
    <p class="hulp">Bijvoorbeeld https://results.loquiz.com/F3CJ8WVUSC:VANWIJNEN</p>
    <input type="text" id="url" name="url" required placeholder="https://results.loquiz.com/..." autocomplete="off">
  </div>
  <div class="veld">
    <label>Groepsfoto('s)</label>
    <p class="hulp">De foto's van de spelleider (uit WhatsApp). Sleep ze hierheen of klik om te kiezen.</p>
    <div class="drop" id="drop">Sleep foto's hierheen of klik om te kiezen
      <input type="file" id="fotos" name="fotos" accept="image/*" multiple></div>
    <div class="duimen" id="duimen"></div>
  </div>
  <div class="veld">
    <label for="stad">Plaatsnaam <span style="font-weight:400;color:var(--muted)">(optioneel)</span></label>
    <p class="hulp">Leeg = "Bedankt voor het spelen van The Hunt". Ingevuld = "... van The Hunt in Den Haag".</p>
    <input type="text" id="stad" name="stad" autocomplete="off">
  </div>
  <button type="submit" id="knop">Maak boekje</button>
  <div class="uitslag" id="uitslag"></div>
</form>
</main>
<script>
const f=document.getElementById('f'),drop=document.getElementById('drop'),inp=document.getElementById('fotos'),
  duimen=document.getElementById('duimen'),knop=document.getElementById('knop'),uit=document.getElementById('uitslag');
let bestanden=[];
function toon(){duimen.innerHTML='';bestanden.forEach(b=>{const i=document.createElement('img');i.src=URL.createObjectURL(b);duimen.appendChild(i)})}
function voeg(lijst){for(const b of lijst){if(b.type.startsWith('image/'))bestanden.push(b)}toon()}
drop.onclick=()=>inp.click();
inp.onchange=()=>{voeg(inp.files);inp.value=''};
['dragenter','dragover'].forEach(t=>drop.addEventListener(t,ev=>{ev.preventDefault();drop.classList.add('over')}));
['dragleave','drop'].forEach(t=>drop.addEventListener(t,ev=>{ev.preventDefault();drop.classList.remove('over')}));
drop.addEventListener('drop',ev=>voeg(ev.dataTransfer.files));
f.onsubmit=async ev=>{
  ev.preventDefault();
  const fd=new FormData();fd.append('url',f.url.value);fd.append('stad',f.stad.value);
  bestanden.forEach(b=>fd.append('fotos',b,b.name));
  knop.disabled=true;uit.className='uitslag ok';uit.innerHTML='<span class="draai"></span>Bezig met ophalen en opmaken, dit duurt ongeveer een minuut...';
  try{
    const r=await fetch('/maak',{method:'POST',body:fd});const d=await r.json();
    if(d.ok){uit.className='uitslag ok';uit.innerHTML='<b>'+d.titel+'</b><br>'+d.samenvatting+
      (d.pdf?'<br><br><a href="'+d.pdf+'" target="_blank">Open de PDF</a> &nbsp; ':'<br><br>')+
      '<a href="'+d.html+'" target="_blank">Open als webpagina</a>'+(d.melding?'<br><br>'+d.melding:'');}
    else{uit.className='uitslag fout';uit.textContent=d.melding}
  }catch(err){uit.className='uitslag fout';uit.textContent='Er ging iets mis: '+err}
  knop.disabled=false;
};
</script>
</body></html>
'''


def schoon(naam):
    naam = os.path.basename(naam or 'foto.jpg')
    stam, ext = os.path.splitext(naam)
    ext = ext.lower() if ext.lower() in boekje.FOTO_EXT else '.jpg'
    return (re.sub(r'[^A-Za-z0-9_-]+', '-', stam).strip('-') or 'foto')[:60] + ext


def lees_formulier(handler):
    lengte = int(handler.headers.get('Content-Length') or 0)
    ruw = handler.rfile.read(lengte)
    kop = f'Content-Type: {handler.headers.get("Content-Type")}\r\nMIME-Version: 1.0\r\n\r\n'.encode()
    bericht = email.parser.BytesParser(policy=email.policy.HTTP).parsebytes(kop + ruw)
    velden, fotos = {}, []
    for deel in bericht.iter_parts():
        naam = deel.get_param('name', header='content-disposition')
        if deel.get_filename():
            data = deel.get_payload(decode=True) or b''
            if data:
                fotos.append((schoon(deel.get_filename()), data))
        elif naam:
            velden[naam] = (deel.get_payload(decode=True) or b'').decode('utf-8', 'replace').strip()
    return velden, fotos


def maak(velden, fotos):
    demo = velden.get('url', '').strip().lower() == 'demo'  # "demo" als URL: voorbeeld zonder API
    try:
        game_id, scope = ('DEMO', '') if demo else boekje.lees_url(velden.get('url', ''))
    except ValueError as fout:
        return {'ok': False, 'melding': str(fout)}
    sleutel = 'demo' if demo else boekje.mapnaam(game_id, scope)
    fotomap = os.path.join(HIER, 'groepsfotos', sleutel)
    os.makedirs(fotomap, exist_ok=True)
    if fotos:  # nieuwe groepsfoto's vervangen de vorige van dit spel
        for oud in os.listdir(fotomap):
            if oud.lower().endswith(boekje.FOTO_EXT):
                os.remove(os.path.join(fotomap, oud))
        for i, (naam, data) in enumerate(fotos, 1):
            with open(os.path.join(fotomap, f'{i:02d}-{naam}'), 'wb') as fh:
                fh.write(data)
    regels = []
    try:
        u = boekje.maak(game_id, scope, velden.get('stad', ''), fotomap, log=regels.append, demo=demo)
    except SystemExit as fout:  # de API-functies stoppen met een leesbare melding
        return {'ok': False, 'melding': str(fout)}
    rel = lambda p: '/bestand/' + urllib.parse.quote(os.path.relpath(p, UITVOER).replace(os.sep, '/'))
    melding = '' if u['pdf'] else 'De PDF kon niet automatisch gemaakt worden: open de webpagina en kies Afdrukken > Opslaan als PDF.'
    if u['pdf'] and os.name == 'nt':
        try:
            os.startfile(os.path.dirname(u['pdf']))  # map openen, zodat ze de PDF meteen kan mailen
        except OSError:
            pass
    return {'ok': True, 'titel': e(u['titel']), 'pdf': rel(u['pdf']) if u['pdf'] else '', 'html': rel(u['html']),
            'melding': melding,
            'samenvatting': f'{u["teams"]} teams, {u["fotos"]} foto\'s uit Loquiz, {u["groepsfotos"]} groepsfoto(\'s).'
                            f'<br>Opgeslagen in {e(os.path.dirname(u["html"]))}'}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def stuur(self, code, data, soort):
        self.send_response(code)
        self.send_header('Content-Type', soort)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        pad = urllib.parse.unquote(urllib.parse.urlparse(self.path).path)
        if pad == '/':
            return self.stuur(200, PAGINA.encode('utf-8'), 'text/html; charset=utf-8')
        if pad.startswith('/bestand/'):
            doel = os.path.realpath(os.path.join(UITVOER, pad[len('/bestand/'):]))
            if doel.startswith(os.path.realpath(UITVOER) + os.sep) and os.path.isfile(doel):
                soort = 'application/pdf' if doel.endswith('.pdf') else 'text/html; charset=utf-8'
                with open(doel, 'rb') as fh:
                    return self.stuur(200, fh.read(), soort)
        self.stuur(404, b'Niet gevonden', 'text/plain')

    def do_POST(self):
        if self.path != '/maak':
            return self.stuur(404, b'Niet gevonden', 'text/plain')
        if not BEZIG.acquire(blocking=False):
            uit = {'ok': False, 'melding': 'Er wordt al een boekje gemaakt. Wacht even en probeer het opnieuw.'}
        else:
            try:
                uit = maak(*lees_formulier(self))
            except Exception:  # noqa: BLE001 - toon de fout in het scherm in plaats van stil te falen
                traceback.print_exc()
                uit = {'ok': False, 'melding': 'Er ging iets mis. Zie het zwarte venster voor details.'}
            finally:
                BEZIG.release()
        self.stuur(200, json.dumps(uit).encode('utf-8'), 'application/json')


def vrije_poort(begin=8765):
    for p in range(begin, begin + 20):
        with socket.socket() as s:
            if s.connect_ex(('127.0.0.1', p)) != 0:
                return p
    return 0


def main():
    poort = vrije_poort()
    server = ThreadingHTTPServer(('127.0.0.1', poort), Handler)
    adres = f'http://127.0.0.1:{server.server_address[1]}/'
    print(f'Fotoboekje maken draait op {adres}')
    print('Laat dit venster open zolang je boekjes maakt. Sluit het om te stoppen.')
    if '--geen-browser' not in sys.argv:
        threading.Timer(0.8, lambda: webbrowser.open(adres)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
