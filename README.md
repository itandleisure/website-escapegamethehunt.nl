# escapegamethehunt.nl

Statische site voor Escape Game The Hunt. Eigen HTML, CSS en een klein stukje JavaScript, zonder WordPress,
database, plugins of externe scripts. Alle pagina's worden gegenereerd door één bouwscript.

## Structuur

```
src/data/site.json         contactgegevens, prijzen, menu, reviews, formulier-endpoint
src/data/locations.json    de 33 speelsteden: naam, provincie, coördinaten, URL, startlocatie
src/content/locaties/      per stad: titel, meta, tekst, FAQ en gerelateerde berichten
src/content/pages/         blogs en losse pagina's: titel, meta, datum, categorie, tekst
tools/build.py             bouwt alle pagina's + sitemap.xml + robots.txt
tools/render.py            basislayout, kop, voet, kaart, prijzen, formulier, FAQ
tools/pages.py             homepage en locatiepagina's
tools/pages_more.py        blogs, prijzen, contact, FAQ, sfeerimpressie, nieuws, categorieën, overige pagina's
tools/extract_content.py   eenmalig gebruikt om de tekst uit de oude WordPress-pagina's te halen (vereist beautifulsoup4)
assets/css/style.css       het hele ontwerp
assets/js/main.js          mobiel menu, trailer (Vimeo pas na klik) en boekingsformulier
assets/uploads/            alle afbeeldingen en video's
_redirects / .htaccess     301-doorverwijzingen (Netlify/Cloudflare Pages resp. Apache)
```

## Bouwen en bekijken

```bash
python tools/build.py
python -m http.server 8080
```

Ga daarna naar http://localhost:8080. Het bouwscript heeft alleen standaard-Python nodig.

## Aanpassen

- **Prijzen, telefoon, e-mail, menu, reviews**: `src/data/site.json`, daarna `python tools/build.py`.
- **Tekst van een stad**: het veld `body` of `faq` in `src/content/locaties/<stad>.json`.
- **Startlocatie van een stad**: `start` in `src/data/locations.json`. Die verschijnt in de hero, de boekkaart en de spelklok.
- **Nieuwe stad**: voeg een regel toe aan `src/data/locations.json` en maak `src/content/locaties/<slug>.json`
  (kopieer een bestaande). De stad komt dan automatisch op de kaart, in de provincielijst, de footer en het formulier.
- **Blog of pagina**: `src/content/pages/<pad>.json`. Een blog heeft een categorie (de stad); die bepaalt de
  links naar de locatiepagina en de gerelateerde berichten.
- **Ontwerp**: `assets/css/style.css`. De kleuren en letters staan bovenaan als variabelen.
- **Pagina weghalen**: haal het JSON-bestand weg, verwijder de map met `index.html` en zet een 301 in
  `_redirects` en `.htaccess`.

Pas de gegenereerde `index.html`-bestanden niet met de hand aan: de volgende build overschrijft ze.
Doorverwijspagina's (met een meta refresh) laat het bouwscript met rust.

## Formulier

Het boekingsformulier stuurt naar `form_endpoint` in `src/data/site.json` (bijvoorbeeld Formspree of Basin).
Zolang dat leeg is, opent het formulier het e-mailprogramma van de bezoeker met een ingevulde aanvraag.

## Privacy

Geen analytics, geen trackers, geen Google Fonts. De trailer laadt Vimeo pas na een klik op afspelen.
