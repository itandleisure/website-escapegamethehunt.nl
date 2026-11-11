/* Boekingsaanvragen Escape Game The Hunt → Google Sheet + e-mail
   ---------------------------------------------------------------
   Dit script hoort bij een Google Sheet (Extensies → Apps Script).
   - Elke aanvraag via het boekingsformulier van escapegamethehunt.nl komt als nieuwe regel
     in het tabblad "Aanvragen".
   - Er gaat meteen een e-mail naar ONTVANGER (antwoorden gaat rechtstreeks naar de invuller).
   - De chat op de website stuurt elke vraag naar het tabblad "Chatvragen" (elke ochtend een overzicht per mail)
     (meteen een mail per vraag, en elke ochtend een overzicht) en een terugbelverzoek naar "Chatcontact" (meteen een mail).
   - Regels ouder dan de bewaartermijn per tabblad worden elke nacht automatisch verwijderd (privacy).
   - Elke ochtend wordt het tabblad "Statistieken" opnieuw opgebouwd (aanvragen per maand, stad, bron,
     soort Hunt en pagina, chatcijfers en Google-zoekcijfers uit Search Console), en elke maandagochtend gaat er een weekrapport naar RAPPORT_ONTVANGER.
     Handmatig bijwerken of een rapport sturen: kies "statistieken" of "weekrapport" en klik op Uitvoeren.

   Eenmalig: kies bovenin de functie "installeer" en klik op Uitvoeren (geeft toestemming
   en zet de nachtelijke opruimtaak aan). Daarna: Implementeren → Nieuwe implementatie → Web-app,
   "Uitvoeren als: ik", "Toegang: iedereen". Zet de /exec-URL in "google_form_url" in src/data/site.json
   en draai python tools/build.py.

   Search Console-cijfers: zet in Projectinstellingen het vinkje "appsscript.json weergeven in editor" aan en
   vervang de inhoud van appsscript.json door het meegeleverde bestand (dat voegt het leesrecht voor Search Console toe).
   Voer daarna "installeer" opnieuw uit en geef toestemming. Het Google-account van het script moet eigenaar of
   gebruiker zijn van escapegamethehunt.nl in Search Console.

   Script gewijzigd? Implementeren → Implementaties beheren → bewerken → Nieuwe versie
   (dan blijft de URL gelijk). */

var ONTVANGER = 'info@escapegamethehunt.nl';
var AFZENDER_NAAM = 'Website Escape Game The Hunt';
var RAPPORT_ONTVANGER = ONTVANGER;   // ander adres of meerdere adressen kan ook: 'a@x.nl,b@y.nl'

// Per formuliertype: tabblad, kolommen, bewaartermijn en onderwerp van de mail
var FORMULIEREN = {
  boeking: {
    tabblad: 'Aanvragen', bewaarMaanden: 12, onderwerp: 'Aanvraag The Hunt',
    velden: [['naam', 'Naam'], ['type', 'Zakelijk / particulier'], ['bedrijf', 'Bedrijf'], ['email', 'E-mail'],
      ['telefoon', 'Telefoon'], ['stad', 'Stad'], ['datum', 'Gewenste datum'], ['starttijd', 'Starttijd'],
      ['personen', 'Aantal personen'], ['soort', 'Soort Hunt'], ['bericht', 'Overige informatie'],
      ['gevonden', 'Hoe gevonden']],
    verplicht: ['naam', 'email', 'telefoon', 'stad', 'datum', 'personen']
  },
  // Sollicitaties via het formulier op de vacaturepagina's (werken bij)
  sollicitatie: {
    tabblad: 'Sollicitaties', bewaarMaanden: 6, onderwerp: 'Sollicitatie The Hunt',
    velden: [['naam', 'Naam'], ['leeftijd', 'Leeftijd'], ['woonplaats', 'Woonplaats'], ['email', 'E-mail'],
      ['telefoon', 'Telefoon'], ['functie', 'Functie'], ['stad', 'Voorkeursstad'], ['bericht', 'Motivatie']],
    verplicht: ['naam', 'email', 'telefoon', 'woonplaats', 'functie']
  },
  // Reviews via escapegamethehunt.nl/review/ (link in het fotoboek)
  review: {
    tabblad: 'Reviews', bewaarMaanden: 36, onderwerp: 'Review The Hunt',
    velden: [['cijfer', 'Sterren (1-5)'], ['review', 'Review'], ['naam', 'Naam'], ['groep', 'Bedrijf of groep'],
      ['stad', 'Gespeeld in'], ['email', 'E-mail'], ['publiceren', 'Mag op de website'],
      ['datum', 'Datum gespeeld'], ['spelleider', 'Spelleider(s)'], ['tips', 'Tips (alleen intern)']],
    verplicht: ['cijfer', 'review', 'naam', 'datum']
  },
  // Elke vraag die in de chat op de website wordt gesteld (anoniem): meteen een mail, en elke ochtend een overzicht.
  chatvraag: {
    tabblad: 'Chatvragen', bewaarMaanden: 12, onderwerp: 'Chatvraag',
    velden: [['vraag', 'Vraag'], ['antwoord', 'Gegeven antwoord']],
    verplicht: ['vraag']
  },
  // Bezoeker laat in de chat naam en telefoon/e-mail achter: meteen een mail
  chatcontact: {
    tabblad: 'Chatcontact', bewaarMaanden: 12, onderwerp: 'Terugbelverzoek via de chat',
    velden: [['naam', 'Naam'], ['contact', 'Telefoon of e-mail'], ['vraag', 'Vraag']],
    verplicht: ['naam', 'contact']
  }
};

