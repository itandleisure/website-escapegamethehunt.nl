/**
 * Verstuurt het wekelijkse statistiekenrapport van escapegamethehunt.nl.
 *
 * Installeren (eenmalig):
 * 1. Ga naar https://script.google.com en maak een nieuw project "Statistieken The Hunt".
 * 2. Plak deze code in Code.gs en sla op.
 * 3. Projectinstellingen (tandwiel) > Scripteigenschappen > eigenschap toevoegen:
 *    naam TOKEN, waarde = "mail_token" uit tools/seo/statistiek.local.json.
 * 4. Implementeren > Nieuwe implementatie > Type: Web-app.
 *    Uitvoeren als: ik. Toegang: iedereen. Klik Implementeren en geef toestemming.
 * 5. Kopieer de web-app-URL (eindigt op /exec) en zet die als "mail_url" in statistiek.local.json
 *    (of stuur hem naar Claude, dan zet hij hem erin).
 */
function doPost(e) {
  var d = JSON.parse(e.postData.contents);
  var token = PropertiesService.getScriptProperties().getProperty('TOKEN');
  if (!token || d.token !== token) {
    return ContentService.createTextOutput('geweigerd');
  }
  MailApp.sendEmail({
    to: d.to,
    subject: d.subject,
    htmlBody: d.html,
    name: 'Escape Game The Hunt'
  });
  return ContentService.createTextOutput('verstuurd naar ' + d.to);
}
