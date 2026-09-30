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

  /* Boekingsformulier.
     Een statische site heeft geen server. Zet in src/data/site.json "form_endpoint" op een formulierdienst
     (bijv. Formspree of Basin) die een POST accepteert; zonder endpoint opent de mail-app met een ingevuld bericht. */
  document.querySelectorAll('form[data-booking]').forEach(function (form) {
    var endpoint = form.getAttribute('data-endpoint') || '';
    var email = form.getAttribute('data-email');

    function note(text, isError) {
      var n = form.querySelector('.form-note');
      if (!n) { n = document.createElement('p'); n.setAttribute('role', 'status'); form.appendChild(n); }
      n.className = 'form-note' + (isError ? ' error' : '');
      n.textContent = text;
    }

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      if (form.querySelector('.hp input').value) { return; }
      if (!form.checkValidity()) { form.reportValidity(); return; }
      var data = new FormData(form);
      data.delete('website');
      if (endpoint) {
        var btn = form.querySelector('[type=submit]');
        btn.disabled = true;
        fetch(endpoint, { method: 'POST', body: data, headers: { Accept: 'application/json' } })
          .then(function (r) { if (!r.ok) { throw new Error(r.status); } })
          .then(function () { form.reset(); note('Bedankt! We hebben je aanvraag ontvangen en nemen snel contact met je op.'); })
          .catch(function () { note('Versturen lukte niet. Mail ons op ' + email + ' of bel 085 004 7719.', true); })
          .then(function () { btn.disabled = false; });
        return;
      }
      var lines = [];
      data.forEach(function (v, k) { if (v) { lines.push(k + ': ' + v); } });
      var subject = 'Aanvraag The Hunt' + (data.get('Stad') ? ' ' + data.get('Stad') : '');
      window.location.href = 'mailto:' + email + '?subject=' + encodeURIComponent(subject) + '&body=' + encodeURIComponent(lines.join('\n'));
      note('Je mailprogramma opent met je aanvraag. Verstuur die mail om de aanvraag af te ronden. Opent er niets? Mail naar ' + email + '.');
    });
  });
})();
