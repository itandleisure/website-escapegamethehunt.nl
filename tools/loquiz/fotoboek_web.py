"""Online fotoboek: de pagina voor de klant, versleuteld met een wachtwoord, en het online zetten via GitHub.

Hoe het werkt
- inhoud() maakt de HTML van het fotoboek (teamfoto groot bovenaan, cijfers, video, alle foto's, downloads, review).
- Het invulscherm (boekje_tool.py) pakt die HTML samen met de foto's en de PDF in één bestand en versleutelt dat in
  de browser met AES-256-GCM. De sleutel komt uit het wachtwoord (PBKDF2, 250.000 rondes). Elk boekje krijgt een nieuw
  willekeurig wachtwoord en een onraadbare map, bijvoorbeeld /fotoboek/261111-k3m9q2x7p4wd/.
- slot() is de pagina die online staat: noindex, alleen een wachtwoordveld. Pas na het juiste wachtwoord ontsleutelt
  de browser de inhoud. Zonder wachtwoord is data.bin onleesbaar, ook al staat de repository openbaar.
- publiceer() zet index.html en data.bin met één commit in docs/fotoboek/ via de GitHub API (GITHUB_TOKEN in .env) en
  ruimt boekjes op die ouder zijn dan FOTOBOEK_BEWAAR_DAGEN.

Instellingen in .env (alleen GITHUB_TOKEN is verplicht om online te zetten):
    GITHUB_TOKEN=github_pat_...            fine-grained token, alleen deze repository, Contents: Read and write
    FOTOBOEK_REPO=itandleisure/website-escapegamethehunt.nl
    FOTOBOEK_BRANCH=main
    FOTOBOEK_MAP=docs/fotoboek
    FOTOBOEK_URL=https://escapegamethehunt.nl/fotoboek
    FOTOBOEK_BEWAAR_DAGEN=90
"""
import base64
import json
import os
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta

from resultaten import ROOT, e

SITE = json.load(open(os.path.join(ROOT, 'src', 'data', 'site.json'), encoding='utf-8'))
URL = SITE['url']


def instelling(naam, standaard=''):
    waarde = os.environ.get(naam, '').strip()
    pad = os.path.join(ROOT, '.env')
    if not waarde and os.path.exists(pad):
        for regel in open(pad, encoding='utf-8-sig'):
            regel = regel.strip()
            if regel.startswith(naam + '='):
                waarde = regel.split('=', 1)[1].strip().strip('"').strip("'")
    return waarde or standaard


def config():
    return {'token': instelling('GITHUB_TOKEN'),
            'repo': instelling('FOTOBOEK_REPO', 'itandleisure/website-escapegamethehunt.nl'),
            'branch': instelling('FOTOBOEK_BRANCH', 'main'),
            'map': instelling('FOTOBOEK_MAP', 'docs/fotoboek').strip('/'),
            'url': instelling('FOTOBOEK_URL', URL + '/fotoboek').rstrip('/'),
            'dagen': int(instelling('FOTOBOEK_BEWAAR_DAGEN', '90') or 90)}


# ---------------------------------------------------------------- de inhoud van het fotoboek

