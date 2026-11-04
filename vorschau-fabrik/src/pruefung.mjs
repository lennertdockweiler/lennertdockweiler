// Website-Check mit Playwright (Smartphone-Ansicht): Erreichbarkeit, HTTPS, Mobiltauglichkeit,
// Ladezeit, Aktualität, Impressum – plus Text-Auszüge und Markenfarben für die Vorschau.
import { join } from 'node:path';
import { extrahiere } from './extraktion.mjs';
import { ensureDir, writeJson } from './util.mjs';

const MOBIL = {
  viewport: { width: 390, height: 844 },
  deviceScaleFactor: 2,
  isMobile: true,
  hasTouch: true,
  locale: 'de-DE',
  timezoneId: 'Europe/Berlin',
  userAgent:
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1',
};

const COOKIE_TEXTE = /^(alle\s+)?(akzeptieren|annehmen|zustimmen|einverstanden|verstanden|ok|okay|alle cookies akzeptieren|accept( all)?|allow all|ich stimme zu|zulassen)$/i;

async function cookieBannerWeg(page) {
  try {
    const knoepfe = page.locator('button, a[role="button"], [role="button"], input[type="button"], input[type="submit"]');
    const n = Math.min(await knoepfe.count(), 60);
    for (let i = 0; i < n; i++) {
      const k = knoepfe.nth(i);
      const text = ((await k.innerText({ timeout: 300 }).catch(() => '')) || (await k.getAttribute('value').catch(() => '')) || '').trim();
      if (text && text.length < 40 && COOKIE_TEXTE.test(text) && (await k.isVisible().catch(() => false))) {
        await k.click({ timeout: 1500 }).catch(() => {});
        await page.waitForTimeout(600);
        return true;
      }
    }
  } catch {}
  return false;
}