// Ontvangt een formulier van de website
function doPost(e) {
  var p = (e && e.parameter) || {};
  var lijsten = (e && e.parameters) || {};   // meerdere waarden, bijv. aangevinkte keuzes

  // Verborgen veld ingevuld of binnen 3 seconden na openen verstuurd = spambot: doen alsof het gelukt is.
  // "duur" is de invultijd in milliseconden, gemeten in de browser (onafhankelijk van de klok).
  if (p.website || p._honey || (p.duur !== undefined && p.duur !== '' && parseInt(p.duur, 10) < 3000)) return antwoord({ ok: true });

  var type = schoon(p.form, 40);
  var cfg = FORMULIEREN[type];
  if (!cfg) return antwoord({ ok: false, fout: 'onbekend formulier' });

  var g = {};
  cfg.velden.forEach(function (v) {
    var sleutel = v[0];
    var waarden = lijsten[sleutel] || lijsten[sleutel + '[]'];
    g[sleutel] = waarden && waarden.length > 1 ? schoon(waarden.join(', '), 1000) : schoon(p[sleutel] || p[sleutel + '[]'], 5000);
  });
  g.pagina = schoon(p.page || p.pagina, 300);

  // Controles
  var fouten = cfg.verplicht.filter(function (k) {
    return k === 'email' ? !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(g.email) : !g[k];
  });
  if (fouten.length) return antwoord({ ok: false, fout: 'velden', velden: fouten });

  // 1. Opslaan in de spreadsheet (slot voorkomt dat twee inzendingen tegelijk botsen)
  var slot = LockService.getScriptLock();
  slot.waitLock(10000);
  try {
    blad(cfg).appendRow([new Date(), g.pagina].concat(cfg.velden.map(function (v) {
      return veiligVoorSheet(g[v[0]]);
    })));
  } finally {
    slot.releaseLock();
  }

  // 2. E-mail sturen. Lukt dat niet, dan staat de inzending in ieder geval al in de spreadsheet.
  if (cfg.geenMail) return antwoord({ ok: true });
  try {
    var extra = type === 'boeking' ? ': ' + (g.stad || '') + ', ' + g.personen + ' pers. (' + (g.bedrijf || g.naam) + ')'
      : type === 'chatvraag' ? (g.antwoord === 'geen antwoord' ? ' zonder antwoord: ' : ': ') + g.vraag.slice(0, 80)
      : type === 'review' ? ': ' + g.cijfer + ' sterren van ' + g.naam + (g.groep ? ' (' + g.groep + ')' : '')
      : type === 'sollicitatie' ? ': ' + g.naam + ' (' + g.functie + ', ' + g.woonplaats + ')'
      : ': ' + g.naam;
    stuurMail(cfg, g, cfg.onderwerp + extra);
  } catch (fout) {
    console.error('Mail versturen mislukt: ' + fout);
  }

  return antwoord({ ok: true });
}

// Openen van de web-app-link in de browser: laat zien dat het script werkt
function doGet() {
  return ContentService.createTextOutput('Formulier-ontvanger Escape Game The Hunt is actief.');
}

// Eenmalig uitvoeren: maakt de tabbladen aan en zet de nachtelijke opruimtaak en het ochtendoverzicht van de chat aan.
// Opnieuw uitvoeren kan geen kwaad: bestaande taken worden niet dubbel aangemaakt.
function installeer() {
  Object.keys(FORMULIEREN).forEach(function (k) { blad(FORMULIEREN[k]); });
  var taken = ScriptApp.getProjectTriggers().map(function (t) { return t.getHandlerFunction(); });
  if (taken.indexOf('opruimen') < 0) {
    ScriptApp.newTrigger('opruimen').timeBased().everyDays(1).atHour(3).create();
  }
  if (taken.indexOf('chatoverzicht') < 0) {
    ScriptApp.newTrigger('chatoverzicht').timeBased().everyDays(1).atHour(8).create();
  }
  if (taken.indexOf('statistieken') < 0) {
    ScriptApp.newTrigger('statistieken').timeBased().everyDays(1).atHour(6).create();
  }
  if (taken.indexOf('weekrapport') < 0) {
    ScriptApp.newTrigger('weekrapport').timeBased().onWeekDay(ScriptApp.WeekDay.MONDAY).atHour(8).create();
  }
  opruimen();
  statistieken();
}

