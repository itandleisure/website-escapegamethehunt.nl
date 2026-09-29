/*
 * Escape Game The Hunt: small vanilla replacement for the Flatsome/jQuery
 * scripts of the old WordPress site (menu, sticky header, sliders,
 * accordions, countdown, table of contents and the booking/contact forms).
 */
(function () {
  'use strict';

  /*
   * Forms. The WordPress site handled forms on the server (HappyForms).
   * A static site has no server, so set FORM_ENDPOINT to a form service
   * (e.g. Formspree, Basin, Netlify Forms) that accepts a POST with the
   * field values. Leave it empty to open the visitor's e-mail program with
   * a pre-filled message to FORM_EMAIL instead.
   */
  var FORM_ENDPOINT = '';
  var FORM_EMAIL = 'info@escapegamethehunt.nl';

  var doc = document.documentElement;
  doc.classList.add('has-js');

  function $all(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }

  /* ---------- Mobile menu ---------- */
  var menu = document.getElementById('main-menu');
  if (menu) {
    var overlay = document.createElement('div');
    overlay.className = 'menu-overlay';
    var closeBtn = document.createElement('button');
    closeBtn.type = 'button';
    closeBtn.className = 'menu-close';
    closeBtn.setAttribute('aria-label', 'Menu sluiten');
    closeBtn.innerHTML = '&times;';
    document.body.appendChild(overlay);
    document.body.appendChild(closeBtn);
    var openers = $all('[data-open="#main-menu"]');

    var setMenu = function (open) {
      doc.classList.toggle('menu-open', open);
      openers.forEach(function (o) { o.setAttribute('aria-expanded', open ? 'true' : 'false'); });
      if (open) { menu.querySelector('a').focus(); }
    };
    openers.forEach(function (o) {
      o.addEventListener('click', function (e) { e.preventDefault(); setMenu(true); });
    });
    overlay.addEventListener('click', function () { setMenu(false); });
    closeBtn.addEventListener('click', function () { setMenu(false); });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && doc.classList.contains('menu-open')) { setMenu(false); }
    });

    $all('.nav-sidebar > li', menu).forEach(function (li) {
      var sub = li.querySelector(':scope > ul.children');
      if (!sub) { return; }
      var t = document.createElement('button');
      t.type = 'button';
      t.className = 'toggle';
      t.setAttribute('aria-label', 'Submenu tonen');
      t.setAttribute('aria-expanded', 'false');
      t.innerHTML = '<i class="icon-angle-down" aria-hidden="true"></i>';
      li.insertBefore(t, sub);
      var toggle = function (e) {
        e.preventDefault();
        var open = li.classList.toggle('is-open');
        t.setAttribute('aria-expanded', open ? 'true' : 'false');
      };
      t.addEventListener('click', toggle);
      var link = li.querySelector(':scope > a');
      if (link && link.getAttribute('href') === '#') { link.addEventListener('click', toggle); }
      if (li.classList.contains('active')) { li.classList.add('is-open'); }
    });
  }

  // "Over" has no page of its own; don't jump to the top when it is clicked.
  $all('.header-nav a[href="#"]').forEach(function (a) {
    a.addEventListener('click', function (e) { e.preventDefault(); });
  });

  /* ---------- Sticky header + back-to-top ---------- */
  var header = document.getElementById('header');
  var wrap = header && header.querySelector('.header-wrapper');
  var topLink = document.getElementById('top-link');
  if (wrap && header.classList.contains('has-sticky')) {
    var headerHeight = 0;
    var onScroll = function () {
      var y = window.pageYOffset;
      if (!wrap.classList.contains('stuck')) { headerHeight = wrap.offsetHeight; }
      var stick = y > headerHeight + 100;
      if (stick !== wrap.classList.contains('stuck')) {
        if (!header.classList.contains('transparent')) {
          header.style.minHeight = stick ? headerHeight + 'px' : '';
        }
        wrap.classList.toggle('stuck', stick);
      }
      if (topLink) { topLink.classList.toggle('active', y > 400); }
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }
  if (topLink) {
    topLink.addEventListener('click', function () { window.scrollTo({ top: 0, behavior: 'smooth' }); });
  }

  /* ---------- Scroll-in animations (data-animate) ---------- */
  var animated = $all('[data-animate]');
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.setAttribute('data-animated', 'true'); io.unobserve(en.target); }
      });
    }, { rootMargin: '0px 0px -10% 0px' });
    animated.forEach(function (el) { io.observe(el); });
  } else {
    animated.forEach(function (el) { el.setAttribute('data-animated', 'true'); });
  }

  /* ---------- Sliders ---------- */
  var arrow = '<svg class="flickity-button-icon" viewBox="0 0 100 100" aria-hidden="true">' +
    '<path d="M 10,50 L 60,100 L 70,90 L 30,50 L 70,10 L 60,0 Z" class="arrow"></path></svg>';
  $all('.slider[data-flickity-options]').forEach(function (slider) {
    var opts = {};
    try { opts = JSON.parse(slider.getAttribute('data-flickity-options')); } catch (e) { /* defaults */ }
    var cells = slider.children;
    if (cells.length < 2) { return; }
    var holder = slider.closest('.slider-wrapper') || slider.parentNode;

    var step = function (dir) {
      var max = slider.scrollWidth - slider.clientWidth;
      var target = slider.scrollLeft + dir * slider.clientWidth;
      if (opts.wrapAround !== false) {
        if (dir > 0 && slider.scrollLeft >= max - 2) { target = 0; }
        if (dir < 0 && slider.scrollLeft <= 2) { target = max; }
      }
      slider.scrollTo({ left: target, behavior: 'smooth' });
    };

    if (opts.prevNextButtons !== false) {
      [['previous', 'Vorige', -1], ['next', 'Volgende', 1]].forEach(function (b) {
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'flickity-button flickity-prev-next-button ' + b[0];
        btn.setAttribute('aria-label', b[1]);
        btn.innerHTML = b[0] === 'next' ? arrow.replace('<path', '<path transform="translate(100, 100) rotate(180)"') : arrow;
        btn.addEventListener('click', function () { step(b[2]); });
        holder.appendChild(btn);
      });
    }

    if (opts.adaptiveHeight) {
      // Size the slider to the photo in view instead of the tallest one.
      var fit = function () {
        var i = Math.round(slider.scrollLeft / (slider.clientWidth || 1));
        var cell = cells[Math.min(i, cells.length - 1)];
        if (cell && cell.offsetHeight) { slider.style.height = cell.offsetHeight + 'px'; }
      };
      var t = null;
      slider.style.transition = 'height .3s';
      slider.addEventListener('scroll', function () { clearTimeout(t); t = setTimeout(fit, 80); }, { passive: true });
      window.addEventListener('resize', fit);
      $all('img', slider).forEach(function (img) { img.addEventListener('load', fit); });
      fit();
    }

    var auto = opts.autoPlay;
    if (auto && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      var delay = typeof auto === 'number' ? auto : 3000;
      var timer = null;
      var start = function () { stop(); timer = setInterval(function () { step(1); }, delay); };
      var stop = function () { if (timer) { clearInterval(timer); timer = null; } };
      holder.addEventListener('mouseenter', stop);
      holder.addEventListener('mouseleave', start);
      holder.addEventListener('focusin', stop);
      start();
    }
  });

  /* ---------- Accordions ---------- */
  $all('.accordion-title').forEach(function (title) {
    title.addEventListener('click', function (e) {
      e.preventDefault();
      var open = !title.classList.contains('active');
      title.classList.toggle('active', open);
      title.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  });

  /* ---------- Table of contents (Easy TOC) ---------- */
  $all('#ez-toc-container').forEach(function (toc) {
    var t = toc.querySelector('.ez-toc-toggle');
    if (t) {
      t.addEventListener('click', function (e) { e.preventDefault(); toc.classList.toggle('is-collapsed'); });
    }
  });

  /* ---------- Countdown ---------- */
  $all('.ux-timer-text[data-countdown]').forEach(function (el) {
    var p = el.getAttribute('data-countdown').match(/(\d+)\/(\d+)\/(\d+)\s+(\d+):(\d+)/);
    if (!p) { return; }
    var end = new Date(+p[1], +p[2] - 1, +p[3], +p[4], +p[5]).getTime();
    var label = function (n, key) {
      return n + ' ' + el.getAttribute('data-text-' + key + (n === 1 ? '' : '-p'));
    };
    var tick = function () {
      var s = Math.max(0, Math.floor((end - Date.now()) / 1000));
      var d = Math.floor(s / 86400);
      var w = Math.floor(d / 7);
      var parts = [];
      if (w) { parts.push(label(w, 'week')); }
      parts.push(label(d % 7, 'day'), label(Math.floor(s % 86400 / 3600), 'hour'),
        label(Math.floor(s % 3600 / 60), 'min'), label(s % 60, 'sec'));
      el.textContent = parts.join(' ');
      if (s === 0) { clearInterval(iv); }
    };
    var iv = setInterval(tick, 1000);
    tick();
  });

  /* ---------- Forms ---------- */
  function fieldLabel(input) {
    var part = input.closest('.happyforms-part');
    var l = part && part.querySelector('.happyforms-part__label .label');
    return l ? l.textContent.trim() : (input.name || 'Veld');
  }

  function fieldValue(input) {
    if (input.type === 'radio' || input.type === 'checkbox') {
      var opt = input.closest('.happyforms-part__option');
      var l = opt && opt.querySelector('.label');
      return l ? l.textContent.trim() : input.value;
    }
    if (input.tagName === 'SELECT') {
      var o = input.options[input.selectedIndex];
      return o ? o.text.trim() : '';
    }
    return input.value.trim();
  }

  function note(form, text, isError) {
    var n = form.querySelector('.static-form-note');
    if (!n) {
      n = document.createElement('p');
      n.className = 'static-form-note';
      n.setAttribute('role', 'status');
      form.appendChild(n);
    }
    n.classList.toggle('is-error', !!isError);
    n.textContent = text;
  }

  $all('form[data-static-form]').forEach(function (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var honeypot = form.querySelector('[data-honeypot]');
      if (honeypot && honeypot.value) { return; }

      var missing = $all('[required]', form).filter(function (i) { return !i.value; });
      if (missing.length) {
        note(form, 'Vul a.u.b. alle verplichte velden in: ' +
          missing.map(fieldLabel).join(', ') + '.', true);
        missing[0].focus();
        return;
      }

      var rows = [];
      var data = new FormData();
      $all('input, select, textarea', form).forEach(function (i) {
        if (!i.name || i.type === 'hidden' || i.hasAttribute('data-honeypot') || i.type === 'submit') { return; }
        if ((i.type === 'radio' || i.type === 'checkbox') && !i.checked) { return; }
        var v = fieldValue(i);
        if (!v) { return; }
        var k = fieldLabel(i);
        rows.push(k + ': ' + v);
        data.append(k, v);
      });
      var subject = 'Aanvraag via de website - ' + document.title.replace(/ - Escape Game The Hunt$/, '');
      data.append('_subject', subject);
      data.append('Pagina', location.href);

      if (FORM_ENDPOINT) {
        var btn = form.querySelector('[type=submit]');
        if (btn) { btn.disabled = true; }
        fetch(FORM_ENDPOINT, { method: 'POST', body: data, headers: { Accept: 'application/json' } })
          .then(function (r) {
            if (!r.ok) { throw new Error(r.status); }
            form.reset();
            note(form, 'Bedankt! We hebben je aanvraag ontvangen en nemen snel contact met je op.');
          })
          .catch(function () {
            note(form, 'Er ging iets mis bij het versturen. Mail ons op ' + FORM_EMAIL +
              ' of bel +31850047719.', true);
          })
          .then(function () { if (btn) { btn.disabled = false; } });
        return;
      }

      var body = rows.join('\n') + '\n\nPagina: ' + location.href;
      window.location.href = 'mailto:' + FORM_EMAIL + '?subject=' + encodeURIComponent(subject) +
        '&body=' + encodeURIComponent(body);
      note(form, 'Je e-mailprogramma wordt geopend met je aanvraag. Verstuur de e-mail om je aanvraag ' +
        'af te ronden. Lukt dat niet? Mail ons op ' + FORM_EMAIL + ' of bel +31850047719.');
    });
  });
})();