/** Läuft im Browser: Kennzahlen der Seite */
function seitenAnalyse() {
  const txt = document.body?.innerText ?? '';
  const meta = (n) => document.querySelector(`meta[name="${n}"]`)?.getAttribute('content') ?? null;
  const links = [...document.querySelectorAll('a[href]')];
  const finde = (re) => links.find((a) => re.test(a.textContent ?? '') || re.test(a.getAttribute('href') ?? ''));
  const impressum = finde(/impressum|imprint/i);
  const datenschutz = finde(/datenschutz|privacy/i);
  const ueber = links.find((a) => /^(über uns|ueber uns|unternehmen|firma|wir über uns|geschichte|team|wir)$/i.test((a.textContent ?? '').trim()));

  // kleine Schrift (Anteil Textzeichen unter 12 px)
  let klein = 0;
  let gesamt = 0;
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let node;
  let zaehler = 0;
  while ((node = walker.nextNode()) && zaehler < 3000) {
    zaehler++;
    const t = node.textContent.trim();
    if (t.length < 3 || !node.parentElement) continue;
    const cs = getComputedStyle(node.parentElement);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    const fs = parseFloat(cs.fontSize);
    gesamt += t.length;
    if (fs < 12) klein += t.length;
  }

  // Copyright-Jahr (jüngstes Jahr hinter ©/Copyright)
  const jahre = [...txt.matchAll(/(?:©|\(c\)|copyright)\s*(?:\d{4}\s*[-–]\s*)?((?:19|20)\d\d)/gi)].map((m) => Number(m[1]));

  // Markenfarben aus Kopfbereich, Buttons, Links, Überschriften
  const parse = (c) => {
    const m = /rgba?\(([^)]+)\)/.exec(c ?? '');
    if (!m) return null;
    const [r, g, b, a = 1] = m[1].split(',').map((x) => parseFloat(x));
    return a < 0.6 ? null : [r, g, b];
  };
  const hsl = ([r, g, b]) => {
    r /= 255; g /= 255; b /= 255;
    const max = Math.max(r, g, b), min = Math.min(r, g, b);
    const l = (max + min) / 2;
    const d = max - min;
    const s = d === 0 ? 0 : d / (1 - Math.abs(2 * l - 1));
    let h = 0;
    if (d) h = max === r ? ((g - b) / d) % 6 : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
    return [(h * 60 + 360) % 360, s, l];
  };
  const hex = (rgb) => '#' + rgb.map((v) => Math.round(v).toString(16).padStart(2, '0')).join('').toUpperCase();
  const punkte = new Map();
  const add = (c, w) => {
    const rgb = parse(c);
    if (!rgb) return;
    const [h, s, l] = hsl(rgb);
    if (s < 0.2 || l < 0.12 || l > 0.88) return;
    const k = hex(rgb);
    const e = punkte.get(k) ?? { hex: k, h, s, l, w: 0 };
    e.w += w;
    punkte.set(k, e);
  };
  const theme = meta('theme-color');
  if (theme) {
    const probe = document.createElement('div');
    probe.style.color = theme;
    document.body.appendChild(probe);
    add(getComputedStyle(probe).color, 25);
    probe.remove();
  }
  const els = document.querySelectorAll('header, nav, [class*="header"], [id*="header"], button, .btn, .button, [class*="btn"], [class*="button"], a, h1, h2, h3, footer');
  for (const el of [...els].slice(0, 500)) {
    const cs = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    const flaeche = Math.min(r.width * r.height, 120000) / 6000;
    add(cs.backgroundColor, 1 + flaeche);
    add(cs.color, el.tagName === 'A' ? 1.2 : 1.6);
  }
  const farben = [...punkte.values()].sort((a, b) => b.w - a.w).slice(0, 6);

  return {
    titel: document.title?.trim() || null,
    metaBeschreibung: meta('description'),
    viewportMeta: meta('viewport'),
    generator: meta('generator'),
    overflowPx: Math.max(0, document.documentElement.scrollWidth - window.innerWidth),
    kleineSchriftAnteil: gesamt ? Math.round((klein / gesamt) * 100) / 100 : 0,
    copyrightJahr: jahre.length ? Math.max(...jahre) : null,
    jquery: window.jQuery?.fn?.jquery ?? null,
    telLink: !!document.querySelector('a[href^="tel:"]'),
    telefonSichtbar: /(?:\+49|\b0)\s?\(?\d{2,5}\)?[\s/-]?\d[\d\s/-]{4,}\d/.test(txt),
    impressumImHtml: /impressum|imprint/i.test(document.documentElement.innerHTML),
    textLaenge: txt.length,
    googleMapsIframe: !!document.querySelector('iframe[src*="google.com/maps"], iframe[src*="maps.google"]'),
    impressumHref: impressum?.href ?? null,
    datenschutzLink: !!datenschutz,
    ueberUnsHref: ueber?.href ?? null,
    wordpress: !!document.querySelector('link[href*="wp-content"], script[src*="wp-content"], script[src*="wp-includes"]'),
    baukasten: /jimdo|wix\.com|websitebuilder|mywebsite|strato-website|weebly|squarespace|site123|webnode/i.test(document.documentElement.innerHTML.slice(0, 200000)),
    farben,
    text: txt.slice(0, 20000),
  };
}

async function textVon(context, href) {
  if (!href) return '';
  const p = await context.newPage();
  try {
    await p.goto(href, { waitUntil: 'domcontentloaded', timeout: 20000 });
    await p.waitForTimeout(500);
    return (await p.evaluate(() => document.body?.innerText ?? '')).slice(0, 14000);
  } catch {
    return '';
  } finally {
    await p.close().catch(() => {});
  }
}

function markenfarben(farben) {
  if (!farben?.length) return undefined;
  const primaer = farben[0];
  const hueDist = (a, b) => Math.min(Math.abs(a.h - b.h), 360 - Math.abs(a.h - b.h));
  const akzent = farben.slice(1).find((f) => hueDist(f, primaer) > 35 && f.w > primaer.w * 0.15);
  return { primaer: primaer.hex, ...(akzent ? { akzent: akzent.hex } : {}) };
}

/**
 * Prüft die Website eines Leads. Schreibt Screenshot und Text-Auszug in den Laufordner.
 * @returns Prüfergebnis (ohne Bewertung)
 */
