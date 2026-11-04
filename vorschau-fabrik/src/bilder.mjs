// Screenshots der gebauten Vorschau und Vorher/Nachher-Vergleichsbild.
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { serve } from './template.mjs';
import { domainVon, ensureDir, escHtml } from './util.mjs';

const SUCHBEGRIFF = { elektro: 'Elektriker', shk: 'Heizung Sanitär', dachdecker: 'Dachdecker', zimmerei: 'Zimmerei', tischler: 'Schreinerei', maler: 'Maler', fliesen: 'Fliesenleger', metallbau: 'Metallbau', galabau: 'Gartenbau', bau: 'Bauunternehmen' };

const MOBIL = { viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true, locale: 'de-DE', timezoneId: 'Europe/Berlin' };

export async function vorschauScreenshots(browser, lead, distDir, laufDir) {
  ensureDir(join(laufDir, 'screens'));
  const { server, url } = await serve(distDir);
  const out = {};
  try {
    const ctx = await browser.newContext(MOBIL);
    const page = await ctx.newPage();
    const fehler = [];
    page.on('pageerror', (e) => fehler.push(e.message));
    await page.goto(`${url}/?static`, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(700);
    out.nachher = `screens/${lead.slug}-nachher.png`;
    await page.screenshot({ path: join(laufDir, out.nachher) });
    out.overflowPx = await page.evaluate(() => document.documentElement.scrollWidth - innerWidth);
    out.nachherLang = `screens/${lead.slug}-nachher-lang.png`;
    await page.screenshot({ path: join(laufDir, out.nachherLang), fullPage: true });
    out.jsFehler = fehler;
    await ctx.close();

    const ctxD = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1, locale: 'de-DE', timezoneId: 'Europe/Berlin' });
    const pd = await ctxD.newPage();
    await pd.goto(`${url}/?static`, { waitUntil: 'networkidle', timeout: 30000 });
    await pd.waitForTimeout(500);
    out.nachherDesktop = `screens/${lead.slug}-nachher-desktop.png`;
    await pd.screenshot({ path: join(laufDir, out.nachherDesktop) });
    await ctxD.close();
  } finally {
    server.close();
  }
  return out;
}

export const dataUri = (file) => (file && existsSync(file) ? `data:image/png;base64,${readFileSync(file).toString('base64')}` : null);

/** HTML-Baustein: zwei Smartphones nebeneinander (für Vergleichsbild und Brief, Seite 2) */
export function vergleichsBausteinHtml(lead, laufDir, { breiteMm } = {}) {
  const vorher = lead.pruefung?.screenshot ? dataUri(join(laufDir, lead.pruefung.screenshot)) : null;
  const nachher = lead.bilder?.nachher ? dataUri(join(laufDir, lead.bilder.nachher)) : null;
  const domain = domainVon(lead.pruefung?.finalUrl || lead.website);
  const einheit = breiteMm ? 'mm' : 'px';
  const w = breiteMm ?? 330;
  const leer = !lead.website
    ? `<div class="vg-leer"><strong>Heute</strong><span>Keine eigene Website gefunden.</span><small>Wer „${escHtml(lead.gewerkBezeichnung ?? SUCHBEGRIFF[lead.gewerk] ?? 'Handwerker')} ${escHtml(lead.adresse.ort)}“ sucht, findet bisher keine eigene Seite von ${escHtml(lead.variante?.kurzname ?? lead.name)}.</small></div>`
    : `<div class="vg-leer"><strong>Heute</strong><span>Website nicht erreichbar.</span><small>${escHtml(domain ?? '')}${lead.pruefung?.fehler ? ` – ${escHtml(lead.pruefung.fehler)}` : ''}</small></div>`;
  return `
<style>
  .vg { display:flex; gap:${breiteMm ? 12 : 56}${einheit}; justify-content:center; align-items:flex-start; }
  .vg figure { margin:0; width:${w / (breiteMm ? 1 : 1)}${einheit}; }
  .vg .phone { border:${breiteMm ? 2.2 : 11}${einheit} solid #15171a; border-radius:${breiteMm ? 9 : 44}${einheit}; overflow:hidden; background:#fff; box-shadow:0 ${breiteMm ? 2 : 18}${einheit} ${breiteMm ? 6 : 40}${einheit} rgba(0,0,0,.18); aspect-ratio:390/844; }
  .vg .phone img { width:100%; height:100%; object-fit:cover; object-position:top; display:block; }
  .vg figcaption { text-align:center; margin-top:${breiteMm ? 3 : 18}${einheit}; font-weight:600; font-size:${breiteMm ? '9.5pt' : '22px'}; }
  .vg figcaption small { display:block; font-weight:400; opacity:.65; font-size:${breiteMm ? '8pt' : '16px'}; margin-top:2px; }
  .vg-leer { height:100%; display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center; gap:${breiteMm ? 2 : 10}${einheit}; padding:${breiteMm ? 6 : 28}${einheit}; background:repeating-linear-gradient(135deg,#f3f3f3 0 12px,#ececec 12px 24px); color:#444; }
  .vg-leer strong { font-size:${breiteMm ? '11pt' : '26px'}; }
  .vg-leer span { font-size:${breiteMm ? '10pt' : '22px'}; }
  .vg-leer small { font-size:${breiteMm ? '8pt' : '16px'}; opacity:.75; }
</style>
<div class="vg">
  <figure><div class="phone">${vorher ? `<img src="${vorher}" alt="">` : leer}</div><figcaption>Ihre Website heute<small>${escHtml(domain ?? 'keine Website')}</small></figcaption></figure>
  <figure><div class="phone">${nachher ? `<img src="${nachher}" alt="">` : ''}</div><figcaption>Ihr Entwurf<small>so könnte es aussehen</small></figcaption></figure>
</div>`;
}

export async function vergleichsBild(browser, lead, laufDir) {
  ensureDir(join(laufDir, 'vergleich'));
  const ctx = await browser.newContext({ viewport: { width: 1000, height: 900 }, deviceScaleFactor: 2 });
  const page = await ctx.newPage();
  await page.setContent(
    `<!doctype html><html lang="de"><head><meta charset="utf-8"><style>body{margin:0;padding:48px 40px;background:#f6f5f2;font-family:Inter,system-ui,sans-serif;color:#15171a}h1{margin:0 0 36px;text-align:center;font-size:30px;letter-spacing:-.01em}</style></head><body><h1>${escHtml(lead.name)}</h1>${vergleichsBausteinHtml(lead, laufDir)}</body></html>`,
    { waitUntil: 'load' },
  );
  const file = `vergleich/${lead.slug}.png`;
  await page.screenshot({ path: join(laufDir, file), fullPage: true });
  await ctx.close();
  return file;
}
