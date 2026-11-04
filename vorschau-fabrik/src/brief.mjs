// Briefe nach DIN 5008 (Form B, Fensterumschlag DL/C5/C4) mit QR-Code zur persönlichen Vorschau.
// Seite 1: Anschreiben. Seite 2 (Rückseite): Vorher/Nachher, Funktionen, Datenschutzhinweis.
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { briefBefunde } from './bewertung.mjs';
import { vergleichsBausteinHtml } from './bilder.mjs';
import { datumLang, domainVon, ensureDir, escHtml, fabrikPfad } from './util.mjs';

const SUCHE = {
  elektro: 'einen Elektriker',
  shk: 'einen Installateur oder Heizungsbauer',
  dachdecker: 'einen Dachdecker',
  zimmerei: 'eine Zimmerei',
  maler: 'einen Maler',
  tischler: 'eine Schreinerei',
  fliesen: 'einen Fliesenleger',
  metallbau: 'einen Metallbauer',
  galabau: 'einen Gartenbaubetrieb',
  bau: 'ein Bauunternehmen',
  allgemein: 'einen Handwerksbetrieb',
};

const istPerson = (s) => !!s && /^[A-ZÄÖÜ][\p{L}.-]+(\s+[A-ZÄÖÜ][\p{L}.-]+){1,3}$/u.test(s) && !/GmbH|Betrieb|Elektro|Maler|Bau|Haus|Service/i.test(s);

export function briefDaten(lead, cfg, { datum = new Date() } = {}) {
  const a = cfg.agentur;
  const inhaber = lead.pruefung?.extrakt?.inhaber;
  const person = cfg.brief?.anrede !== 'neutral' && istPerson(inhaber) ? inhaber : null;
  const kurz = lead.variante?.kurzname ?? lead.name;
  const domain = domainVon(lead.pruefung?.finalUrl || lead.website);
  const befunde = lead.bewertung ? briefBefunde(lead.bewertung) : [];
  const url = lead.variante?.url ?? '';
  const wochen = cfg.vorschau?.loeschenNachWochen ?? 6;
  const ozBekannt = !!lead.variante?.oeffnungszeitenBekannt;
  const suche = lead.gewerkBezeichnung ? `einen Betrieb für ${lead.gewerkBezeichnung}` : SUCHE[lead.gewerk] ?? SUCHE.allgemein;

  const aufzaehlung = (teile) => (teile.length > 1 ? `${teile.slice(0, -1).join(', ')} und ${teile.at(-1)}` : teile[0] ?? '');
  const mitDaten = aufzaehlung(['Ihren Leistungen', 'Ihrer Adresse', ...(ozBekannt ? ['Ihren Öffnungszeiten'] : [])]);
  const absaetze = [];
  let liste = [];
  const kat = lead.bewertung?.kategorie;
  if (kat === 'keine-website') {
    absaetze.push(
      `wer heute in ${lead.adresse.ort} ${suche} sucht, schaut zuerst im Internet. Bei unserer Recherche sind wir auf keine eigene Website von ${kurz} gestoßen – deshalb haben wir Ihnen einfach einen Entwurf gebaut.`,
      `Er zeigt Ihre Leistungen, Ihre Adresse${ozBekannt ? ', Ihre Öffnungszeiten' : ''} und eine Anfrage-Funktion, über die Kundinnen und Kunden ihr Vorhaben in wenigen Minuten beschreiben – auf dem Smartphone genauso wie am Computer.`,
    );
  } else if (kat === 'nicht-erreichbar') {
    absaetze.push(
      `bei unserem Test am ${datumLang(datum)} war Ihre Website ${domain} leider nicht erreichbar${lead.pruefung?.fehler ? ` (${lead.pruefung.fehler})` : ''}. Wer Sie über Google findet, landet dann auf einer Fehlerseite – und ruft im Zweifel den nächsten Betrieb an.`,
      `Damit Sie sehen, wie es besser geht, haben wir Ihnen einen Entwurf gebaut – mit ${mitDaten}.`,
    );
  } else {
    absaetze.push(`wir haben uns Ihre Website ${domain} auf dem Smartphone angesehen – so, wie es heute viele Ihrer Kundinnen und Kunden tun. Dabei ist uns aufgefallen:`);
    liste = befunde.map((b) => b.brief);
    absaetze.push(`Statt Ihnen das nur zu schreiben, haben wir einen Entwurf gebaut, wie Ihr Auftritt aussehen könnte – mit ${mitDaten}.`);
  }
  const nachQr = [
    `Der Entwurf ist kostenlos und unverbindlich. Er ist nicht über Google auffindbar und wird nach ${wochen} Wochen gelöscht, wenn Sie kein Interesse haben. Gefällt er Ihnen, passen wir Texte, Fotos und Farben gemeinsam an – danach kann die Seite in wenigen Tagen online gehen.`,
    `Ich freue mich über Ihren Anruf unter ${a.telefon} oder eine kurze Nachricht an ${a.email}.`,
  ];
  return {
    agentur: a,
    empfaenger: [lead.name, person, lead.adresse.strasse, `${lead.adresse.plz} ${lead.adresse.ort}`].filter(Boolean),
    datum: datumLang(datum),
    betreff: `Ein Website-Entwurf für ${kurz} – fertig zum Ansehen`,
    anrede: person ? `Guten Tag ${person},` : 'Sehr geehrte Damen und Herren,',
    absaetze,
    liste,
    nachQr,
    url,
    ps: lead.pruefung?.screenshot
      ? 'P. S. Auf der Rückseite sehen Sie Ihre heutige Website und den Entwurf direkt nebeneinander.'
      : 'P. S. Auf der Rückseite finden Sie einen ersten Eindruck vom Entwurf.',
    datenschutz: `Datenschutz: Ihre Geschäftsanschrift stammt aus öffentlich zugänglichen Quellen (OpenStreetMap${lead.website ? ', Ihre Website' : ''}). Wir nutzen sie einmalig, um Ihnen dieses Angebot zu schicken (Art. 6 Abs. 1 lit. f DSGVO). Sie können der Verwendung Ihrer Daten für Werbung jederzeit widersprechen (Art. 21 DSGVO) – eine kurze Nachricht an ${a.email} genügt, dann löschen wir Ihre Daten und den Entwurf.${a.datenschutzUrl ? ` Weitere Informationen: ${a.datenschutzUrl}` : ''}`,
  };
}

