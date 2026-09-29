# escapegamethehunt.nl (statische site)

Statische versie van [escapegamethehunt.nl](https://escapegamethehunt.nl), overgezet vanaf WordPress
(Flatsome-thema) in september 2026. Gewone HTML/CSS met een klein stukje JavaScript, zonder database,
PHP of plugins.

## Structuur

```
index.html                   homepage
<pagina>/index.html          elke pagina/blogpost staat op dezelfde URL als op WordPress
category/<stad>/             nieuwsoverzicht per stad
escape-game-the-hunt-nieuws/page/N/   nieuwsarchief, pagina 2 t/m 6
assets/css/flatsome.css      originele Flatsome-stylesheet (ongewijzigd)
assets/css/theme.css         kleuren, lettertypes en instellingen uit de WordPress-customizer
assets/css/site.css          aanvullingen voor de statische site (menu, sliders, accordions)
assets/css/*.css             stylesheets van formulieren, inhoudsopgave, kaart en countdown
assets/js/site.js            menu, sticky header, sliders, accordions, countdown, formulieren
assets/uploads/              alle afbeeldingen en video (zelfde mappen als wp-content/uploads)
partials/                    gedeelde header, footer en mobiel menu
tools/build.py               zet de partials in alle pagina's + maakt sitemap.xml/robots.txt
tools/import_wordpress.py    eenmalig gebruikt importscript (ter referentie)
```

## Lokaal bekijken

De links beginnen met `/`, dus open de site via een webserver in plaats van dubbelklikken:

```bash
python -m http.server 8080
```

en ga naar http://localhost:8080.

## Aanpassen

- **Tekst of afbeeldingen op een pagina**: pas `<pagina>/index.html` direct aan. Afbeeldingen komen in `assets/uploads/`.
- **Menu, header of footer**: pas het bestand in `partials/` aan en draai daarna `python tools/build.py`.
  Dat zet de nieuwe versie in alle pagina's en markeert het actieve menu-item.
- **Interne links**: `python tools/build.py` zet onderaan elke blogpost een blok met links naar de
  stadspagina, het nieuwsoverzicht van die stad en de prijzen, en op elk nieuwsoverzicht een link
  naar de stadspagina. Dat gebeurt op basis van de categorie in `<article class="... category-<stad>">`.
  De footer (`partials/footer.html`) linkt naar alle vaste pagina's.
- **Nieuwe pagina**: kopieer een bestaande `index.html` naar een nieuwe map, pas de inhoud, `<title>`,
  description en canonical aan en draai `python tools/build.py` (die werkt ook de sitemap bij).

## Formulieren (boekingsaanvraag, contact, vacatures)

Op WordPress werden de formulieren (HappyForms) door de server verstuurd. Een statische site heeft geen
server, dus in `assets/js/site.js` staan bovenaan twee instellingen:

- `FORM_ENDPOINT`: leeg laten, of het adres van een formulierdienst (bijv. Formspree, Basin of Netlify Forms).
  Die krijgt de ingevulde velden als POST en mailt ze door.
- `FORM_EMAIL`: zolang er geen endpoint is, opent het formulier het e-mailprogramma van de bezoeker met een
  ingevulde e-mail aan dit adres.

## Wat er niet meer in zit

Google Analytics/Tag Manager/Ads, WordPress-scripts (jQuery, emoji, wp-json, REST API) en de reCAPTCHA
van het formulier. Voeg tracking alleen weer toe als dat bewust gewenst is (let dan op cookiemelding/AVG).
De kaart op /escape-game-the-hunt-locaties/ laadt nog amCharts vanaf cdn.amcharts.com.
