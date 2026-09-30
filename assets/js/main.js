/* Escape Game The Hunt: menu en boekingsformulier. Geen trackers, geen externe scripts. */
(function () {
  'use strict';

  /* Menu op mobiel */
  var toggle = document.querySelector('.nav-toggle');
  var nav = document.getElementById('nav');
  if (toggle && nav) {
    toggle.addEventListener('click', function () {
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
})();