function briefHtml(d, qrSvg, vergleich, unterschriftDataUri) {
  const a = d.agentur;
  const e = escHtml;
  return `<!doctype html><html lang="de"><head><meta charset="utf-8"><title>${e(d.betreff)}</title>
<style>
  @page { size: A4; margin: 0; }
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; }
  body { font-family: Inter, "Helvetica Neue", Arial, sans-serif; font-size: var(--fs, 10.3pt); line-height: 1.42; color: #1a1c1f; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .seite { position: relative; width: 210mm; height: 297mm; overflow: hidden; break-after: page; }
  .seite:last-child { break-after: auto; }
  .kopf { position: absolute; top: 15mm; left: 25mm; right: 20mm; display: flex; justify-content: space-between; align-items: flex-start; }
  .marke { font-weight: 800; letter-spacing: .18em; font-size: 12.5pt; text-transform: uppercase; }
  .marke small { display: block; font-weight: 500; letter-spacing: .02em; text-transform: none; font-size: 8pt; color: #6b6f76; margin-top: 1.4mm; }
  .kopf .web { font-size: 8pt; color: #6b6f76; text-align: right; line-height: 1.5; }
  .marke-linie { position: absolute; top: 31mm; left: 25mm; width: 18mm; height: 1.2mm; background: #c9a227; }
  .falz { position: absolute; left: 0; width: 5mm; border-top: .25mm solid #9a9a9a; }
  .f1 { top: 105mm; } .f2 { top: 210mm; } .loch { top: 148.5mm; width: 7mm; }
  .adressfeld { position: absolute; top: 45mm; left: 20mm; width: 85mm; height: 45mm; }
  .ruecksende { position: absolute; top: 12.2mm; left: 5mm; font-size: 7pt; color: #555; text-decoration: underline; text-underline-offset: .6mm; white-space: nowrap; }
  .anschrift { position: absolute; top: 17.7mm; left: 5mm; right: 0; font-size: 10.5pt; line-height: 1.38; }
  .info { position: absolute; top: 50mm; left: 125mm; width: 70mm; font-size: 8.4pt; line-height: 1.45; margin: 0; }
  .info dt { color: #6b6f76; }
  .info dd { margin: 0 0 1.8mm; }
  .inhalt { position: absolute; top: 98.5mm; left: 25mm; width: 165mm; }
  .betreff { font-weight: 700; font-size: 1.08em; margin: 0 0 5.5mm; }
  p { margin: 0 0 3mm; }
  ul.befunde { margin: 0 0 3mm; padding-left: 5mm; }
  ul.befunde li { margin-bottom: 1.3mm; }
  .qrbox { display: flex; gap: 6mm; align-items: center; border: .3mm solid #ddd8cc; background: #f7f5f0; border-radius: 3mm; padding: 3.6mm 5mm; margin: 3.5mm 0 4.5mm; }
  .qrbox .qr { width: 27mm; height: 27mm; flex: none; }
  .qrbox .qr svg { width: 100%; height: 100%; display: block; }
  .qrbox .lbl { font-size: .86em; color: #6b6f76; }
  .qrbox .url { font-weight: 700; font-size: 1.05em; word-break: break-all; margin: .8mm 0 1.2mm; }
  .unterschrift { height: 13mm; margin: 1mm 0 0; }
  .unterschrift img { height: 13mm; }
  .ps { margin-top: 4mm; color: #3c3f44; }
  .fuss { position: absolute; bottom: 9mm; left: 25mm; right: 20mm; border-top: .2mm solid #cfcfcf; padding-top: 2.4mm; font-size: 7.1pt; color: #6b6f76; display: flex; justify-content: space-between; gap: 6mm; line-height: 1.45; }
  .s2 { position: absolute; top: 20mm; left: 25mm; right: 20mm; }
  .s2 h2 { font-size: 15pt; margin: 0 0 2mm; letter-spacing: -.01em; }
  .s2 .lead { color: #555; margin: 0 0 7mm; }
  .vorteile { columns: 2; column-gap: 9mm; margin: 9mm 0 0; padding-left: 4.5mm; font-size: 9.4pt; }
  .vorteile li { margin-bottom: 1.6mm; break-inside: avoid; }
  .datenschutz { position: absolute; bottom: 21mm; left: 25mm; right: 20mm; font-size: 7.1pt; color: #6b6f76; line-height: 1.45; border-top: .2mm solid #e2e2e2; padding-top: 2.4mm; }
</style></head><body>
<section class="seite">
  <span class="falz f1"></span><span class="falz loch"></span><span class="falz f2"></span>
  <header class="kopf">
    <div class="marke">${e(a.name)}<small>${e(a.claim ?? 'Webdesign')}</small></div>
    <div class="web">${e(a.website?.replace(/^https?:\/\//, '') ?? '')}<br>${e(a.telefon ?? '')}</div>
  </header>
  <span class="marke-linie"></span>
  <div class="adressfeld">
    <div class="ruecksende">${e([a.name, a.strasse, `${a.plz} ${a.ort}`].filter(Boolean).join(' · '))}</div>
    <div class="anschrift">${d.empfaenger.map(e).join('<br>')}</div>
  </div>
  <dl class="info">
    <dt>Ihr Ansprechpartner</dt><dd>${e(a.ansprechpartner ?? a.name)}</dd>
    ${a.telefon ? `<dt>Telefon</dt><dd>${e(a.telefon)}</dd>` : ''}
    ${a.email ? `<dt>E-Mail</dt><dd>${e(a.email)}</dd>` : ''}
    <dt>Datum</dt><dd>${e(d.datum)}</dd>
  </dl>
  <main class="inhalt">
    <p class="betreff">${e(d.betreff)}</p>
    <p>${e(d.anrede)}</p>
    ${d.absaetze.length ? `<p>${e(d.absaetze[0])}</p>` : ''}
    ${d.liste.length ? `<ul class="befunde">${d.liste.map((l) => `<li>${e(l)}</li>`).join('')}</ul>` : ''}
    ${d.absaetze.slice(1).map((t) => `<p>${e(t)}</p>`).join('')}
    <div class="qrbox">
      <div class="qr">${qrSvg}</div>
      <div><div class="lbl">Ihr persönlicher Entwurf</div><div class="url">${e(d.url.replace(/^https?:\/\//, ''))}</div><div class="lbl">Einfach den Code mit der Handykamera scannen.</div></div>
    </div>
    ${d.nachQr.map((t) => `<p>${e(t)}</p>`).join('')}
    <p style="margin-top:4mm">Mit freundlichen Grüßen</p>
    <div class="unterschrift">${unterschriftDataUri ? `<img src="${unterschriftDataUri}" alt="">` : ''}</div>
    <p>${e(a.ansprechpartner ?? '')}<br>${e(a.name)}</p>
    <p class="ps">${e(d.ps)}</p>
  </main>
  <footer class="fuss">
    <div>${e(a.name)}<br>${e(a.strasse ?? '')}, ${e(`${a.plz ?? ''} ${a.ort ?? ''}`)}</div>
    <div>${e(a.telefon ?? '')}<br>${e(a.email ?? '')}</div>
    <div style="text-align:right">${e(a.website?.replace(/^https?:\/\//, '') ?? '')}${a.ustId ? `<br>USt-IdNr. ${e(a.ustId)}` : ''}</div>
  </footer>
</section>
<section class="seite">
  <div class="s2">
    <h2>Ihr Auftritt heute – und wie er aussehen könnte</h2>
    <p class="lead">Beide Ansichten so, wie sie auf einem Smartphone erscheinen. Den vollständigen Entwurf öffnen Sie über den QR-Code auf der Vorderseite.</p>
    ${vergleich}
    <ul class="vorteile">
      <li>Anrufen mit einem Fingertipp – auf jeder Seite</li>
      <li>Öffnungszeiten mit Live-Status („Jetzt geöffnet“)</li>
      <li>Anfrage-Assistent: Ihre Kundschaft beschreibt ihr Vorhaben in wenigen Minuten</li>
      <li>Einsatzgebiet mit Postleitzahl-Prüfung</li>
      <li>Schnell, ohne Cookie-Banner und ohne Google-Fonts</li>
      <li>Für Google aufbereitet: Leistungen und Ort sauber ausgezeichnet</li>
    </ul>
  </div>
  <p class="datenschutz">${e(d.datenschutz)}</p>
  <footer class="fuss">
    <div>${e(a.name)} · ${e(a.ansprechpartner ?? '')}</div>
    <div style="text-align:right">${e(a.telefon ?? '')} · ${e(a.email ?? '')}</div>
  </footer>
</section>
</body></html>`;
}