def inhoud(g, pdf_naam):
    """HTML van het fotoboek. Foto's en PDF staan als data-f="..." en worden na het ontsleutelen ingevuld."""
    import boekje as b
    T, k = b.TEKST, b.KENGETALLEN
    deel = b.deel_links(T['hunter_deeltekst'], T['hunter_url'])
    c = b.cijfers(g['teams'])
    stad = g.get('stad') or ''
    team = g.get('teamfoto')
    held = (f'<img class="held-foto" data-f="fotos/{e(team)}" alt="Teamfoto">' if team
            else f'<img class="held-foto" src="{URL}{b.VOORKANT_FOTO}" alt="">')
    rijen = ''.join(f'<tr><td>{e(n)}</td><td>{b.nl(d, 1)}</td><td>{b.nl(s)}</td><td>{b.nl(kc)}</td><td>{b.nl(co, 2)}</td></tr>'
                    for n, d, s, kc, co in c['rijen'])
    fotos = ''
    for i, f in enumerate(g['fotos']):
        bij = f.get('bijschrift') or ''
        fotos += (f'<button class="foto" data-i="{i}" type="button"><img data-f="fotos/{e(f["bestand"])}" alt="{e(bij or "Foto")}"'
                  f' loading="lazy">' + (f'<span>{e(bij)}</span>' if bij else '') + '</button>')
    kaarten = ''.join(
        (f'<a class="kaart" href="{e(s["link"])}" target="_blank" rel="noopener">' if s.get('link') else '<div class="kaart">')
        + (f'<img src="{e(s["foto"] if s["foto"].startswith("http") else URL + s["foto"])}" alt="" loading="lazy">' if s.get('foto') else '')
        + f'<div class="in"><b>{e(s["naam"])}</b><span>{e(s["tekst"])}</span></div>' + ('</a>' if s.get('link') else '</div>')
        for s in b.SPELLEN)
    google = SITE.get('google_review_url') or ''
    review_knoppen = ((f'<a class="knop" href="{e(google)}" target="_blank" rel="noopener">Google-review</a>'
                       f'<a class="knop licht" href="{e(T["review_url"])}" target="_blank" rel="noopener">Review via onze website</a>')
                      if google else
                      f'<a class="knop" href="{e(T["review_url"])}" target="_blank" rel="noopener">Laat een review achter</a>')
    pdf_knop = (f'<a class="knop" data-f="{e(pdf_naam)}" download="{e(pdf_naam)}">Download het fotoboek (PDF)</a>'
                if pdf_naam else '')
    n = len(g['fotos'])
    return f'''<style>
.fb{{--night:#141e29;--navy:#29394a;--signal:#f29222;--paper:#f3f5f7;--ink:#1c2834;--muted:#5a6878;--line:#dbe2e9;
  --on-dark:#e7edf3;--on-dark-muted:#a9b6c4;--mono:ui-monospace,'Cascadia Mono',Consolas,monospace;
  font:400 17px/1.6 'Lato',system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;color:var(--ink);background:#fff}}
.fb *{{box-sizing:border-box}}
.fb img{{max-width:100%;display:block}}
.fb .wrap{{max-width:1120px;margin:0 auto;padding:0 16px}}
.fb .label{{font:700 .75rem/1.2 var(--mono);letter-spacing:.14em;text-transform:uppercase;color:#a85600}}
.fb h1,.fb h2,.fb h3{{margin:0;line-height:1.1;letter-spacing:-.01em}}
.fb h2{{font-size:clamp(1.7rem,3.6vw,2.4rem);margin:.3em 0 .5em}}
.fb section{{padding:56px 0}}
.fb .held{{position:relative;background:var(--night);color:#fff}}
.fb .held-foto{{width:100%;height:min(78vh,760px);object-fit:cover}}
.fb .held .over{{position:absolute;inset:auto 0 0 0;padding:120px 0 36px;background:linear-gradient(180deg,rgba(20,30,41,0),rgba(20,30,41,.92))}}
.fb .held .label{{color:var(--signal)}}
.fb .held h1{{font-size:clamp(2rem,5.5vw,3.8rem);margin:.25em 0 .6em;max-width:18ch}}
.fb .held h1 em{{font-style:normal;color:var(--signal)}}
.fb .logo{{position:absolute;top:20px;left:20px;height:64px;width:auto;z-index:2}}
.fb .knoppen{{display:flex;flex-wrap:wrap;gap:10px}}
.fb .knop{{display:inline-flex;align-items:center;gap:.5em;background:var(--signal);color:var(--night);font-weight:700;padding:.85em 1.4em;
  border-radius:999px;text-decoration:none;border:0;cursor:pointer;font:inherit;font-weight:700}}
.fb .knop.licht{{background:rgba(255,255,255,.12);color:#fff;border:1px solid rgba(255,255,255,.35)}}
.fb .tegels{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:24px 0}}
.fb .tegel{{background:var(--paper);border-radius:12px;padding:18px}}
.fb .tegel b{{display:block;font-size:1.9rem;line-height:1.1;color:var(--navy)}}
.fb .tegel span{{font-size:.9rem;color:var(--muted)}}
.fb .tegel.oranje{{background:var(--navy)}}
.fb .tegel.oranje b{{color:var(--signal)}}
.fb .tegel.oranje span{{color:var(--on-dark-muted)}}
.fb .tabel{{overflow-x:auto}}
.fb table{{width:100%;border-collapse:collapse;font-size:.95rem;min-width:520px}}
.fb th{{font:700 .72rem var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--muted);text-align:right;padding:0 10px 8px;border-bottom:2px solid var(--navy)}}
.fb td{{padding:8px 10px;border-bottom:1px solid var(--line);text-align:right;font-variant-numeric:tabular-nums}}
.fb th:first-child,.fb td:first-child{{text-align:left;padding-left:0;font-weight:700}}
.fb .klein{{font-size:.8rem;color:var(--muted);margin-top:10px}}
.fb .video video{{width:100%;border-radius:12px;background:#000;display:block}}
.fb .grijs{{background:var(--paper)}}
.fb .kop-rij{{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:end;gap:12px;margin-bottom:20px}}
.fb .raster{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:10px}}
.fb .foto{{position:relative;padding:0;border:0;background:#ddd;border-radius:8px;overflow:hidden;cursor:zoom-in;aspect-ratio:1}}
.fb .foto img{{width:100%;height:100%;object-fit:cover;transition:transform .2s}}
.fb .foto:hover img{{transform:scale(1.04)}}
.fb .foto span{{position:absolute;left:8px;bottom:8px;background:rgba(20,30,41,.75);color:#fff;font:600 .72rem var(--mono);letter-spacing:.05em;
  text-transform:uppercase;padding:3px 7px;border-radius:4px;max-width:calc(100% - 16px);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.fb .donker{{background:var(--night);color:var(--on-dark)}}
.fb .donker h2,.fb .donker h3{{color:#fff}}
.fb .donker .label{{color:var(--signal)}}
.fb .donker p{{color:var(--on-dark-muted)}}
.fb .kaarten{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin-top:16px}}
.fb .kaart{{border:1px solid rgba(255,255,255,.15);border-top:3px solid var(--signal);border-radius:10px;overflow:hidden;color:inherit;text-decoration:none;display:block;background:#1f2b38}}
.fb .kaart img{{width:100%;aspect-ratio:16/9;object-fit:cover}}
.fb .kaart .in{{padding:16px}}
.fb .rv{{display:grid;grid-template-columns:1fr 1fr;gap:28px;align-items:center}}
.fb .rv img{{border-radius:12px;width:100%;aspect-ratio:4/3;object-fit:cover}}
@media (max-width:760px){{.fb .rv{{grid-template-columns:1fr}}}}
.fb .kaart b{{display:block;color:#fff;font-size:1.1rem}}
.fb .kaart span{{font-size:.92rem;color:var(--on-dark-muted)}}
.fb .hunter{{margin-top:40px;display:grid;grid-template-columns:minmax(0,2fr) minmax(0,3fr);background:var(--signal);
  color:var(--night);border-radius:12px;overflow:hidden;text-decoration:none}}
.fb .hunter img{{width:100%;height:100%;min-height:220px;object-fit:cover}}
.fb .hunter .in{{padding:24px;display:flex;flex-direction:column;align-items:flex-start;gap:6px}}
@media (max-width:640px){{.fb .hunter{{grid-template-columns:1fr}}.fb .hunter img{{min-height:0;aspect-ratio:16/9}}}}
.fb .hunter b{{display:block;font-size:1.3rem;margin:.2em 0 .3em}}
.fb .hunter .label{{color:var(--night);opacity:.75}}
.fb .hunter p{{margin:0;color:var(--night);max-width:60ch}}
.fb .hunter .hk{{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px}}
.fb .hunter .hk a{{text-decoration:none;font-weight:700;border:2px solid var(--night);border-radius:999px;padding:.6em 1.1em;white-space:nowrap;color:var(--night)}}
.fb .hunter .hk a.vol{{background:var(--night);color:#fff}}
.fb footer{{background:var(--night);color:var(--on-dark-muted);border-top:1px solid rgba(255,255,255,.12);padding:28px 0;font-size:.9rem}}
.fb footer .wrap{{display:flex;flex-wrap:wrap;gap:16px;justify-content:space-between;align-items:center}}
.fb footer a{{color:#fff;text-decoration:none}}
.fb footer img{{height:48px;width:auto}}
.fb .lb{{position:fixed;inset:0;background:rgba(10,14,20,.94);display:none;z-index:50;align-items:center;justify-content:center;padding:56px 12px 72px}}
.fb .lb.open{{display:flex}}
.fb .lb img{{max-width:100%;max-height:100%;object-fit:contain;border-radius:6px}}
.fb .lb .balk{{position:absolute;left:0;right:0;bottom:14px;display:flex;justify-content:center;gap:10px}}
.fb .lb .dicht{{position:absolute;top:10px;right:14px;background:none;border:0;color:#fff;font-size:2rem;cursor:pointer;line-height:1}}
.fb .lb .pijl{{position:absolute;top:50%;transform:translateY(-50%);background:rgba(255,255,255,.12);border:0;color:#fff;width:48px;height:48px;border-radius:50%;font-size:1.4rem;cursor:pointer}}
.fb .lb .vorige{{left:10px}}.fb .lb .volgende{{right:10px}}
.fb .bg-logo{{float:right;width:120px;height:120px;margin:0 0 16px 24px}}
@media (max-width:600px){{.fb .bg-logo{{width:84px;height:84px}}.fb section{{padding:40px 0}}.fb .logo{{height:48px}}.fb .raster{{grid-template-columns:repeat(2,1fr);gap:6px}}}}
</style>
<div class="fb">
  <header class="held">
    <img class="logo" src="{URL}{SITE["logo"]}" alt="The Hunt">
    {held}
    <div class="over"><div class="wrap">
      <div class="label">{e(T["label"])}</div>
      <h1>{e(T["bedankt"])}{f" in <em>{e(stad)}</em>" if stad else ""}</h1>
      <div class="knoppen">{pdf_knop}<button class="knop licht" type="button" data-zip>Download alle {n} foto's (.zip)</button></div>
    </div></div>
  </header>

  <section><div class="wrap">
    <div class="label">{e(T["label"])}</div>
    <h2>{e(T["cijfers_kop"])}</h2>
    <p style="color:var(--muted);max-width:65ch">{e(T["cijfers"])}</p>
    <div class="tegels">
      <div class="tegel"><b>{b.nl(c["gem_km"], 1)} km</b><span>gemiddeld gelopen per team</span></div>
      <div class="tegel"><b>{b.nl(c["gem_km"] * k["stappen_per_km"])}</b><span>stappen per persoon, gemiddeld</span></div>
      <div class="tegel"><b>{b.nl(c["tot_km"], 1)} km</b><span>samen gelopen door {len(g["teams"])} teams</span></div>
      <div class="tegel oranje"><b>{b.nl(c["tot_co2"], 1)} kg</b><span>CO₂ bespaard ten opzichte van de auto</span></div>
    </div>
    <div class="tabel"><table><thead><tr><th>Team</th><th>km</th><th>stappen p.p.</th><th>kcal p.p.</th><th>kg CO₂ bespaard</th></tr></thead>
      <tbody>{rijen}</tbody></table></div>
    <p class="klein">Indicatief: {b.nl(k["stappen_per_km"])} stappen en {k["kcal_per_km"]} kcal per km per persoon, {b.nl(k["co2_auto_per_km"], 2)} kg CO₂ per autokilometer, één auto per team.</p>
  </div></section>

  <section class="grijs"><div class="wrap">
    <div class="kop-rij"><div><div class="label">{e(T["label"])}</div><h2 style="margin-bottom:0">{e(T["fotos_kop"])}</h2></div>
      <button class="knop" type="button" data-zip>Download alle foto's (.zip)</button></div>
    <div class="raster">{fotos}</div>
  </div></section>

  <section class="video"><div class="wrap">
    <div class="label">{e(T["label"])}</div>
    <h2>{e(T["video_kop"])}</h2>
    <video controls preload="none" playsinline poster="{URL}{b.VIDEO_POSTER}" src="{e(b.VIDEO)}"></video>
  </div></section>

  <section class="donker"><div class="wrap">
    <div class="rv">
      <div><div class="label">{e(T["label"])}</div>
        <h2>{e(T["review_kop"])}</h2>
        <p style="max-width:60ch">{e(T["review"])}</p>
        <div class="knoppen" style="margin-top:18px">{review_knoppen}</div></div>
      <img src="{URL}{b.REVIEW_FOTO}" alt="" loading="lazy">
    </div>
    <div class="hunter">
      <img src="{URL}{b.HUNTER_FOTO}" alt="" loading="lazy">
      <div class="in"><div class="label">{e(T["hunter_label"])}</div><b>{e(T["hunter_kop"])}</b><p>{e(T["hunter"])}</p>
      <p><strong>{e(T["hunter_doorsturen"])}</strong></p>
      <div class="hk"><a class="vol" href="{e(deel["whatsapp"])}" target="_blank" rel="noopener">Stuur door via WhatsApp</a>
      <a href="{e(deel["mail"])}">Stuur door per mail</a>
      <a href="{e(T["hunter_url"])}" target="_blank" rel="noopener">Bekijk de vacature →</a></div></div>
    </div>
  </div></section>

  <section class="donker" style="border-top:1px solid rgba(255,255,255,.1)"><div class="wrap">
    <img class="bg-logo" src="{URL}{b.BADASS_LOGO}" alt="Badass Games" loading="lazy">
    <div class="label">Badass Games</div>
    <h2>{e(T["spellen_kop"])}</h2>
    <p style="max-width:65ch">{e(T["spellen"])}</p>
    <div class="kaarten">{kaarten}</div>
  </div></section>

  <footer><div class="wrap">
    <img src="{URL}{SITE["logo"]}" alt="The Hunt">
    <div><a href="{URL}">{e(URL.replace("https://", ""))}</a> · <a href="mailto:{e(SITE["email"])}">{e(SITE["email"])}</a> ·
      <a href="tel:{e(SITE["phone"])}">{e(SITE["phone_display"])}</a></div>
  </div></footer>

  <div class="lb" id="lb" role="dialog" aria-label="Foto">
    <button class="dicht" type="button" data-lb="dicht" aria-label="Sluiten">×</button>
    <button class="pijl vorige" type="button" data-lb="-1" aria-label="Vorige">‹</button>
    <img alt="">
    <button class="pijl volgende" type="button" data-lb="1" aria-label="Volgende">›</button>
    <div class="balk"><a class="knop" data-lb="download">Download deze foto</a></div>
  </div>
</div>
'''