// Elke ochtend: mail met alle chatvragen van gisteren. Geen vragen gesteld, dan geen mail.
function chatoverzicht() {
  var cfg = FORMULIEREN.chatvraag;
  var sheet = blad(cfg);
  var laatste = sheet.getLastRow();
  if (laatste < 2) return;
  var tot = new Date(); tot.setHours(0, 0, 0, 0);
  var van = new Date(tot); van.setDate(van.getDate() - 1);
  var rijen = sheet.getRange(2, 1, laatste - 1, 4).getValues().filter(function (r) {
    return r[0] instanceof Date && r[0] >= van && r[0] < tot;
  });
  if (!rijen.length) return;
  var zonder = rijen.filter(function (r) { return r[3] === 'geen antwoord'; }).length;
  var tz = Session.getScriptTimeZone();
  var html = '<p style="font-family:Arial,sans-serif;font-size:14px">' + rijen.length + ' vragen in de chat, waarvan ' + zonder +
    ' zonder antwoord. Vragen zonder antwoord zijn ideeën voor de veelgestelde vragen.</p>' +
    '<table cellpadding="6" style="border-collapse:collapse;font-family:Arial,sans-serif;font-size:14px">' +
    '<tr style="background:#F1EDE5"><th align="left">Tijd</th><th align="left">Vraag</th><th align="left">Antwoord</th><th align="left">Pagina</th></tr>' +
    rijen.map(function (r) {
      var geen = r[3] === 'geen antwoord';
      return '<tr><td valign="top">' + Utilities.formatDate(r[0], tz, 'HH:mm') + '</td><td valign="top">' + html_(String(r[2]).replace(/^'/, '')) +
        '</td><td valign="top"' + (geen ? ' style="color:#C0392B"' : '') + '>' + html_(r[3]) + '</td><td valign="top">' + html_(r[1]) + '</td></tr>';
    }).join('') + '</table>' +
    '<p style="font-family:Arial,sans-serif;font-size:12px;color:#777">Alle vragen staan in de Google Sheet, tabblad "' + cfg.tabblad + '".</p>';
  MailApp.sendEmail({
    to: ONTVANGER,
    name: AFZENDER_NAAM,
    subject: 'Chatvragen van ' + Utilities.formatDate(van, tz, 'd-M-yyyy') + ': ' + rijen.length + ' (' + zonder + ' zonder antwoord)',
    htmlBody: html
  });
}

/* ===== Statistieken en weekrapport ==========================================
   statistieken(): bouwt het tabblad "Statistieken" opnieuw op (elke ochtend om 6 uur).
   weekrapport():  mailt elke maandag de cijfers van vorige week, vergeleken met de week ervoor.
   Beide gebruiken alleen wat al in de tabbladen Aanvragen, Chatvragen en Chatcontact staat. */

var STATS_TABBLAD = 'Statistieken';

function statistieken() {
  var s = bereken_();
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(STATS_TABBLAD) || ss.insertSheet(STATS_TABBLAD, 0);
  sheet.clear();

  var tz = Session.getScriptTimeZone();
  var regel = 1;
  sheet.getRange(regel, 1).setValue('Statistieken Escape Game The Hunt').setFontWeight('bold').setFontSize(14);
  sheet.getRange(regel + 1, 1).setValue('Bijgewerkt op ' + Utilities.formatDate(new Date(), tz, 'd-M-yyyy HH:mm') +
    '. Wordt elke ochtend automatisch vernieuwd; niet zelf in dit tabblad typen.').setFontColor('#777777');
  regel += 3;

  s.blokken.forEach(function (b) {
    sheet.getRange(regel, 1).setValue(b.titel).setFontWeight('bold').setFontSize(12);
    if (b.uitleg) sheet.getRange(regel, 2).setValue(b.uitleg).setFontColor('#777777');
    regel++;
    var rijen = [b.koppen].concat(b.rijen.length ? b.rijen : [b.koppen.map(function (k, i) { return i ? '' : 'Nog geen gegevens'; })]);
    sheet.getRange(regel, 1, rijen.length, b.koppen.length).setValues(rijen);
    sheet.getRange(regel, 1, 1, b.koppen.length).setFontWeight('bold').setBackground('#F1EDE5');
    regel += rijen.length + 1;
  });

  sheet.setColumnWidth(1, 320);
  for (var k = 2; k <= 8; k++) sheet.setColumnWidth(k, 130);
  sheet.setFrozenRows(2);
  return s;
}

function weekrapport() {
  var s = statistieken();
  var tz = Session.getScriptTimeZone();
  var vw = s.periode['Vorige week'], ww = s.periode['Week daarvoor'];
  var deze = filter_(s.aanvragen, vw), vorige = filter_(s.aanvragen, ww);
  var chat = filter_(s.chat, vw), chatVorige = filter_(s.chat, ww);
  var contact = filter_(s.contact, vw), contactVorige = filter_(s.contact, ww);
  var pers = som_(deze), persVorige = som_(vorige);

  var stijl = 'font-family:Arial,sans-serif;font-size:14px';
  var kop = function (t) { return '<h3 style="font-family:Arial,sans-serif;font-size:15px;margin:22px 0 6px">' + t + '</h3>'; };
  var tabel = function (koppen, rijen) {
    return '<table cellpadding="6" style="border-collapse:collapse;' + stijl + '"><tr style="background:#F1EDE5">' +
      koppen.map(function (k, i) { return '<th align="' + (i ? 'right' : 'left') + '">' + html_(k) + '</th>'; }).join('') + '</tr>' +
      rijen.map(function (r) {
        return '<tr>' + r.map(function (c, i) {
          var inhoud = c && c.html ? c.html : html_(c === 0 ? '0' : c);   // {html: ...} wordt niet ge-escaped
          return '<td valign="top" align="' + (i && (typeof c === 'number' || c.html) ? 'right' : 'left') + '">' + inhoud + '</td>';
        }).join('') + '</tr>';
      }).join('') + '</table>';
  };
  var verschil = function (a, b) {
    if (a === b) return { html: '<span style="color:#777">gelijk</span>' };
    return { html: '<span style="color:' + (a > b ? '#1E8449' : '#C0392B') + '">' + (a > b ? '+' : '') + Math.round((a - b) * 10) / 10 + '</span>' };
  };

  // Google-cijfers (Search Console); lukt dat niet, dan gaat het rapport zonder
  var googleRijen = [], topWoorden = [], googleFout = '';
  try {
    var sc = sc_(), g = sc.totaal(vw), gv = sc.totaal(ww);
    var pos = function (x) { return x ? Math.round(x * 10) / 10 : ''; };
    googleRijen = [
      ['Klikken vanuit Google', g.klikken, gv.klikken, verschil(g.klikken, gv.klikken)],
      ['Vertoningen in Google', g.vertoningen, gv.vertoningen, verschil(g.vertoningen, gv.vertoningen)],
      // Bij de positie is lager beter, dus het verschil omgedraaid kleuren
      ['Gemiddelde positie in Google', pos(g.positie), pos(gv.positie), g.positie && gv.positie ?
        verschil(Math.round(-g.positie * 10) / 10, Math.round(-gv.positie * 10) / 10) : '']
    ];
    topWoorden = sc.top(vw, 'query', 10);
  } catch (fout) {
    googleFout = String(fout.message || fout);
  }

  var html = '<div style="' + stijl + '">' +
    '<p>Cijfers van ' + Utilities.formatDate(vw[0], tz, 'd-M') + ' t/m ' + Utilities.formatDate(new Date(vw[1].getTime() - 1), tz, 'd-M-yyyy') +
    ', vergeleken met de week ervoor.</p>' +
    tabel(['', 'Vorige week', 'Week ervoor', 'Verschil'], [
      ['Aanvragen', deze.length, vorige.length, verschil(deze.length, vorige.length)],
      ['Personen aangevraagd', pers, persVorige, verschil(pers, persVorige)],
      ['Chatvragen', chat.length, chatVorige.length, verschil(chat.length, chatVorige.length)],
      ['Chatvragen zonder antwoord', zonder_(chat), zonder_(chatVorige), verschil(zonder_(chat), zonder_(chatVorige))],
      ['Terugbelverzoeken via de chat', contact.length, contactVorige.length, verschil(contact.length, contactVorige.length)]
    ].concat(googleRijen));

  if (googleFout) html += '<p style="color:#C0392B">Google-cijfers konden niet worden opgehaald: ' + html_(googleFout) + '</p>';
  else html += '<p style="font-size:12px;color:#777">Google-cijfers komen uit Search Console; zondag is daar vaak nog niet compleet.</p>';

  if (deze.length) {
    html += kop('Aanvragen van vorige week') + tabel(['Binnengekomen', 'Stad', 'Gewenste datum', 'Personen', 'Zakelijk/particulier', 'Hoe gevonden'],
      deze.map(function (r) {
        return [Utilities.formatDate(r.datum, tz, 'EEE d-M HH:mm'), r.stad || '', r['Gewenste datum'] instanceof Date ? Utilities.formatDate(r['Gewenste datum'], tz, 'd-M-yyyy') : r['Gewenste datum'] || '', r.personen || '',
          r['Zakelijk / particulier'] || '', r['Hoe gevonden'] || ''];
      }));
    html += kop('Per stad') + tabel(['Stad', 'Aanvragen', 'Personen'], perGroep_(deze, 'stad'));
    html += kop('Hoe gevonden') + tabel(['Bron', 'Aanvragen', 'Personen'], perGroep_(deze, 'Hoe gevonden', true));
  } else {
    html += '<p>Vorige week kwamen er geen aanvragen binnen.</p>';
  }

  if (topWoorden.length) html += kop('Top zoekwoorden in Google vorige week') + tabel(['Zoekwoord', 'Klikken', 'Vertoningen', 'CTR', 'Positie'], topWoorden);

  var open = topVragen_(chat.filter(function (r) { return r['Gegeven antwoord'] === 'geen antwoord'; }), 10);
  if (open.length) html += kop('Chatvragen zonder antwoord') + '<p style="color:#777">Ideeën voor de veelgestelde vragen of de chat.</p>' +
    tabel(['Vraag', 'Keer gesteld'], open);

  var ss = SpreadsheetApp.getActiveSpreadsheet();
  html += '<p style="font-size:12px;color:#777;margin-top:24px">Alle cijfers per maand, stad, bron en pagina staan in de Google Sheet, ' +
    '<a href="' + ss.getUrl() + '#gid=' + ss.getSheetByName(STATS_TABBLAD).getSheetId() + '">tabblad "' + STATS_TABBLAD + '"</a>.</p></div>';

  MailApp.sendEmail({
    to: RAPPORT_ONTVANGER,
    name: AFZENDER_NAAM,
    subject: 'Weekrapport The Hunt ' + Utilities.formatDate(vw[0], tz, 'd-M') + ': ' + deze.length + ' aanvragen, ' + pers + ' personen, ' + chat.length + ' chatvragen',
    htmlBody: html
  });
}

// Rekent alle cijfers uit en geeft ze terug als blokken voor het tabblad, plus de ruwe regels voor het weekrapport
function bereken_() {
  var tz = Session.getScriptTimeZone();
  var aanvragen = regels_(FORMULIEREN.boeking), chat = regels_(FORMULIEREN.chatvraag), contact = regels_(FORMULIEREN.chatcontact);
  aanvragen.forEach(function (r) {
    r.personen = getal_(r['Aantal personen']);
    r.stad = netjes_(r.Stad);
    r.zakelijk = /zakelijk/i.test(r['Zakelijk / particulier'] || '');
  });

  var vandaag = new Date(); vandaag.setHours(0, 0, 0, 0);
  var morgen = dagen_(vandaag, 1);
  var maandag = dagen_(vandaag, -((vandaag.getDay() + 6) % 7));
  var periodes = [
    ['Deze week', maandag, morgen],
    ['Vorige week', dagen_(maandag, -7), maandag],
    ['Week daarvoor', dagen_(maandag, -14), dagen_(maandag, -7)],
    ['Deze maand', new Date(vandaag.getFullYear(), vandaag.getMonth(), 1), morgen],
    ['Vorige maand', new Date(vandaag.getFullYear(), vandaag.getMonth() - 1, 1), new Date(vandaag.getFullYear(), vandaag.getMonth(), 1)],
    ['Laatste 12 maanden', new Date(vandaag.getFullYear() - 1, vandaag.getMonth(), vandaag.getDate()), morgen]
  ];
  var periode = {};
  periodes.forEach(function (p) { periode[p[0]] = [p[1], p[2]]; });
  var getoond = periodes.filter(function (p) { return p[0] !== 'Week daarvoor'; });

  var cijfer = function (naam, f) {
    return [naam].concat(getoond.map(function (p) { return f([p[1], p[2]]); }));
  };
  var overzicht = [
    cijfer('Aanvragen', function (p) { return filter_(aanvragen, p).length; }),
    cijfer('  waarvan zakelijk', function (p) { return filter_(aanvragen, p).filter(function (r) { return r.zakelijk; }).length; }),
    cijfer('  waarvan particulier', function (p) { return filter_(aanvragen, p).filter(function (r) { return !r.zakelijk; }).length; }),
    cijfer('Personen aangevraagd', function (p) { return som_(filter_(aanvragen, p)); }),
    cijfer('Gemiddelde groepsgrootte', function (p) {
      var r = filter_(aanvragen, p).filter(function (x) { return x.personen; });
      return r.length ? Math.round(som_(r) / r.length) : '';
    }),
    cijfer('Chatvragen', function (p) { return filter_(chat, p).length; }),
    cijfer('  waarvan zonder antwoord', function (p) { return zonder_(filter_(chat, p)); }),
    cijfer('Terugbelverzoeken via de chat', function (p) { return filter_(contact, p).length; })
  ];

  var maanden = [];
  for (var i = 0; i < 12; i++) {
    var van = new Date(vandaag.getFullYear(), vandaag.getMonth() - i, 1), tot = new Date(vandaag.getFullYear(), vandaag.getMonth() - i + 1, 1);
    var a = filter_(aanvragen, [van, tot]), c = filter_(chat, [van, tot]);
    maanden.push([Utilities.formatDate(van, tz, 'MMMM yyyy'), a.length, a.filter(function (r) { return r.zakelijk; }).length,
      a.filter(function (r) { return !r.zakelijk; }).length, som_(a), c.length, zonder_(c), filter_(contact, [van, tot]).length]);
  }

  var jaar = periode['Laatste 12 maanden'], dertig = [dagen_(vandaag, -30), morgen];
  var jaarAanvragen = filter_(aanvragen, jaar);
  var groep = function (kolom, splits) {
    var recent = {};
    perGroep_(filter_(aanvragen, dertig), kolom, splits).forEach(function (r) { recent[r[0]] = r[1]; });
    return perGroep_(jaarAanvragen, kolom, splits).map(function (r) { return [r[0], recent[r[0]] || 0, r[1], r[2]]; });
  };
  var groepKoppen = function (naam) { return [naam, 'Laatste 30 dagen', 'Laatste 12 maanden', 'Personen (12 mnd)']; };

  aanvragen.forEach(function (r) { r.paginaKort = String(r.Pagina || '').replace(/^https?:\/\/[^\/]+/, '').replace(/[?#].*$/, '') || '(onbekend)'; });

  var blokken = [
    { titel: 'Overzicht', koppen: [''].concat(getoond.map(function (p) { return p[0]; })), rijen: overzicht },
    { titel: 'Per maand', koppen: ['Maand', 'Aanvragen', 'Zakelijk', 'Particulier', 'Personen', 'Chatvragen', 'Zonder antwoord', 'Terugbelverzoeken'], rijen: maanden },
    { titel: 'Aanvragen per stad', koppen: groepKoppen('Stad'), rijen: groep('stad') },
    { titel: 'Hoe gevonden', uitleg: 'Meerdere keuzes per aanvraag mogelijk', koppen: groepKoppen('Bron'), rijen: groep('Hoe gevonden', true) },
    { titel: 'Soort Hunt', koppen: groepKoppen('Soort'), rijen: groep('Soort Hunt') },
    { titel: 'Pagina waarop het formulier is ingevuld', koppen: groepKoppen('Pagina'), rijen: groep('paginaKort').slice(0, 25) },
    { titel: 'Chatvragen zonder antwoord (laatste 30 dagen)', uitleg: 'Ideeën voor de veelgestelde vragen of de chat', koppen: ['Vraag', 'Keer gesteld'],
      rijen: topVragen_(filter_(chat, dertig).filter(function (r) { return r['Gegeven antwoord'] === 'geen antwoord'; }), 25) }
  ];

  Array.prototype.splice.apply(blokken, [1, 0].concat(scBlokken_(getoond, dertig, aanvragen)));

  return { blokken: blokken, periode: periode, aanvragen: aanvragen, chat: chat, contact: contact };
}

// Leest een tabblad als lijst van objecten op kolomnaam, zodat de kolomvolgorde niet uitmaakt
function regels_(cfg) {
  var sheet = blad(cfg);
  var laatste = sheet.getLastRow();
  if (laatste < 2) return [];
  var waarden = sheet.getRange(1, 1, laatste, sheet.getLastColumn()).getValues();
  var koppen = waarden.shift();
  return waarden.filter(function (r) { return r[0] instanceof Date; }).map(function (r) {
    var o = {};
    koppen.forEach(function (k, i) { o[k] = r[i] instanceof Date ? r[i] : String(r[i] === null ? '' : r[i]).replace(/^'/, '').trim(); });
    o.datum = r[0];
    return o;
  });
}

// Telt aanvragen en personen per waarde van een kolom, meeste aanvragen bovenaan
function perGroep_(rijen, kolom, splits) {
  var t = {};
  rijen.forEach(function (r) {
    var w = String(r[kolom] instanceof Date ? Utilities.formatDate(r[kolom], Session.getScriptTimeZone(), 'd-M-yyyy') : r[kolom] || '');
    (splits ? w.split(/\s*,\s*/) : [w]).forEach(function (x) {
      x = kolom === 'paginaKort' ? x : netjes_(x);
      x = x || '(niet ingevuld)';
      var g = t[x] || (t[x] = [x, 0, 0]);
      g[1]++;
      g[2] += r.personen || 0;
    });
  });
  return Object.keys(t).map(function (k) { return t[k]; }).sort(function (a, b) { return b[1] - a[1] || b[2] - a[2] || (a[0] < b[0] ? -1 : 1); });
}

// Dezelfde vraag (hoofdletters en leestekens genegeerd) één keer tonen, met hoe vaak hij gesteld is
function topVragen_(rijen, max) {
  var t = {};
  rijen.forEach(function (r) {
    var v = String(r.Vraag || '').trim();
    if (!v) return;
    var sleutel = v.toLowerCase().replace(/[^a-z0-9à-ÿ ]/g, '').replace(/\s+/g, ' ').trim();
    var g = t[sleutel] || (t[sleutel] = [v.slice(0, 200), 0]);
    g[1]++;
  });
  return Object.keys(t).map(function (k) { return t[k]; }).sort(function (a, b) { return b[1] - a[1]; }).slice(0, max);
}

function filter_(rijen, p) {
  return rijen.filter(function (r) { return r.datum >= p[0] && r.datum < p[1]; });
}
function som_(rijen) {
  return rijen.reduce(function (t, r) { return t + (r.personen || 0); }, 0);
}
function zonder_(rijen) {
  return rijen.filter(function (r) { return r['Gegeven antwoord'] === 'geen antwoord'; }).length;
}
function getal_(tekst) {
  var m = String(tekst || '').match(/\d+/);
  return m ? Number(m[0]) : 0;
}
function netjes_(tekst) {
  tekst = String(tekst || '').trim().replace(/\s+/g, ' ');
  return tekst.charAt(0).toUpperCase() + tekst.slice(1);
}
function dagen_(datum, n) {
  var d = new Date(datum);
  d.setDate(d.getDate() + n);
  return d;
}

/* ===== Google Search Console =================================================
   Haalt klikken, vertoningen, CTR en gemiddelde positie in Google op voor escapegamethehunt.nl.
   Werkt omdat het script draait als jij, en jij eigenaar bent van de site in Search Console.
   Nodig: het bestand appsscript.json met de rechten hieronder (zie de uitleg bij de bestanden).
   De laatste 2 à 3 dagen zijn in Search Console vaak nog niet compleet. */

var SEARCH_CONSOLE_DOMEIN = 'escapegamethehunt.nl';   // de property wordt hiermee automatisch gevonden

function sc_() {
  if (sc_.cache) return sc_.cache;
  var token = ScriptApp.getOAuthToken();
  var haal = function (url, body) {
    var r = UrlFetchApp.fetch(url, {
      method: body ? 'post' : 'get', contentType: 'application/json', payload: body ? JSON.stringify(body) : undefined,
      headers: { Authorization: 'Bearer ' + token }, muteHttpExceptions: true
    });
    var data = JSON.parse(r.getContentText() || '{}');
    if (r.getResponseCode() >= 300) throw new Error('Search Console: ' + ((data.error && data.error.message) || r.getResponseCode()));
    return data;
  };
  // Domein-property (sc-domain:) heeft voorkeur boven een URL-property
  var sites = (haal('https://www.googleapis.com/webmasters/v3/sites').siteEntry || []).map(function (s) { return s.siteUrl; })
    .filter(function (u) { return u.replace(/^sc-domain:|^https?:\/\/(www\.)?|\/$/g, '') === SEARCH_CONSOLE_DOMEIN; })
    .sort(function (a, b) { return (/^sc-domain:/.test(b) ? 1 : 0) - (/^sc-domain:/.test(a) ? 1 : 0); });
  if (!sites.length) throw new Error('Search Console: geen property voor ' + SEARCH_CONSOLE_DOMEIN + ' gevonden bij dit Google-account');
  var basis = 'https://www.googleapis.com/webmasters/v3/sites/' + encodeURIComponent(sites[0]) + '/searchAnalytics/query';
  var tz = Session.getScriptTimeZone();
  var dag = function (d) { return Utilities.formatDate(d, tz, 'yyyy-MM-dd'); };
  sc_.cache = {
    // Totaal over een periode [van, tot) als {klikken, vertoningen, ctr, positie}
    totaal: function (p) {
      var r = (haal(basis, { startDate: dag(p[0]), endDate: dag(dagen_(p[1], -1)) }).rows || [])[0] || {};
      return { klikken: r.clicks || 0, vertoningen: r.impressions || 0, ctr: r.ctr || 0, positie: r.position || 0 };
    },
    // Top-lijst per zoekwoord ('query') of pagina ('page')
    top: function (p, dimensie, aantal) {
      return (haal(basis, { startDate: dag(p[0]), endDate: dag(dagen_(p[1], -1)), dimensions: [dimensie], rowLimit: aantal }).rows || [])
        .map(function (r) {
          return [dimensie === 'page' ? r.keys[0].replace(/^https?:\/\/[^\/]+/, '') : r.keys[0], r.clicks, r.impressions,
            Math.round(r.ctr * 1000) / 10 + '%', Math.round(r.position * 10) / 10];
        });
    }
  };
  return sc_.cache;
}

// Blokken voor het tabblad Statistieken. Lukt het ophalen niet, dan staat de foutmelding in het tabblad en gaat de rest gewoon door.
function scBlokken_(getoond, dertig, aanvragen) {
  try {
    var sc = sc_();
    var tot = getoond.map(function (p) { return sc.totaal([p[1], p[2]]); });
    var rij = function (naam, f) { return [naam].concat(tot.map(f)); };
    var overzicht = [
      rij('Klikken vanuit Google', function (t) { return t.klikken; }),
      rij('Vertoningen in Google', function (t) { return t.vertoningen; }),
      rij('CTR (klikken / vertoningen)', function (t) { return Math.round(t.ctr * 1000) / 10 + '%'; }),
      rij('Gemiddelde positie', function (t) { return t.positie ? Math.round(t.positie * 10) / 10 : ''; }),
      rij('Aanvragen per 100 klikken', function (t, i) {
        var a = filter_(aanvragen, [getoond[i][1], getoond[i][2]]).length;
        return t.klikken ? Math.round(a / t.klikken * 1000) / 10 : '';
      })
    ];
    var koppen = ['Klikken', 'Vertoningen', 'CTR', 'Positie'];
    return [
      { titel: 'Google zoekresultaten (Search Console)', uitleg: 'De laatste 2-3 dagen zijn vaak nog niet compleet',
        koppen: [''].concat(getoond.map(function (p) { return p[0]; })), rijen: overzicht },
      { titel: 'Top zoekwoorden in Google (laatste 30 dagen)', koppen: ['Zoekwoord'].concat(koppen), rijen: sc.top(dertig, 'query', 30) },
      { titel: "Top pagina's in Google (laatste 30 dagen)", koppen: ['Pagina'].concat(koppen), rijen: sc.top(dertig, 'page', 25) }
    ];
  } catch (fout) {
    console.error(fout);
    return [{ titel: 'Google zoekresultaten (Search Console)', koppen: ['Kon niet worden opgehaald'], rijen: [[String(fout.message || fout)]] }];
  }
}

// Verwijdert per tabblad de regels die ouder zijn dan de bewaartermijn
function opruimen() {
  Object.keys(FORMULIEREN).forEach(function (k) {
    var cfg = FORMULIEREN[k];
    var sheet = blad(cfg);
    var laatste = sheet.getLastRow();
    if (laatste < 2) return;
    var grens = new Date();
    grens.setMonth(grens.getMonth() - cfg.bewaarMaanden);
    var datums = sheet.getRange(2, 1, laatste - 1, 1).getValues();
    // Van onder naar boven, zodat regelnummers niet verschuiven
    for (var i = datums.length - 1; i >= 0; i--) {
      var d = datums[i][0];
      if (d instanceof Date && d < grens) sheet.deleteRow(i + 2);
    }
  });
}

function blad(cfg) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(cfg.tabblad);
  if (!sheet) {
    var kolommen = ['Datum', 'Pagina'].concat(cfg.velden.map(function (v) { return v[1]; }));
    sheet = ss.insertSheet(cfg.tabblad);
    sheet.appendRow(kolommen);
    sheet.getRange(1, 1, 1, kolommen.length).setFontWeight('bold');
    sheet.setFrozenRows(1);
    sheet.getRange('A:A').setNumberFormat('dd-mm-yyyy hh:mm');
  }
  // Nieuwe velden toegevoegd? Dan ontbrekende kolomkoppen aanvullen.
  var koppen = ['Datum', 'Pagina'].concat(cfg.velden.map(function (v) { return v[1]; }));
  var huidig = sheet.getLastColumn();
  if (huidig < koppen.length) {
    sheet.getRange(1, huidig + 1, 1, koppen.length - huidig).setValues([koppen.slice(huidig)]).setFontWeight('bold');
  }
  return sheet;
}

function stuurMail(cfg, g, onderwerp) {
  var rijen = cfg.velden.map(function (v) { return [v[1], g[v[0]]]; }).concat([['Pagina', g.pagina]]);
  var html = '<table cellpadding="6" style="border-collapse:collapse;font-family:Arial,sans-serif;font-size:14px">' +
    rijen.filter(function (r) { return r[1]; }).map(function (r) {
      return '<tr><th align="left" valign="top" style="background:#F1EDE5">' + r[0] + '</th><td>' +
        html_(r[1]).replace(/\n/g, '<br>') + '</td></tr>';
    }).join('') + '</table>' +
    '<p style="font-family:Arial,sans-serif;font-size:12px;color:#777">Deze inzending staat ook in de Google Sheet "' +
    html_(SpreadsheetApp.getActiveSpreadsheet().getName()) + '", tabblad "' + cfg.tabblad + '".</p>';
  MailApp.sendEmail({
    to: ONTVANGER,
    replyTo: /@/.test(g.email || g.contact || '') ? (g.email || g.contact) : ONTVANGER,
    name: AFZENDER_NAAM,
    subject: onderwerp,
    htmlBody: html
  });
}

function antwoord(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

function schoon(waarde, max) {
  return String(waarde || '').trim().slice(0, max);
}

// Voorkomt dat tekst die met = + - @ begint als formule wordt uitgevoerd, en dat Sheets
// de voorloopnul van een telefoonnummer weghaalt (0612... wordt anders 612...)
function veiligVoorSheet(tekst) {
  return /^[=+\-@]/.test(tekst) || /^0\d/.test(tekst) ? "'" + tekst : tekst;
}

function html_(tekst) {
  return String(tekst || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
