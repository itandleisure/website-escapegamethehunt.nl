/* Escape Game The Hunt: menu en boekingsformulier. Geen trackers, geen externe scripts. */
(function () {
  'use strict';

  /* Menu op mobiel */
  var toggle = document.querySelector('.nav-toggle');
  var nav = document.getElementById('nav');
  if (toggle && nav) {
    toggle.addEventListener('click', function () {
      nav.classList.add('anim');  // animatie alleen bij openen/sluiten, niet bij het draaien of verkleinen van het scherm
      var open = nav.classList.toggle('open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    nav.addEventListener('click', function (e) {
      if (e.target.closest('a')) { nav.classList.remove('open'); toggle.setAttribute('aria-expanded', 'false'); }
    });
  }

  /* Trailer: Vimeo laadt pas na een klik, zodat er zonder klik geen verbinding met Vimeo is. */
  document.querySelectorAll('.trailer[data-vimeo]').forEach(function (box) {
    box.querySelector('.play').addEventListener('click', function () {
      var f = document.createElement('iframe');
      f.src = 'https://player.vimeo.com/video/' + box.getAttribute('data-vimeo') + '?dnt=1&autoplay=1';
      f.title = 'Trailer Escape Game The Hunt';
      f.allow = 'autoplay; fullscreen; picture-in-picture';
      f.allowFullscreen = true;
      box.innerHTML = '';
      box.appendChild(f);
      box.classList.add('playing');
    });
  });

  /* Videoband: korte loop (eigen mp4, gedempt) starten zodra hij in beeld komt en pauzeren daarbuiten.
     Bij "minder beweging" in de systeeminstellingen blijft de poster (foto) staan. */
  var still = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  function play(v) { var p = v.play(); if (p && p.catch) { p.catch(function () {}); } }
  var vids = document.querySelectorAll('video[data-autoplay]');
  if (vids.length && 'IntersectionObserver' in window && !still) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        var v = en.target;
        if (en.isIntersecting) {
          if (!v.dataset.loaded) {
            v.dataset.loaded = '1';
            v.autoplay = true;            // de browser start zelf zodra er genoeg geladen is
            v.preload = 'auto';
            v.addEventListener('canplay', function () { play(v); }, { once: true });
            v.load();
          } else { play(v); }
        } else { v.pause(); }
      });
    }, { rootMargin: '150px' });
    vids.forEach(function (v) { io.observe(v); });
  }

  /* Boekingsformulier (zelfde opzet als coworkingcompeta.com en badassrentals.nl).
     - Staat er een Google Apps Script-URL in data-google (uit "google_form_url" in src/data/site.json), dan gaat
       de aanvraag naar die Google Sheet + e-mail en daarna naar de bedankpagina.
     - Is die leeg of lukt het niet, dan verstuurt het formulier gewoon via FormSubmit (de action in de HTML).
       Zo gaat er nooit een aanvraag verloren. */
  var opened = Date.now();
  document.querySelectorAll('form[data-booking]').forEach(function (form) {
    var google = form.getAttribute('data-google');
    form.addEventListener('submit', function (e) {
      if (!form.checkValidity()) { e.preventDefault(); form.reportValidity(); return; }
      if (window.gtag) {
        var stad = form.querySelector('[name="stad"]');
        gtag('event', 'generate_lead', { stad: stad ? stad.value : '', pagina: location.pathname });
      }
      if (!google || !window.fetch || !window.URLSearchParams) { return; }
      e.preventDefault();
      var btn = form.querySelector('[type=submit]');
      btn.disabled = true;
      var data = new URLSearchParams(new FormData(form));
      data.append('pagina', location.pathname);
      data.append('duur', String(Date.now() - opened));
      fetch(google, { method: 'POST', body: data })
        .then(function (r) { return r.json(); })
        .then(function (res) {
          if (!res.ok) { throw new Error(res.fout || 'mislukt'); }
          location.href = new URL(form.querySelector('[name="_next"]').value).pathname;
        })
        .catch(function () { form.submit(); });
    });
  });

  /* Cookiemelding voor Google Analytics en Google Ads-conversiemeting (Consent Mode, zie GA_HEAD in tools/render.py). */
  var bar = document.getElementById('cookiebar');
  if (bar) {
    var keuze = null;
    try { keuze = localStorage.getItem('cookiekeuze-v2'); } catch (e) {}
    if (!keuze) { bar.hidden = false; }
    bar.querySelectorAll('[data-cookie]').forEach(function (b) {
      b.addEventListener('click', function () {
        var ja = b.getAttribute('data-cookie') === 'ja';
        try { localStorage.setItem('cookiekeuze-v2', ja ? 'ja' : 'nee'); } catch (e) {}
        if (window.gtag) { var g = ja ? 'granted' : 'denied'; gtag('consent', 'update', { analytics_storage: g, ad_storage: g, ad_user_data: g }); }
        bar.hidden = true;
      });
    });
    document.querySelectorAll('[data-cookie-open]').forEach(function (b) {
      b.addEventListener('click', function () { bar.hidden = false; });
    });
  }
})();