# ---------------------------------------------------------------- de afgesloten pagina

SLOT = r'''<!doctype html>
<html lang="nl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow,noarchive,noimageindex">
<meta name="referrer" content="no-referrer">
<title>Fotoboek · The Hunt</title>
<style>
@font-face{font-family:'Lato';font-weight:400;font-display:swap;src:url(/assets/fonts/S6uyw4BMUTPHjx4wXg.woff2) format('woff2')}
@font-face{font-family:'Lato';font-weight:700;font-display:swap;src:url(/assets/fonts/S6u9w4BMUTPHh6UVSwiPGQ.woff2) format('woff2')}
html,body{margin:0;background:#141e29}
.slot{min-height:100vh;display:grid;place-items:center;padding:24px;font:400 17px/1.5 'Lato',system-ui,sans-serif;color:#e7edf3}
.slot form{width:100%;max-width:380px;text-align:center}
.slot img{height:72px;margin:0 auto 22px;display:block}
.slot h1{font-size:1.6rem;margin:0 0 6px;color:#fff}
.slot p{color:#a9b6c4;margin:0 0 20px}
.slot input{width:100%;box-sizing:border-box;font:inherit;font-size:1.15rem;letter-spacing:.08em;text-align:center;padding:13px;border-radius:10px;border:1px solid rgba(255,255,255,.25);background:rgba(255,255,255,.06);color:#fff}
.slot input:focus{outline:3px solid rgba(242,146,34,.5);border-color:#f29222}
.slot button{margin-top:12px;width:100%;font:inherit;font-weight:700;background:#f29222;color:#141e29;border:0;border-radius:999px;padding:13px;cursor:pointer}
.slot button[disabled]{opacity:.6;cursor:wait}
.slot .fout{color:#ffb4a8;min-height:1.5em;margin-top:12px}
</style></head>
<body>
<div class="slot" id="slot"><form id="f">
  <img src="/assets/uploads/2025/06/escape-game-the-hunt-wit-logo.png" alt="The Hunt">
  <h1>Jullie fotoboek</h1>
  <p>Vul het wachtwoord in dat je van ons hebt gekregen.</p>
  <input id="ww" type="text" autocomplete="off" autocapitalize="characters" spellcheck="false" required placeholder="Wachtwoord" aria-label="Wachtwoord">
  <button id="knop">Open het fotoboek</button>
  <div class="fout" id="fout" role="alert"></div>
</form></div>
<div id="app"></div>
<script>
(function(){
const ITER=250000,MAGIC='THB1';
const $=id=>document.getElementById(id);
function norm(s){return s.toUpperCase().replace(/[^A-Z0-9]/g,'')}
async function sleutel(ww,zout){
  const basis=await crypto.subtle.importKey('raw',new TextEncoder().encode(norm(ww)),'PBKDF2',false,['deriveKey']);
  return crypto.subtle.deriveKey({name:'PBKDF2',salt:zout,iterations:ITER,hash:'SHA-256'},basis,{name:'AES-GCM',length:256},false,['decrypt']);
}
let data=null;
async function laad(){if(!data){const r=await fetch('data.bin',{cache:'no-store'});if(!r.ok)throw new Error('niet gevonden');data=new Uint8Array(await r.arrayBuffer())}return data}
async function open(ww){
  const d=await laad();
  if(new TextDecoder().decode(d.slice(0,4))!==MAGIC)throw new Error('onbekend bestand');
  const zout=d.slice(4,20),iv=d.slice(20,32);
  const k=await sleutel(ww,zout);
  let plat;
  try{plat=new Uint8Array(await crypto.subtle.decrypt({name:'AES-GCM',iv},k,d.slice(32)))}catch(e){return false}
  const lengte=new DataView(plat.buffer).getUint32(0);
  const kop=JSON.parse(new TextDecoder().decode(plat.subarray(4,4+lengte)));
  const basis=4+lengte,blobs={},bytes={};
  for(const b of kop.bestanden){const deel=plat.subarray(basis+b.start,basis+b.start+b.lengte);bytes[b.naam]=deel;blobs[b.naam]=URL.createObjectURL(new Blob([deel],{type:b.type}))}
  toon(kop,blobs,bytes);
  try{sessionStorage.setItem('fb:'+location.pathname,ww)}catch(e){}
  return true;
}
function crc32(b){let c,t=crc32.t;if(!t){t=crc32.t=[];for(let n=0;n<256;n++){c=n;for(let k=0;k<8;k++)c=c&1?0xEDB88320^(c>>>1):c>>>1;t[n]=c>>>0}}
  c=0xFFFFFFFF;for(let i=0;i<b.length;i++)c=t[(c^b[i])&255]^(c>>>8);return(c^0xFFFFFFFF)>>>0}
function zip(bestanden){ // zonder compressie (foto's zijn al gecomprimeerd)
  const delen=[],centraal=[];let pos=0;
  for(const [naam,data] of bestanden){
    const n=new TextEncoder().encode(naam),crc=crc32(data),h=new DataView(new ArrayBuffer(30));
    h.setUint32(0,0x04034b50,true);h.setUint16(4,20,true);h.setUint16(8,0,true);h.setUint32(14,crc,true);
    h.setUint32(18,data.length,true);h.setUint32(22,data.length,true);h.setUint16(26,n.length,true);
    delen.push(new Uint8Array(h.buffer),n,data);
    const c=new DataView(new ArrayBuffer(46));
    c.setUint32(0,0x02014b50,true);c.setUint16(4,20,true);c.setUint16(6,20,true);c.setUint32(16,crc,true);
    c.setUint32(20,data.length,true);c.setUint32(24,data.length,true);c.setUint16(28,n.length,true);c.setUint32(42,pos,true);
    centraal.push(new Uint8Array(c.buffer),n);pos+=30+n.length+data.length;
  }
  const grootte=centraal.reduce((s,x)=>s+x.length,0),eind=new DataView(new ArrayBuffer(22));
  eind.setUint32(0,0x06054b50,true);eind.setUint16(8,bestanden.length,true);eind.setUint16(10,bestanden.length,true);
  eind.setUint32(12,grootte,true);eind.setUint32(16,pos,true);
  return new Blob([...delen,...centraal,new Uint8Array(eind.buffer)],{type:'application/zip'});
}
function bewaar(blob,naam){const a=document.createElement('a');a.href=typeof blob==='string'?blob:URL.createObjectURL(blob);a.download=naam;document.body.appendChild(a);a.click();a.remove()}
function toon(kop,blobs,bytes){
  $('slot').remove();
  document.title=kop.titel||document.title;
  const app=$('app');app.innerHTML=kop.html;
  app.querySelectorAll('[data-f]').forEach(el=>{const u=blobs[el.dataset.f];if(!u)return;if(el.tagName==='A')el.href=u;else el.src=u});
  const fotos=kop.bestanden.filter(b=>b.naam.startsWith('fotos/'));
  const bewaarnaam={};fotos.forEach((b,i)=>bewaarnaam[b.naam]=String(i+1).padStart(2,'0')+'-'+(b.bewaar||b.naam.slice(6)));
  const zipnaam=(kop.zip||'fotos-the-hunt')+'.zip';
  app.querySelectorAll('[data-zip]').forEach(k=>k.onclick=()=>bewaar(zip(fotos.map(b=>[bewaarnaam[b.naam],bytes[b.naam]])),zipnaam));
  const lb=app.querySelector('#lb'),img=lb.querySelector('img'),dl=lb.querySelector('[data-lb=download]');let nu=0;
  const tegels=[...app.querySelectorAll('.foto')];
  function toonFoto(i){nu=(i+tegels.length)%tegels.length;const f=tegels[nu].querySelector('img');img.src=f.src;dl.href=f.src;
    dl.download='the-hunt-'+(bewaarnaam[f.dataset.f]||'foto.jpg');lb.classList.add('open')}
  tegels.forEach((t,i)=>t.onclick=()=>toonFoto(i));
  lb.addEventListener('click',ev=>{const a=ev.target.dataset.lb;if(a==='dicht'||ev.target===lb)lb.classList.remove('open');else if(a==='1'||a==='-1')toonFoto(nu+Number(a))});
  document.addEventListener('keydown',ev=>{if(!lb.classList.contains('open'))return;if(ev.key==='Escape')lb.classList.remove('open');
    if(ev.key==='ArrowRight')toonFoto(nu+1);if(ev.key==='ArrowLeft')toonFoto(nu-1)});
  window.scrollTo(0,0);
}
$('f').addEventListener('submit',async ev=>{
  ev.preventDefault();const k=$('knop');k.disabled=true;$('fout').textContent='';k.textContent='Bezig met openen...';
  try{if(!await open($('ww').value)){$('fout').textContent='Dat wachtwoord klopt niet. Let op: hoofdletters maken niet uit, streepjes ook niet.'}}
  catch(e){$('fout').textContent='Het fotoboek kon niet geladen worden. Probeer het later opnieuw.'}
  k.disabled=false;k.textContent='Open het fotoboek';
});
try{const w=sessionStorage.getItem('fb:'+location.pathname);if(w){$('ww').value=w;open(w).catch(()=>{})}}catch(e){}
})();
</script>
</body></html>
'''