export async function pruefeWebsite(browser, lead, laufDir) {
  const ergebnis = { url: lead.website, zeitpunkt: new Date().toISOString() };
  if (!lead.website) return { ...ergebnis, keineWebsite: true };

  ensureDir(join(laufDir, 'screens'));
  ensureDir(join(laufDir, 'texte'));
  let context;
  let page;
  let bytes = 0;
  let googleFonts = false;
  const versuche = [{ url: lead.website, ignoreHTTPSErrors: false }];
  if (lead.website.startsWith('https://')) versuche.push({ url: lead.website.replace(/^https:/, 'http:'), ignoreHTTPSErrors: false });
  versuche.push({ url: lead.website, ignoreHTTPSErrors: true, ssl: true });

  let response = null;
  let fehler = null;
  let t0 = 0;
  for (const v of versuche) {
    await context?.close().catch(() => {});
    context = await browser.newContext({ ...MOBIL, ignoreHTTPSErrors: v.ignoreHTTPSErrors });
    page = await context.newPage();
    bytes = 0;
    page.on('requestfinished', async (req) => {
      if (/fonts\.(googleapis|gstatic)\.com/.test(req.url())) googleFonts = true;
      try {
        const s = await req.sizes();
        bytes += s.responseBodySize + s.responseHeadersSize;
      } catch {}
    });
    page.on('request', (req) => {
      if (/fonts\.(googleapis|gstatic)\.com/.test(req.url())) googleFonts = true;
    });
    t0 = Date.now();
    try {
      response = await page.goto(v.url, { waitUntil: 'load', timeout: 35000 });
      fehler = null;
      if (v.ssl) ergebnis.sslFehler = true;
      break;
    } catch (e) {
      fehler = String(e.message || e).split('\n')[0];
      if (/ERR_CERT|SSL|certificate/i.test(fehler) && !v.ignoreHTTPSErrors) ergebnis.sslFehlerMeldung = fehler;
    }
  }

  if (!response) {
    await context?.close().catch(() => {});
    const kurz = /ERR_NAME_NOT_RESOLVED/.test(fehler) ? 'Adresse nicht gefunden' : /TIMED_OUT|Timeout/i.test(fehler) ? 'Zeitüberschreitung' : /ERR_CONNECTION_REFUSED/.test(fehler) ? 'Verbindung abgelehnt' : 'nicht erreichbar';
    return { ...ergebnis, erreichbar: false, fehler: kurz, fehlerDetail: fehler };
  }

  const ladezeitMs = Date.now() - t0;
  await page.waitForTimeout(1500);
  const status = response.status();
  const finalUrl = page.url();
  // Erst Einwilligungs-Banner schließen – manche Seiten zeigen ihren Inhalt erst danach
  if (await cookieBannerWeg(page)) await page.waitForTimeout(1200);
  const analyse = await page.evaluate(seitenAnalyse).catch((e) => ({ fehler: String(e) }));
  await page.evaluate(() => scrollTo(0, 0)).catch(() => {});
  const screenshot = `screens/${lead.slug}-vorher.png`;
  await page.screenshot({ path: join(laufDir, screenshot), timeout: 15000 }).catch(() => {});

  const impressumText = await textVon(context, analyse.impressumHref);
  const ueberUnsText = await textVon(context, analyse.ueberUnsHref);
  await context.close().catch(() => {});

  const texte = { url: finalUrl, start: analyse.text ?? '', impressum: impressumText, ueberUns: ueberUnsText };
  writeJson(join(laufDir, 'texte', `${lead.slug}.json`), texte);

  return {
    ...ergebnis,
    erreichbar: status < 400,
    status,
    fehler: status >= 400 ? `HTTP ${status}` : undefined,
    finalUrl,
    https: finalUrl.startsWith('https://') && !ergebnis.sslFehler,
    ladezeitMs,
    megabytes: Math.round((bytes / 1024 / 1024) * 10) / 10,
    googleFonts,
    titel: analyse.titel,
    metaBeschreibung: !!analyse.metaBeschreibung,
    viewportMeta: !!analyse.viewportMeta && /width\s*=\s*device-width/i.test(analyse.viewportMeta),
    overflowPx: analyse.overflowPx,
    kleineSchriftAnteil: analyse.kleineSchriftAnteil,
    copyrightJahr: analyse.copyrightJahr,
    generator: analyse.generator,
    wordpress: analyse.wordpress,
    baukasten: analyse.baukasten,
    jquery: analyse.jquery,
    telLink: analyse.telLink,
    telefonSichtbar: analyse.telefonSichtbar,
    impressumImHtml: analyse.impressumImHtml,
    textLaenge: analyse.textLaenge,
    googleMapsIframe: analyse.googleMapsIframe,
    impressumLink: !!analyse.impressumHref,
    datenschutzLink: analyse.datenschutzLink,
    farben: markenfarben(analyse.farben),
    extrakt: extrahiere(texte),
    screenshot,
  };
}