export async function erzeugeBrief(browser, lead, cfg, laufDir, opts = {}) {
  const QRCode = (await import('qrcode')).default;
  ensureDir(join(laufDir, 'briefe'));
  const d = briefDaten(lead, cfg, opts);
  if (!d.url) throw new Error(`Für ${lead.name} gibt es noch keine Vorschau-Adresse.`);
  const qrSvg = await QRCode.toString(d.url, { type: 'svg', margin: 0, errorCorrectionLevel: 'M', color: { dark: '#15171aff', light: '#ffffff00' } });
  const vergleich = vergleichsBausteinHtml(lead, laufDir, { breiteMm: 58 });
  const sig = cfg.brief?.unterschrift ? fabrikPfad(cfg.brief.unterschrift) : null;
  const sigUri = sig && existsSync(sig) ? `data:image/png;base64,${readFileSync(sig).toString('base64')}` : null;
  const htmlFile = join(laufDir, 'briefe', `${lead.slug}.html`);
  writeFileSync(htmlFile, briefHtml(d, qrSvg, vergleich, sigUri));

  const ctx = await browser.newContext();
  const page = await ctx.newPage();
  await page.emulateMedia({ media: 'print' });
  await page.goto(pathToFileURL(htmlFile).href, { waitUntil: 'load' });
  // Passt der Text auf Seite 1? Sonst Schrift schrittweise verkleinern.
  let fs = 10.3;
  for (let i = 0; i < 5; i++) {
    const zuLang = await page.evaluate(() => {
      const inhalt = document.querySelector('.inhalt').getBoundingClientRect();
      const fuss = document.querySelector('.seite .fuss').getBoundingClientRect();
      return inhalt.bottom > fuss.top - 6;
    });
    if (!zuLang) break;
    fs -= 0.3;
    await page.evaluate((v) => document.documentElement.style.setProperty('--fs', `${v}pt`), fs);
  }
  const pdf = `briefe/${lead.slug}.pdf`;
  await page.pdf({ path: join(laufDir, pdf), format: 'A4', printBackground: true, preferCSSPageSize: true });
  await ctx.close();
  return { pdf, html: `briefe/${lead.slug}.html`, schriftgroesse: fs };
}

export async function sammelPdf(laufDir, dateien) {
  const { PDFDocument } = await import('pdf-lib');
  const out = await PDFDocument.create();
  for (const f of dateien) {
    const src = await PDFDocument.load(readFileSync(join(laufDir, f)));
    for (const p of await out.copyPages(src, src.getPageIndices())) out.addPage(p);
  }
  const file = 'briefe/alle-briefe.pdf';
  writeFileSync(join(laufDir, file), await out.save());
  return file;
}

export function adressCsv(laufDir, leads) {
  const q = (s) => `"${String(s ?? '').replace(/"/g, '""')}"`;
  const zeilen = [['Firma', 'Ansprechpartner', 'Straße', 'PLZ', 'Ort', 'Vorschau', 'Brief'].map(q).join(';')];
  for (const l of leads) {
    zeilen.push([l.name, l.pruefung?.extrakt?.inhaber ?? '', l.adresse.strasse, l.adresse.plz, l.adresse.ort, l.variante?.url ?? '', l.brief?.pdf ?? ''].map(q).join(';'));
  }
  const file = 'briefe/adressen.csv';
  writeFileSync(join(laufDir, file), '﻿' + zeilen.join('\r\n') + '\r\n');
  return file;
}
