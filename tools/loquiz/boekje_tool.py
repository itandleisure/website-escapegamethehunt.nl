"""Invulscherm voor het fotoboek: spelleider-URL plakken, teamfoto en extra foto's erin, PDF en online pagina krijgen.

Start met "Boekje maken.bat" (of: python tools/loquiz/boekje_tool.py). Er opent een pagina in de browser op
http://127.0.0.1:8765. Alles draait op deze computer; de API-key en de GitHub-token blijven in .env.

Stappen:
1. "Teams en foto's ophalen": foto's uit Loquiz, teamfoto en extra foto's erbij;
2. controleren: teams (zoals de spelleiders) en foto's die niet in het boekje mogen uitvinken;
3. "Maak fotoboek": aanvullen met eigen foto's tot minimaal 8 en de PDF maken;
4. (als "online zetten" aan staat) in de browser: foto's verkleinen, alles versleutelen met een nieuw wachtwoord,
   en het versleutelde bestand online zetten op escapegamethehunt.nl/fotoboek/<code>/;
5. een kant-en-klare mail tonen met de link, het wachtwoord en de PDF.
Sluit het zwarte venster om te stoppen.
"""
import email.parser
import email.policy
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import threading
import traceback
import urllib.parse
import webbrowser
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import boekje  # noqa: E402
import fotoboek_web  # noqa: E402
from resultaten import HIER, e  # noqa: E402

UITVOER = os.path.join(HIER, 'uitvoer')
BEZIG = threading.Lock()
BOEK_ID = re.compile(r'^\d{6}-[a-z0-9]{12}$')
SOORTEN = {'.pdf': 'application/pdf', '.html': 'text/html; charset=utf-8', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
           '.png': 'image/png', '.webp': 'image/webp', '.bin': 'application/octet-stream'}
MAANDEN = ['januari', 'februari', 'maart', 'april', 'mei', 'juni', 'juli', 'augustus', 'september', 'oktober',
           'november', 'december']