def slot():
    return SLOT


# ---------------------------------------------------------------- online zetten via GitHub

class Fout(Exception):
    pass


def _api(cfg, methode, pad, data=None):
    url = f'https://api.github.com/repos/{cfg["repo"]}/{pad}'
    req = urllib.request.Request(url, method=methode, data=json.dumps(data).encode() if data is not None else None,
                                 headers={'Authorization': f'Bearer {cfg["token"]}', 'Accept': 'application/vnd.github+json',
                                          'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'thehunt-fotoboek/1.0',
                                          'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read() or b'null')
    except urllib.error.HTTPError as fout:
        tekst = fout.read().decode('utf-8', 'replace')[:300]
        if fout.code == 404 and methode == 'GET' and pad.startswith('contents/'):
            return None
        if fout.code in (401, 403):
            raise Fout(f'GitHub weigert de toegang ({fout.code}). Controleer GITHUB_TOKEN in .env '
                       f'(nodig: Contents read and write op {cfg["repo"]}).') from None
        raise Fout(f'GitHub gaf fout {fout.code}: {tekst}') from None
    except urllib.error.URLError as fout:
        raise Fout(f'Kan GitHub niet bereiken: {fout.reason}') from None


def _blob(cfg, inhoud):
    return _api(cfg, 'POST', 'git/blobs', {'content': base64.b64encode(inhoud).decode(), 'encoding': 'base64'})['sha']


def oude_boekjes(cfg, vandaag=None):
    """Mappen in FOTOBOEK_MAP die ouder zijn dan de bewaartermijn (de map begint met de datum: jjmmdd-...)."""
    grens = (vandaag or date.today()) - timedelta(days=cfg['dagen'])
    lijst = _api(cfg, 'GET', f'contents/{cfg["map"]}?ref={cfg["branch"]}') or []
    oud = []
    for item in lijst:
        if item.get('type') != 'dir':
            continue
        try:
            datum = datetime.strptime(item['name'][:6], '%y%m%d').date()
        except ValueError:
            continue
        if datum < grens:
            oud.append(item['name'])
    return oud


def publiceer(boek_id, data_bin, log=print):
    """Zet index.html en data.bin in FOTOBOEK_MAP/<boek_id>/ met één commit en geeft de URL terug."""
    cfg = config()
    if not cfg['token']:
        raise Fout('Geen GITHUB_TOKEN in .env, dus niet online gezet.')
    if len(data_bin) > 90 * 1024 * 1024:
        raise Fout('Het fotoboek is te groot om online te zetten (meer dan 90 MB).')
    ref = _api(cfg, 'GET', f'git/ref/heads/{cfg["branch"]}')
    basis = ref['object']['sha']
    boom = _api(cfg, 'GET', f'git/commits/{basis}')['tree']['sha']
    items = [{'path': f'{cfg["map"]}/{boek_id}/index.html', 'mode': '100644', 'type': 'blob',
              'sha': _blob(cfg, slot().encode('utf-8'))},
             {'path': f'{cfg["map"]}/{boek_id}/data.bin', 'mode': '100644', 'type': 'blob', 'sha': _blob(cfg, data_bin)}]
    weg = []
    try:
        weg = oude_boekjes(cfg)
    except Fout as fout:
        log(f'Opruimen overgeslagen: {fout}')
    for naam in weg:
        for bestand in ('index.html', 'data.bin'):
            items.append({'path': f'{cfg["map"]}/{naam}/{bestand}', 'mode': '100644', 'type': 'blob', 'sha': None})
    nieuwe_boom = _api(cfg, 'POST', 'git/trees', {'base_tree': boom, 'tree': items})['sha']
    bericht = f'Fotoboek {boek_id} online' + (f', {len(weg)} oude opgeruimd' if weg else '')
    commit = _api(cfg, 'POST', 'git/commits', {'message': bericht, 'tree': nieuwe_boom, 'parents': [basis]})['sha']
    _api(cfg, 'PATCH', f'git/refs/heads/{cfg["branch"]}', {'sha': commit})
    if weg:
        log(f'{len(weg)} fotoboek(en) ouder dan {cfg["dagen"]} dagen opgeruimd.')
    return f'{cfg["url"]}/{boek_id}/'
