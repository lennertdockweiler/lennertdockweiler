// Bewertung der bestehenden Website: Punktzahl (0 = dringender Bedarf, 100 = alles gut)
// und Befunde in Briefsprache (sachlich, freundlich, überprüfbar).
import { domainVon } from './util.mjs';

const JAHR = new Date().getFullYear();

/**
 * @returns {{ score: number, kategorie: string, befunde: {code:string, gewicht:number, kurz:string, brief:string}[] }}
 */
export function bewerte(lead, p) {
  const befunde = [];
  const add = (code, gewicht, kurz, brief) => befunde.push({ code, gewicht, kurz, brief });
  const domain = domainVon(p?.finalUrl || lead.website) ?? lead.website;

  if (!lead.website || p?.keineWebsite) {
    return { score: 0, kategorie: 'keine-website', befunde: [{ code: 'keine-website', gewicht: 100, kurz: 'Keine Website gefunden', brief: '' }] };
  }
  if (!p || p.erreichbar === false) {
    return {
      score: 5,
      kategorie: 'nicht-erreichbar',
      befunde: [
        {
          code: 'nicht-erreichbar',
          gewicht: 95,
          kurz: `Website nicht erreichbar (${p?.fehler ?? 'unbekannt'})`,
          brief: `Ihre Website ${domain} war bei unserem Test nicht erreichbar (${p?.fehler ?? 'keine Antwort'}). Wer Sie über Google findet, landet dann auf einer Fehlerseite.`,
        },
      ],
    };
  }

  if (p.sslFehler) add('ssl', 25, 'SSL-Zertifikat fehlerhaft', 'Das Sicherheitszertifikat der Seite ist fehlerhaft – viele Browser warnen Besucher deshalb, bevor sie die Seite öffnen.');
  else if (!p.https) add('kein-https', 25, 'Kein HTTPS', 'Die Seite wird ohne verschlüsselte Verbindung (HTTPS) ausgeliefert – Browser zeigen dann „Nicht sicher“ neben der Adresse an.');

  const nichtMobil = !p.viewportMeta || p.overflowPx > 24;
  if (nichtMobil) add('nicht-mobil', 25, 'Nicht für Smartphones optimiert', 'Auf dem Smartphone ist die Seite nicht an kleine Bildschirme angepasst – man muss zoomen oder seitlich scrollen.');
  else if (p.kleineSchriftAnteil > 0.4) add('kleine-schrift', 10, 'Sehr kleine Schrift auf dem Handy', 'Auf dem Smartphone ist ein Großteil der Schrift sehr klein und schwer lesbar.');

  // Ladezeit: Messung inkl. Netz – deshalb großzügige Schwellen und vorsichtige Formulierung
  if (p.ladezeitMs > 8000) add('langsam', 15, `Ladezeit ca. ${Math.round(p.ladezeitMs / 1000)} s`, `In unserem Test brauchte die Seite auf dem Smartphone rund ${Math.round(p.ladezeitMs / 1000)} Sekunden, bis sie vollständig geladen war – viele Besucher springen vorher ab.`);
  else if (p.ladezeitMs > 5000) add('traege', 7, `Ladezeit ca. ${(p.ladezeitMs / 1000).toFixed(1).replace('.', ',')} s`, '');

  if (p.megabytes > 6) add('schwer', 8, `${String(p.megabytes).replace('.', ',')} MB Seitengewicht`, `Beim Öffnen werden rund ${String(Math.round(p.megabytes)).replace('.', ',')} MB geladen – im Mobilfunknetz kostet das Zeit und Datenvolumen.`);

  if (p.copyrightJahr && p.copyrightJahr <= JAHR - 3) add('veraltet', 15, `© ${p.copyrightJahr} im Footer`, `Im Fußbereich steht „© ${p.copyrightJahr}“ – das wirkt auf Besucher schnell, als würde die Seite nicht mehr gepflegt.`);

  // Nur melden, wenn die Seite echten Inhalt hat und „Impressum“ nirgends im HTML vorkommt
  if (!p.impressumLink && !p.impressumImHtml && (p.textLaenge ?? 0) > 800) add('kein-impressum', 10, 'Kein Impressum-Link gefunden', 'Auf der Startseite haben wir keinen Link zum Impressum gefunden – das ist für Firmen-Websites Pflicht.');
  if (p.googleFonts) add('google-fonts', 6, 'Google Fonts extern geladen', 'Schriften werden direkt von Google-Servern geladen. Das ist datenschutzrechtlich heikel und wurde in Deutschland bereits abgemahnt (LG München I, 2022).');
  if (!p.telLink && p.telefonSichtbar) add('kein-tel', 5, 'Telefonnummer nicht antippbar', 'Die Telefonnummer lässt sich auf dem Handy nicht direkt antippen und anrufen.');
  if (!p.metaBeschreibung) add('keine-meta', 3, 'Keine Seitenbeschreibung für Google', 'Für Google fehlt eine Seitenbeschreibung – in den Suchergebnissen erscheint dann ein zufälliger Textausschnitt.');
  if (p.baukasten) add('baukasten', 0, 'Baukasten-System', '');
  if (p.jquery && /^1\.([0-9]|1[01])\./.test(p.jquery)) add('alte-technik', 4, `Veraltete Technik (jQuery ${p.jquery})`, '');

  befunde.sort((a, b) => b.gewicht - a.gewicht);
  const score = Math.max(0, 100 - befunde.reduce((s, b) => s + b.gewicht, 0));
  return { score, kategorie: score < 50 ? 'dringend' : score < 75 ? 'potenzial' : 'gut', befunde };
}

/** Die (bis zu) drei wichtigsten Befunde für den Brief */
export const briefBefunde = (bewertung, max = 3) => bewertung.befunde.filter((b) => b.brief).slice(0, max);
