# escapegamethehunt.nl

Statische site voor Escape Game The Hunt, gehost op GitHub Pages (map `docs/`, domein in `docs/CNAME`). Eigen HTML, CSS en een klein stukje JavaScript, zonder WordPress,
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
docs/assets/css/style.css  het hele ontwerp
docs/assets/js/main.js     mobiel menu, trailer (Vimeo pas na klik) en boekingsformulier
tools/google-formulier/    Google Apps Script voor aanvragen (Google Sheet + e-mail)
docs/assets/uploads/       alle afbeeldingen en video's
docs/_redirects, .htaccess 301-doorverwijzingen voor andere hosting (GitHub Pages leest ze niet;
                           daar zorgen doorverwijspagina's en docs/404.html voor)
docs/                      de gebouwde website: dit is wat GitHub Pages publiceert
```

## Bouwen en bekijken

```bash
python tools/build.py
python -m http.server 8080 --directory docs
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
- **Ontwerp**: `docs/assets/css/style.css`. De kleuren en letters staan bovenaan als variabelen.
- **Pagina weghalen**: haal het JSON-bestand weg, verwijder de map met `index.html` en zet een 301 in
  `_redirects` en `.htaccess`.

Pas de gegenereerde `index.html`-bestanden niet met de hand aan: de volgende build overschrijft ze.
Doorverwijspagina's (met een meta refresh) laat het bouwscript met rust.

## Formulier (zelfde opzet als coworkingcompeta.com en badassrentals.nl)

Het boekingsformulier werkt in twee stappen:

1. **Google Sheet + e-mail.** Staat `google_form_url` in `src/data/site.json` ingevuld, dan stuurt
   `docs/assets/js/main.js` elke aanvraag naar het Google Apps Script `tools/google-formulier/Code.gs`. Dat zet de
   aanvraag in het tabblad "Aanvragen", mailt info@escapegamethehunt.nl (antwoorden gaat direct naar de klant) en
   ruimt aanvragen ouder dan 12 maanden automatisch op. Daarna gaat de bezoeker naar `/bedankt/`.
2. **FormSubmit als reserve.** Is `google_form_url` leeg of lukt Google niet, dan gaat het formulier gewoon via
   FormSubmit (`https://formsubmit.co/info@escapegamethehunt.nl`) naar hetzelfde adres. Bij de allereerste
   inzending stuurt FormSubmit een activatiemail naar info@; die link moet één keer worden aangeklikt.

Google Sheet instellen (eenmalig):

1. Maak een Google Sheet, bijv. "The Hunt aanvragen". Extensies > Apps Script: plak `tools/google-formulier/Code.gs`.
2. Kies bovenin de functie `installeer` en klik op Uitvoeren (toestemming geven).
3. Implementeren > Nieuwe implementatie > Web-app, "Uitvoeren als: ik", "Toegang: iedereen".
4. Zet de /exec-URL in `google_form_url` in `src/data/site.json`, draai `python tools/build.py`, commit en push.

## Privacy

Geen analytics, geen trackers, geen Google Fonts. De trailer laadt Vimeo pas na een klik op afspelen.
