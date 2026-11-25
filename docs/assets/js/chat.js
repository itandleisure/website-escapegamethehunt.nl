/* Chat op de website: vraag en antwoord, zonder AI en zonder server.
   De antwoorden staan in /assets/chat.json (gemaakt door tools/chat.py uit de teksten van de site). De chat zoekt het
   antwoord dat het best bij de vraag past. Weet hij het niet, dan kan de bezoeker naam en telefoon/e-mail achterlaten.
   Elke vraag gaat (anoniem, met het gegeven antwoord en de pagina) naar de Google Sheet, tabblad "Chatvragen". */
(function () {
  'use strict';
  var me = document.currentScript;
  var DATA_URL = me && me.getAttribute('data-chat');
  var data = null, opened = Date.now();

  // Woorden met dezelfde betekenis tellen als één onderwerp
  var SYN = {
    prijs: 'kost kosten kostte prijs prijzen tarief tarieven euro geld betalen betaal bedrag offerte btw goedkoop',
    tijd: 'lang duurt duur tijd minuten minuut uur uren',
    personen: 'personen persoon mensen deelnemers groep groepen groepsgrootte aantal minimaal maximaal minimum maximum spelers teams team',
    regen: 'regen regent weer slecht nat winter koud sneeuw',
    kinderen: 'kind kinderen kids leeftijd jong jaar oud basisschool tieners',
    start: 'start starten begint beginnen startlocatie startpunt verzamelen verzamelpunt adres parkeren parkeergarage station',
    boeken: 'boeken boek reserveren reserveer boeking reservering beschikbaar beschikbaarheid plek datum vrij aanvraag aanvragen',
    contact: 'contact bellen bel telefoon telefoonnummer mail mailen email',
    steden: 'steden stad locaties locatie plaatsen plaats',
    eten: 'eten drinken borrel diner lunch restaurant drankje kroeg cafe',
    maat: 'maat aangepast thema eigen persoonlijk',
    escaperoom: 'escaperoom escape room escapes',
    hunters: 'hunters hunter jagers jager achtervolgd achtervolgen live echte',
    spelleider: 'spelleider spelleiders begeleiding begeleidt begeleider',
    winnaar: 'winnaar winnen wint',
    uitje: 'teamuitje bedrijfsuitje bedrijfsfeest personeelsuitje collegas teambuilding',
    vrijgezel: 'vrijgezellenfeest vrijgezellen vrijgezel',
    hunted: 'hunted jachtseizoen',
    app: 'app gameapp telefoon smartphone'
  };
  var STOP = ' de het een en van in op te is je jij jullie we wij ik kan kun kunnen mag moet met voor ook nog wel niet dat dit die er bij aan als om of hoe wat wie welke wanneer the hunt escape game spel spelen speel ';
  var CANON = {};
  Object.keys(SYN).forEach(function (k) { SYN[k].split(' ').forEach(function (w) { CANON[w] = k; }); });

  function norm(s) {
    return String(s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
      .replace(/hoe duur/g, 'prijs').replace(/escape room/g, 'escaperoom').replace(/[^a-z0-9 ]/g, ' ');
  }
  function woorden(s) {
    var out = {};
    norm(s).split(/\s+/).forEach(function (w) {
      if (!w || STOP.indexOf(' ' + w + ' ') >= 0) return;
      out[CANON[w] || CANON[w.replace(/(en|s)$/, '')] || CANON[w + 'en'] || w] = 1;
    });
    return out;
  }
  function stadIn(q) {
    var t = ' ' + norm(q) + ' ', hit = null;
    (data.steden || []).forEach(function (s) { if (t.indexOf(' ' + norm(s.n).trim() + ' ') >= 0) hit = s; });
    return hit;
  }

  function zoek(q) {
    var w = woorden(q), stad = stadIn(q), best = null, score = 0;
    if (stad) delete w[norm(stad.n).trim().split(' ').pop()];
    data.items.forEach(function (it) {
      if (it.stad && (!stad || it.stad !== stad.n)) return;
      if (!it._w) it._w = woorden(it.k);
      var s = 0;
      Object.keys(w).forEach(function (x) { if (it._w[x]) s += SYN[x] ? 3 : 1; });
      if (!s) return;
      if (it.stad) s += 1;
      s -= Object.keys(it._w).length / 100;   // bij gelijke stand: het meest gerichte antwoord
      if (s > score) { score = s; best = it; }
    });
    var antwoord = score >= 2.5 ? best.a : null;
    // "Kan het in Breda?": een stad waar we (nog) niet spelen
    var m = !stad && !antwoord && norm(q).trim().match(/\bin ([a-z-]{3,}(?: [a-z-]{3,})?)$/);
    if (m && !CANON[m[1]] && STOP.indexOf(' ' + m[1] + ' ') < 0) {
      return { q: 'Onbekende stad: ' + m[1], a: '<p>In ' + esc(m[1].replace(/\b\w/g, function (c) { return c.toUpperCase(); })) + ' hebben we nog geen vaste locatie, maar we organiseren The Hunt daar graag. ' +
        'Samen kijken we wat wel en niet kan, en daar zitten geen extra kosten aan.</p>', terug: true };
    }
    // "Kan het in Zwolle?" zonder ander onderwerp: bevestigen met link naar de stad
    if (stad && (!antwoord || (best && !best.stad && Object.keys(w).every(function (x) { return x === 'steden'; })))) {
      return { q: 'Stad: ' + stad.n, a: '<p>Ja, The Hunt speel je in ' + esc(stad.n) + (stad.s ? ', we starten bij ' + esc(stad.s) : '') +
        '. Alles over het spel daar lees je op de <a href="' + stad.u + '">pagina over ' + esc(stad.n) + '</a>.</p>' };
    }
    if (!antwoord) return null;
    if (stad && !best.stad) antwoord += '<p><a href="' + stad.u + '">Meer over The Hunt in ' + esc(stad.n) + '</a></p>';
    return { q: best.q, a: antwoord };
  }

  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }

  function stuur(velden) {
    if (!data || !data.google || !window.fetch) return Promise.resolve(false);
    var body = new URLSearchParams(velden);
    body.append('pagina', location.pathname);
    body.append('duur', String(Date.now() - opened));
    return fetch(data.google, { method: 'POST', body: body }).then(function (r) { return r.json(); })
      .then(function (r) { return !!r.ok; }).catch(function () { return false; });
  }

  // ---------- venster ----------
  var knop = document.createElement('button');
  knop.type = 'button'; knop.className = 'chat-knop'; knop.setAttribute('aria-expanded', 'false'); knop.setAttribute('aria-controls', 'chat');
  knop.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z"/></svg><span>Vragen?</span>';
  var win = document.createElement('section');
  win.className = 'chat'; win.id = 'chat'; win.hidden = true; win.setAttribute('aria-label', 'Chat met vragen en antwoorden');
  win.innerHTML = '<header class="chat-kop"><b>Vraag het ons</b><span>Antwoord meteen, uit onze veelgestelde vragen</span>' +
    '<button type="button" class="chat-sluit" aria-label="Chat sluiten">&times;</button></header>' +
    '<div class="chat-log" aria-live="polite"></div>' +
    '<form class="chat-in"><label class="sr-only" for="chat-vraag">Je vraag</label><input id="chat-vraag" autocomplete="off" maxlength="300" placeholder="Typ je vraag…">' +
    '<button type="submit" aria-label="Versturen"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg></button></form>';
  document.body.appendChild(win); document.body.appendChild(knop);
  var logEl = win.querySelector('.chat-log'), form = win.querySelector('.chat-in'), input = win.querySelector('input');

  function bericht(html, wie) {
    var d = document.createElement('div');
    d.className = 'chat-msg ' + (wie || 'bot');
    d.innerHTML = html;
    logEl.appendChild(d);
    logEl.scrollTop = logEl.scrollHeight;
    return d;
  }
  function chips(lijst) {
    var d = document.createElement('div'); d.className = 'chat-chips';
    lijst.forEach(function (t) {
      var b = document.createElement('button'); b.type = 'button'; b.textContent = t;
      b.addEventListener('click', function () { vraag(t); });
      d.appendChild(b);
    });
    logEl.appendChild(d); logEl.scrollTop = logEl.scrollHeight;
  }
  function terugbel(vraagTekst, alleenFormulier) {
    var d = bericht((alleenFormulier ? '<p>' : '<p>Daar heb ik nog geen antwoord op. ') + 'Laat je naam en telefoonnummer of e-mail achter, dan nemen we contact met je op. ' +
      'Of bel ons: <a href="tel:' + data.tel + '">' + esc(data.tel_tekst) + '</a>.</p>' +
      '<form class="chat-contact"><input name="naam" placeholder="Naam" required maxlength="100" autocomplete="name">' +
      '<input name="contact" placeholder="Telefoon of e-mail" required maxlength="150" autocomplete="email">' +
      '<button type="submit" class="btn btn-signal">Bel of mail mij</button></form>');
    var f = d.querySelector('form');
    f.addEventListener('submit', function (e) {
      e.preventDefault();
      var btn = f.querySelector('button'); btn.disabled = true;
      stuur({ form: 'chatcontact', naam: f.naam.value, contact: f.contact.value, vraag: vraagTekst }).then(function (ok) {
        f.outerHTML = ok ? '<p><b>Dank je!</b> We nemen zo snel mogelijk contact met je op.</p>'
          : '<p>Versturen lukte niet. Bel ons op <a href="tel:' + data.tel + '">' + esc(data.tel_tekst) + '</a> of mail <a href="mailto:' + data.mail + '">' + esc(data.mail) + '</a>.</p>';
      });
      if (window.gtag) gtag('event', 'chat_contact', { pagina: location.pathname });
    });
  }
  function vraag(t) {
    t = String(t || '').trim();
    if (!t) return;
    bericht('<p>' + esc(t) + '</p>', 'jij');
    var r = zoek(t);
    if (r) bericht(r.a);
    if (!r || r.terug) terugbel(t, !!r);
    stuur({ form: 'chatvraag', vraag: t, antwoord: r ? r.q : 'geen antwoord' });
    if (window.gtag) gtag('event', 'chat_vraag', { beantwoord: r ? 'ja' : 'nee', pagina: location.pathname });
  }

  function laad() {
    if (data) return Promise.resolve();
    return fetch(DATA_URL || '/assets/chat.json').then(function (r) { return r.json(); }).then(function (d) {
      data = d;
      bericht('<p>Hoi! Waar kan ik je mee helpen? Kies een vraag of typ je eigen vraag.</p>');
      chips(['Wat kost het?', 'In welke steden?', 'Hoe lang duurt het?', 'En als het regent?', 'Hoe boek ik?']);
    });
  }
  function open(aan) {
    win.hidden = !aan; knop.setAttribute('aria-expanded', String(aan)); document.body.classList.toggle('chat-open', aan);
    if (aan) laad().then(function () { input.focus(); }).catch(function () { bericht('<p>De chat kon niet laden. Bel ons op 085 004 7719.</p>'); });
  }
  knop.addEventListener('click', function () { open(win.hidden); });
  win.querySelector('.chat-sluit').addEventListener('click', function () { open(false); knop.focus(); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !win.hidden) { open(false); knop.focus(); } });
  logEl.addEventListener('click', function (e) { var a = e.target.closest('a[href^="#"]'); if (a) open(false); });
  form.addEventListener('submit', function (e) { e.preventDefault(); var t = input.value; input.value = ''; laad().then(function () { vraag(t); }); });
})();