PAGINA = r'''<!doctype html>
<html lang="nl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Fotoboek maken · The Hunt</title>
<style>
:root{--night:#141e29;--navy:#29394a;--signal:#f29222;--paper:#f3f5f7;--ink:#1c2834;--muted:#5a6878;--line:#dbe2e9}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font:400 16px/1.5 system-ui,-apple-system,'Segoe UI',Roboto,sans-serif}
header{background:var(--night);color:#fff;padding:18px 0}
.wrap{max-width:680px;margin:0 auto;padding:0 16px}
header b{font-size:20px}
header span{color:#a9b6c4;font-size:14px;margin-left:8px}
main{padding:28px 0 60px}
.kaart{background:#fff;border:1px solid var(--line);border-radius:12px;padding:22px;margin-bottom:18px}
label,.kop{display:block;font-weight:700;margin:0 0 6px}
.stap{display:inline-grid;place-items:center;width:24px;height:24px;border-radius:50%;background:var(--night);color:#fff;font-size:13px;margin-right:6px}
.hulp{color:var(--muted);font-size:14px;margin:-2px 0 8px}
.opt{font-weight:400;color:var(--muted)}
input[type=text],input[type=number]{width:100%;font:inherit;padding:11px 12px;border:1px solid var(--line);border-radius:8px}
input[type=number]{width:100px}
input:focus{outline:3px solid rgba(242,146,34,.35);border-color:var(--signal)}
.veld{margin-bottom:22px}
.veld:last-child{margin-bottom:0}
.drop{border:2px dashed var(--line);border-radius:10px;padding:20px;text-align:center;color:var(--muted);cursor:pointer}
.drop.over{border-color:var(--signal);background:#fff8ef}
.drop input{display:none}
.duimen{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
.duim{position:relative}
.duim img{width:84px;height:84px;object-fit:cover;border-radius:6px;display:block}
.duim.groot img{width:220px;height:150px}
.duim button{position:absolute;top:-6px;right:-6px;width:24px;height:24px;padding:0;border-radius:50%;background:var(--night);color:#fff;font-size:14px}
.vink{display:flex;gap:10px;align-items:flex-start;font-weight:700;cursor:pointer}
.vink input{width:20px;height:20px;margin:2px 0 0;flex:none}
.vink span{font-weight:400;color:var(--muted);display:block;font-size:14px}
button{font-family:inherit;font-weight:700;font-size:16px;line-height:1;background:var(--signal);color:var(--night);border:0;border-radius:999px;padding:14px 26px;cursor:pointer}
button.licht{background:#fff;border:1px solid var(--line);padding:10px 16px;font-size:14px}
button[disabled]{opacity:.6;cursor:wait}
.voortgang{display:none;margin-top:18px}
.voortgang li{margin:4px 0;color:var(--muted)}
.voortgang li.bezig{color:var(--ink);font-weight:700}
.voortgang li.klaar{color:#2e7d43}
.uitslag{display:none}
.uitslag.fout{display:block;background:#fdeeee;border:1px solid #f1c2c2;border-radius:10px;padding:16px;margin-top:18px}
#klaar a{color:#a85600;font-weight:700}
.gegevens{display:grid;grid-template-columns:max-content 1fr;gap:6px 14px;margin:16px 0 4px}
.gegevens dt{color:var(--muted)}
.gegevens dd{margin:0;font-weight:700;word-break:break-all}
.ww{font:700 20px ui-monospace,Consolas,monospace;letter-spacing:.06em}
textarea{width:100%;min-height:300px;font:inherit;font-size:14px;padding:12px;border:1px solid var(--line);border-radius:8px;margin-top:8px}
.rij{display:flex;flex-wrap:wrap;gap:8px 16px;align-items:center;margin-top:10px}
.keuze{display:none}
.keuze.open{display:block}
.teams{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:8px;margin:10px 0 18px}
.teams label{display:flex;gap:10px;align-items:center;border:1px solid var(--line);border-radius:8px;padding:10px 12px;cursor:pointer}
.teams label.uit{opacity:.5;text-decoration:line-through}
.teams input{width:18px;height:18px;flex:none}
.teams small{display:block;color:var(--muted);text-decoration:none}
.raster{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:8px;margin-top:10px}
.raster label{position:relative;cursor:pointer;display:block}
.raster img{width:100%;aspect-ratio:1;object-fit:cover;border-radius:8px;display:block;background:var(--line)}
.raster input{position:absolute;top:8px;left:8px;width:22px;height:22px;margin:0}
.raster small{display:block;font-size:12px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:3px}
.raster label.uit img{opacity:.25;filter:grayscale(1)}
.raster label.dicht{display:none}
.telling{font-weight:700;margin-top:14px}
.melding{background:#fff8ef;border:1px solid #f6d3a4;border-radius:8px;padding:10px 12px;margin-top:12px;font-size:14px}
</style></head>
<body>
<header><div class="wrap"><b>Fotoboek maken</b><span>The Hunt</span></div></header>
<main class="wrap">
<form id="f">
 <div class="kaart">
  <div class="veld">
    <label for="url"><span class="stap">1</span>Spelleider-URL</label>
    <p class="hulp">Bijvoorbeeld https://results.loquiz.com/F3CJ8WVUSC:VANWIJNEN. De foto's uit het spel worden automatisch opgehaald.</p>
    <input type="text" id="url" required placeholder="https://results.loquiz.com/..." autocomplete="off">
  </div>
  <div class="veld">
    <label for="stad">Plaatsnaam <span class="opt">(optioneel)</span></label>
    <p class="hulp">Leeg = "Bedankt voor het spelen van The Hunt". Ingevuld = "... van The Hunt in Den Haag".</p>
    <input type="text" id="stad" autocomplete="off">
  </div>
 </div>
 <div class="kaart">
  <div class="veld">
    <span class="kop"><span class="stap">2</span>Teamfoto <span class="opt">(één foto, komt groot bovenaan)</span></span>
    <p class="hulp">De groepsfoto van de spelleider. Geen teamfoto? Dan staat onze eigen foto op de voorkant.</p>
    <div class="drop" id="drop-team">Sleep de teamfoto hierheen of klik om te kiezen<input type="file" accept="image/*"></div>
    <div class="duimen" id="duim-team"></div>
  </div>
  <div class="veld">
    <span class="kop"><span class="stap">3</span>Extra foto's <span class="opt">(optioneel, zoveel als je wilt)</span></span>
    <p class="hulp">Bijvoorbeeld van de spelleider of het social media team. Ze komen bij de foto's uit het spel.</p>
    <div class="drop" id="drop-extra">Sleep foto's hierheen of klik om te kiezen<input type="file" accept="image/*" multiple></div>
    <div class="duimen" id="duim-extra"></div>
  </div>
  <div class="veld">
    <label for="min">Minimaal aantal foto's</label>
    <p class="hulp">Zijn er minder foto's, dan vullen we aan met onze eigen sfeerfoto's.</p>
    <input type="number" id="min" min="0" max="40" value="8">
  </div>
 </div>
 <div class="kaart">
  <label class="vink"><input type="checkbox" id="online" checked>
    <div>Ook online zetten met een wachtwoord<span>Op escapegamethehunt.nl/fotoboek/, niet vindbaar in Google, elke keer met een nieuw wachtwoord. Je krijgt meteen een mail om te versturen.</span></div></label>
 </div>
 <button type="submit" id="knop">Teams en foto's ophalen</button>
 <div class="kaart keuze" id="keuze" style="margin-top:18px">
  <span class="kop"><span class="stap">4</span>Controleer wat er in het boekje komt</span>
  <p class="hulp">Vink teams uit die er niet in horen, zoals de spelleiders: die tellen dan niet mee in de kilometers en hun foto's vallen weg. Klik op een foto om hem uit of aan te zetten.</p>
  <div class="teams" id="teams"></div>
  <div class="kop">Foto's</div>
  <div class="raster" id="raster"></div>
  <p class="telling" id="telling"></p>
  <button type="button" id="maak">Maak fotoboek</button>
 </div>
 <ol class="voortgang" id="voortgang">
   <li data-s="ophalen">Teams en foto's ophalen</li>
   <li data-s="maken">Fotoboek en PDF maken (ongeveer een minuut)</li>
   <li data-s="verkleinen">Foto's klaarmaken voor de website</li>
   <li data-s="versleutelen">Versleutelen met een nieuw wachtwoord</li>
   <li data-s="online">Online zetten</li>
 </ol>
 <div class="uitslag" id="uitslag"></div>
</form>
<div class="kaart uitslag" id="klaar"></div>
</main>
<script>
const $=id=>document.getElementById(id);
const teamfoto=[],extra=[];
function duimen(lijst,doos,groot){
  doos.innerHTML='';
  lijst.forEach((b,i)=>{const d=document.createElement('div');d.className='duim'+(groot?' groot':'');
    const im=document.createElement('img');im.src=URL.createObjectURL(b);const x=document.createElement('button');
    x.type='button';x.textContent='×';x.title='Weghalen';x.onclick=()=>{lijst.splice(i,1);duimen(lijst,doos,groot)};
    d.append(im,x);doos.appendChild(d)});
}
function dropzone(drop,lijst,doos,een){
  const inp=drop.querySelector('input');
  const voeg=bestanden=>{for(const b of bestanden){if(!b.type.startsWith('image/'))continue;if(een)lijst.length=0;lijst.push(b);if(een)break}
    duimen(lijst,doos,een)};
  drop.onclick=ev=>{if(ev.target!==inp)inp.click()};
  inp.onchange=()=>{voeg(inp.files);inp.value=''};
  ['dragenter','dragover'].forEach(t=>drop.addEventListener(t,ev=>{ev.preventDefault();drop.classList.add('over')}));
  ['dragleave','drop'].forEach(t=>drop.addEventListener(t,ev=>{ev.preventDefault();drop.classList.remove('over')}));
  drop.addEventListener('drop',ev=>voeg(ev.dataTransfer.files));
}
dropzone($('drop-team'),teamfoto,$('duim-team'),true);
dropzone($('drop-extra'),extra,$('duim-extra'),false);

const STAPPEN=['ophalen','maken','verkleinen','versleutelen','online'];
function stap(naam){const n=STAPPEN.indexOf(naam);document.querySelectorAll('#voortgang li').forEach(li=>{
  const i=STAPPEN.indexOf(li.dataset.s);li.className=i<n?'klaar':i===n?'bezig':''})}

// Foto verkleinen (JPEG): de online versie laadt dan snel en de website groeit niet onnodig.
async function verklein(blob,max){
  try{
    const bm=await createImageBitmap(blob,{imageOrientation:'from-image'});
    const f=Math.min(1,max/Math.max(bm.width,bm.height)),c=document.createElement('canvas');
    c.width=Math.round(bm.width*f);c.height=Math.round(bm.height*f);c.getContext('2d').drawImage(bm,0,0,c.width,c.height);
    const uit=await new Promise(r=>c.toBlob(r,'image/jpeg',.82));
    return uit&&uit.size<blob.size?uit:blob;
  }catch(e){return blob}
}
const ALFABET='23456789ABCDEFGHJKMNPQRSTUVWXYZ';
function willekeurig(alfabet,n){const r=crypto.getRandomValues(new Uint32Array(n));return [...r].map(x=>alfabet[x%alfabet.length]).join('')}
function nieuwWachtwoord(){return [0,1,2].map(()=>willekeurig(ALFABET,4)).join('-')}
function nieuwId(){const d=new Date(),p=x=>String(x).padStart(2,'0');
  return String(d.getFullYear()).slice(2)+p(d.getMonth()+1)+p(d.getDate())+'-'+willekeurig('abcdefghijkmnpqrstuvwxyz23456789',12)}

async function versleutel(ww,platte){
  const zout=crypto.getRandomValues(new Uint8Array(16)),iv=crypto.getRandomValues(new Uint8Array(12));
  const basis=await crypto.subtle.importKey('raw',new TextEncoder().encode(ww.toUpperCase().replace(/[^A-Z0-9]/g,'')),'PBKDF2',false,['deriveKey']);
  const k=await crypto.subtle.deriveKey({name:'PBKDF2',salt:zout,iterations:250000,hash:'SHA-256'},basis,{name:'AES-GCM',length:256},false,['encrypt']);
  const geheim=new Uint8Array(await crypto.subtle.encrypt({name:'AES-GCM',iv},k,platte));
  const uit=new Uint8Array(32+geheim.length);uit.set(new TextEncoder().encode('THB1'));uit.set(zout,4);uit.set(iv,20);uit.set(geheim,32);
  return uit;
}

async function pakIn(d){
  // alles (pagina, foto's, PDF) in één bestand: [lengte kop][kop JSON][bestanden achter elkaar]
  const delen=[],bestanden=[];let pos=0;
  const voeg=(naam,type,bytes,bewaar)=>{bestanden.push({naam,type,start:pos,lengte:bytes.length,bewaar});delen.push(bytes);pos+=bytes.length};
  for(const f of d.fotos){
    const klein=await verklein(await (await fetch(f.url)).blob(),1600);
    const ext=klein.type==='image/jpeg'?'.jpg':f.naam.slice(f.naam.lastIndexOf('.'));
    voeg('fotos/'+f.naam,klein.type||'image/jpeg',new Uint8Array(await klein.arrayBuffer()),f.naam.replace(/\.[^.]+$/,'')+ext);
  }
  if(d.pdf)voeg(d.pdf_naam,'application/pdf',new Uint8Array(await (await fetch(d.pdf)).arrayBuffer()));
  const html=await (await fetch(d.online)).text();
  const kop=new TextEncoder().encode(JSON.stringify({html,bestanden,titel:'Fotoboek · The Hunt',zip:'fotos-the-hunt'}));
  const totaal=new Uint8Array(4+kop.length+pos);new DataView(totaal.buffer).setUint32(0,kop.length);totaal.set(kop,4);
  let p=4+kop.length;for(const b of delen){totaal.set(b,p);p+=b.length}
  return totaal;
}

function toonKlaar(d,o){
  const k=$('klaar');k.className='kaart';
  let h='<b style="font-size:18px">Klaar: '+d.titel+'</b><br>'+d.samenvatting+
    '<div class="rij">'+(d.pdf?'<a href="'+d.pdf+'" target="_blank">Open de PDF</a>':'')+
    '<a href="'+d.html+'" target="_blank">PDF-versie als webpagina</a></div>';
  if(d.melding)h+='<div class="melding">'+d.melding+'</div>';
  if(o){
    h+='<dl class="gegevens"><dt>Link</dt><dd>'+(o.url?'<a href="'+o.url+'" target="_blank">'+o.url+'</a>':'niet online gezet')+'</dd>'+
       '<dt>Wachtwoord</dt><dd class="ww">'+o.ww+'</dd>'+(o.url?'<dt>Online tot</dt><dd>'+d.tot+'</dd>':'')+'</dl>';
    if(o.melding)h+='<div class="melding">'+o.melding+'</div>';
    if(o.url)h+='<div class="kop" style="margin-top:18px">Mail voor de klant (de PDF zit in de map die net is geopend)</div><textarea id="mail"></textarea>'+
      '<div class="rij"><button type="button" class="licht" id="kopieer">Kopieer mail</button>'+
      '<button type="button" class="licht" id="kopieer-ww">Kopieer wachtwoord</button><span id="gekopieerd" class="opt"></span></div>';
  }
  k.innerHTML=h;
  if(o&&o.url){
    $('mail').value=mailtekst(d,o);
    const kopieer=(tekst,wat)=>navigator.clipboard.writeText(tekst).then(()=>$('gekopieerd').textContent=wat+' gekopieerd.')
      .catch(()=>{$('mail').select();document.execCommand('copy');$('gekopieerd').textContent='Gekopieerd.'});
    $('kopieer').onclick=()=>kopieer($('mail').value,'Mail');
    $('kopieer-ww').onclick=()=>kopieer(o.ww,'Wachtwoord');
  }
  k.scrollIntoView({behavior:'smooth'});
}
function mailtekst(d,o){
  return 'Onderwerp: Jullie fotoboek van The Hunt\n\n'+
  'Hoi,\n\nMissie volbracht! Bedankt voor het spelen van The Hunt'+(d.stad?' in '+d.stad:'')+'. '+
  'Jullie fotoboek staat klaar, met alle foto\'s van de dag.\n\n'+
  'Bekijk het fotoboek online:\n'+o.url+'\nWachtwoord: '+o.ww+'\n\n'+
  'Op die pagina kun je alle foto\'s in één keer downloaden (zip) of per foto. '+
  (d.pdf?'Het fotoboek als PDF zit als bijlage bij deze mail en staat ook op de pagina.':'')+'\n\n'+
  'De pagina blijft online tot '+d.tot+', dus download de foto\'s op tijd. Deel de link en het wachtwoord gerust met de hele groep.\n\n'+
  'Vonden jullie het een toffe dag? Dan zijn we heel blij met een review.\n\n'+
  'Met vriendelijke groet,\n\nEscape Game The Hunt\nescapegamethehunt.nl · 085 004 7719';
}

let gehaald=null;
function telling(){
  const aan=[...document.querySelectorAll('#raster input')].filter(i=>i.checked&&!i.closest('label').classList.contains('dicht')).length;
  const teams=[...document.querySelectorAll('#teams input')].filter(i=>i.checked).length;
  const min=+$('min').value||0;
  $('telling').textContent=teams+' teams en '+aan+' foto\'s in het boekje'+(aan<min?', aangevuld met '+(min-aan)+' eigen sfeerfoto\'s':'')+'.';
}
function toonKeuze(d){
  gehaald=d;
  $('teams').innerHTML='';$('raster').innerHTML='';
  d.teams.forEach(t=>{
    const l=document.createElement('label');
    l.innerHTML='<input type="checkbox" checked><span><b></b><small></small></span>';
    l.querySelector('b').textContent=t.naam;
    l.querySelector('small').textContent=t.km.toLocaleString('nl-NL',{maximumFractionDigits:1})+' km · '+t.fotos+' foto\'s';
    const cb=l.querySelector('input');cb.dataset.i=t.i;
    cb.onchange=()=>{l.classList.toggle('uit',!cb.checked);
      document.querySelectorAll('#raster label[data-team="'+t.i+'"]').forEach(f=>f.classList.toggle('dicht',!cb.checked));telling()};
    $('teams').appendChild(l);
  });
  const fotos=(d.teamfoto?[Object.assign({bijschrift:'Teamfoto'},d.teamfoto)]:[]).concat(d.fotos);
  fotos.forEach(f=>{
    const l=document.createElement('label');if(f.team!=null)l.dataset.team=f.team;
    l.innerHTML='<input type="checkbox" checked><img loading="lazy" alt=""><small></small>';
    l.querySelector('img').src=f.url;l.querySelector('small').textContent=f.bijschrift||(f.bron==='extra'?'Extra foto':'');
    const cb=l.querySelector('input');cb.dataset.naam=f.naam;
    cb.onchange=()=>{l.classList.toggle('uit',!cb.checked);telling()};
    $('raster').appendChild(l);
  });
  $('keuze').classList.add('open');telling();$('keuze').scrollIntoView({behavior:'smooth'});
}
$('min').oninput=()=>{if(gehaald)telling()};

$('f').onsubmit=async ev=>{
  ev.preventDefault();
  const knop=$('knop'),uit=$('uitslag'),vg=$('voortgang');
  $('klaar').className='uitslag';uit.className='uitslag';$('keuze').classList.remove('open');knop.disabled=true;
  vg.style.display='block';vg.querySelectorAll('li').forEach(li=>li.style.display=li.dataset.s==='ophalen'?'':'none');
  stap('ophalen');
  const fd=new FormData();fd.append('url',$('url').value);fd.append('stad',$('stad').value);
  // uploads eerst verkleinen tot 2400 px: sneller, en nog steeds scherp in de PDF
  for(const b of teamfoto)fd.append('teamfoto',await verklein(b,2400),b.name);
  for(const b of extra)fd.append('extra',await verklein(b,2400),b.name);
  let d;
  try{d=await (await fetch('/ophalen',{method:'POST',body:fd})).json()}
  catch(err){d={ok:false,melding:'Er ging iets mis: '+err}}
  vg.style.display='none';knop.disabled=false;knop.textContent='Opnieuw ophalen';
  if(!d.ok){uit.className='uitslag fout';uit.textContent=d.melding;return}
  toonKeuze(d);
};

$('maak').onclick=async()=>{
  if(!gehaald)return;
  const knop=$('maak'),uit=$('uitslag'),online=$('online').checked,vg=$('voortgang');
  $('klaar').className='uitslag';uit.className='uitslag';knop.disabled=true;$('knop').disabled=true;
  vg.style.display='block';vg.querySelectorAll('li').forEach(li=>li.style.display=li.dataset.s==='ophalen'?'none':(online||li.dataset.s==='maken')?'':'none');
  stap('maken');
  const keuze={sleutel:gehaald.sleutel,min:+$('min').value||0,
    uit_teams:[...document.querySelectorAll('#teams input')].filter(i=>!i.checked).map(i=>+i.dataset.i),
    uit_fotos:[...document.querySelectorAll('#raster input')].filter(i=>!i.checked).map(i=>i.dataset.naam)};
  let d;
  try{d=await (await fetch('/maak',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(keuze)})).json()}
  catch(err){d={ok:false,melding:'Er ging iets mis: '+err}}
  const klaarZetten=()=>{vg.style.display='none';knop.disabled=false;$('knop').disabled=false};
  if(!d.ok){uit.className='uitslag fout';uit.textContent=d.melding;klaarZetten();return}
  let o=null;
  if(online){
    o={ww:nieuwWachtwoord(),id:nieuwId()};
    try{
      stap('verkleinen');const platte=await pakIn(d);
      stap('versleutelen');const geheim=await versleutel(o.ww,platte);
      stap('online');
      const r=await (await fetch('/publiceer?sleutel='+encodeURIComponent(d.sleutel)+'&id='+o.id,{method:'POST',body:geheim})).json();
      o.url=r.url||'';o.melding=r.melding||'';
    }catch(err){o.melding='Online zetten mislukt: '+err}
  }
  klaarZetten();toonKlaar(d,o);
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
    velden, bestanden = {}, {}
    for deel in bericht.iter_parts():
        naam = deel.get_param('name', header='content-disposition')
        if deel.get_filename():
            data = deel.get_payload(decode=True) or b''
            if data:
                bestanden.setdefault(naam, []).append((schoon(deel.get_filename()), data))
        elif naam:
            velden[naam] = (deel.get_payload(decode=True) or b'').decode('utf-8', 'replace').strip()
    return velden, bestanden


def bestand_url(p):
    return '/bestand/' + urllib.parse.quote(os.path.relpath(p, UITVOER).replace(os.sep, '/'))


def ophalen(velden, bestanden):
    """Stap 1: teams en foto's ophalen (nog zonder aanvulling), zodat je kunt kiezen wat erin komt."""
    demo = velden.get('url', '').strip().lower() == 'demo'  # "demo" als URL: voorbeeld zonder API
    try:
        game_id, scope = ('DEMO', '') if demo else boekje.lees_url(velden.get('url', ''))
    except ValueError as fout:
        return {'ok': False, 'melding': str(fout)}
    regels = []
    with tempfile.TemporaryDirectory() as tmp:
        def bewaar(lijst, voorvoegsel):
            paden = []
            for i, (naam, data) in enumerate(lijst, 1):
                pad = os.path.join(tmp, f'{voorvoegsel}-{i:02d}-{naam}')
                with open(pad, 'wb') as fh:
                    fh.write(data)
                paden.append(pad)
            return paden
        team = bewaar(bestanden.get('teamfoto', [])[:1], 'team')
        extra = bewaar(bestanden.get('extra', []), 'extra')
        try:  # vervang=True: alleen wat nu is geüpload telt, niets van een eerdere poging
            g = boekje.verzamel(game_id, scope, velden.get('stad', ''), team[0] if team else None, extra, 0,
                                demo=demo, log=regels.append, vervang=True)
        except SystemExit as fout:  # de API-functies stoppen met een leesbare melding
            return {'ok': False, 'melding': str(fout)}
    fmap = os.path.join(boekje.werkmap(g['sleutel']), 'fotos')
    per_team = {}
    for f in g['fotos']:
        if f.get('team') is not None:
            per_team[f['team']] = per_team.get(f['team'], 0) + 1
    return {'ok': True, 'sleutel': g['sleutel'],
            'teams': [{'i': i, 'naam': t['naam'], 'km': t['km'], 'fotos': per_team.get(i, 0)} for i, t in enumerate(g['teams'])],
            'teamfoto': {'naam': g['teamfoto'], 'url': bestand_url(os.path.join(fmap, g['teamfoto'])), 'bron': 'team'}
            if g.get('teamfoto') else None,
            'fotos': [{'naam': f['bestand'], 'url': bestand_url(os.path.join(fmap, f['bestand'])), 'bron': f['bron'],
                       'bijschrift': f['bijschrift'], 'team': f.get('team')} for f in g['fotos']]}


def maak(keuze):
    """Stap 2: met de keuze (teams en foto's eruit) aanvullen, de PDF en de online pagina maken."""
    sleutel = str(keuze.get('sleutel') or '')
    if not re.match(r'^[A-Za-z0-9-]+$', sleutel) or not os.path.exists(os.path.join(boekje.werkmap(sleutel), 'boekje-alles.json')):
        return {'ok': False, 'melding': 'Haal eerst de teams en foto\'s op.'}
    try:
        minimaal = max(0, min(40, int(keuze.get('min', boekje.MIN_FOTOS))))
        uit_teams = [int(i) for i in keuze.get('uit_teams') or []]
    except (TypeError, ValueError):
        return {'ok': False, 'melding': 'Ongeldige keuze.'}
    uit_fotos = [str(n) for n in keuze.get('uit_fotos') or []]
    regels = []
    g = boekje.kies(sleutel, uit_teams, uit_fotos, minimaal, log=regels.append)
    if not g['teams']:
        return {'ok': False, 'melding': 'Er staat geen enkel team meer aan. Vink minstens één team aan.'}
    u = boekje.opmaken(sleutel, log=regels.append)
    fmap = os.path.join(u['map'], 'fotos')
    lijst = ([g['teamfoto']] if g.get('teamfoto') else []) + [f['bestand'] for f in g['fotos']]
    soorten = {b: sum(1 for f in g['fotos'] if f['bron'] == b) for b in ('loquiz', 'extra', 'eigen')}
    tot = date.today() + timedelta(days=fotoboek_web.config()['dagen'])
    melding = '' if u['pdf'] else 'De PDF kon niet automatisch gemaakt worden: open de webpagina en kies Afdrukken > Opslaan als PDF.'
    return {'ok': True, 'sleutel': sleutel, 'titel': e(u['titel']), 'stad': g.get('stad') or '',
            'pdf': bestand_url(u['pdf']) if u['pdf'] else '', 'pdf_naam': os.path.basename(u['pdf']) if u['pdf'] else '',
            'html': bestand_url(u['html']), 'online': bestand_url(u['online']), 'melding': melding,
            'fotos': [{'naam': n, 'url': bestand_url(os.path.join(fmap, n))} for n in lijst],
            'tot': f'{tot.day} {MAANDEN[tot.month - 1]} {tot.year}',
            'samenvatting': f'{u["teams"]} teams, {u["fotos"]} foto\'s ({soorten["loquiz"]} uit het spel, '
                            f'{soorten["extra"]} extra, {soorten["eigen"]} eigen), teamfoto: {"ja" if u["teamfoto"] else "nee"}.'
                            f'<br>Opgeslagen in {e(u["map"])}'}


def publiceer(sleutel, boek_id, data):
    if not BOEK_ID.match(boek_id or '') or not re.match(r'^[A-Za-z0-9-]+$', sleutel or ''):
        return {'melding': 'Ongeldige aanvraag.'}
    if data[:4] != b'THB1':
        return {'melding': 'Het versleutelde bestand klopt niet.'}
    lokaal = os.path.join(boekje.werkmap(sleutel), 'online', boek_id)  # altijd ook een kopie op deze computer
    os.makedirs(lokaal, exist_ok=True)
    with open(os.path.join(lokaal, 'data.bin'), 'wb') as fh:
        fh.write(data)
    with open(os.path.join(lokaal, 'index.html'), 'w', encoding='utf-8') as fh:
        fh.write(fotoboek_web.slot())
    try:  # map openen, zodat de PDF meteen als bijlage kan
        if os.name == 'nt':
            os.startfile(boekje.werkmap(sleutel))
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', boekje.werkmap(sleutel)])
    except OSError:
        pass
    try:
        url = fotoboek_web.publiceer(boek_id, data, log=print)
    except fotoboek_web.Fout as fout:
        return {'melding': f'{e(str(fout))} Het versleutelde fotoboek staat wel op deze computer in {e(lokaal)}.'}
    return {'url': url, 'melding': 'Het kan een paar minuten duren voordat de link werkt: de website wordt eerst bijgewerkt.'}


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

    def json(self, uit):
        self.stuur(200, json.dumps(uit).encode('utf-8'), 'application/json')

    def do_GET(self):
        pad = urllib.parse.unquote(urllib.parse.urlparse(self.path).path)
        if pad == '/':
            return self.stuur(200, PAGINA.encode('utf-8'), 'text/html; charset=utf-8')
        if pad.startswith('/bestand/'):
            doel = os.path.realpath(os.path.join(UITVOER, pad[len('/bestand/'):]))
            if doel.startswith(os.path.realpath(UITVOER) + os.sep) and os.path.isfile(doel):
                soort = SOORTEN.get(os.path.splitext(doel)[1].lower(), 'application/octet-stream')
                with open(doel, 'rb') as fh:
                    return self.stuur(200, fh.read(), soort)
        self.stuur(404, b'Niet gevonden', 'text/plain')

    def do_POST(self):
        url = urllib.parse.urlparse(self.path)
        if url.path not in ('/ophalen', '/maak', '/publiceer'):
            return self.stuur(404, b'Niet gevonden', 'text/plain')
        if not BEZIG.acquire(blocking=False):
            return self.json({'ok': False, 'melding': 'Er wordt al een fotoboek gemaakt. Wacht even en probeer het opnieuw.'})
        try:
            if url.path == '/ophalen':
                uit = ophalen(*lees_formulier(self))
            elif url.path == '/maak':
                uit = maak(json.loads(self.rfile.read(int(self.headers.get('Content-Length') or 0)) or b'{}'))
            else:
                q = urllib.parse.parse_qs(url.query)
                data = self.rfile.read(int(self.headers.get('Content-Length') or 0))
                uit = publiceer(q.get('sleutel', [''])[0], q.get('id', [''])[0], data)
        except Exception:  # noqa: BLE001 - toon de fout in het scherm in plaats van stil te falen
            traceback.print_exc()
            uit = {'ok': False, 'melding': 'Er ging iets mis. Zie het zwarte venster voor details.'}
        finally:
            BEZIG.release()
        self.json(uit)


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
    print(f'Fotoboek maken draait op {adres}')
    print('Laat dit venster open zolang je fotoboeken maakt. Sluit het om te stoppen.')
    if not fotoboek_web.config()['token']:
        print('Let op: geen GITHUB_TOKEN in .env. Fotoboeken worden dan niet online gezet, wel op deze computer bewaard.')
    if '--geen-browser' not in sys.argv:
        threading.Timer(0.8, lambda: webbrowser.open(adres)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
