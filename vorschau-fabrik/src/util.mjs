// Kleine Hilfsfunktionen für die Vorschau-Fabrik (keine externen Abhängigkeiten).
import { existsSync, mkdirSync, readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, isAbsolute, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export const FABRIK_DIR = resolve(dirname(fileURLToPath(import.meta.url)), '..');
export const AUSGABE_DIR = join(FABRIK_DIR, 'ausgabe');

export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const UMLAUTE = { ä: 'ae', ö: 'oe', ü: 'ue', ß: 'ss', Ä: 'ae', Ö: 'oe', Ü: 'ue', é: 'e', è: 'e', á: 'a', à: 'a', ç: 'c' };

/** „Müller & Söhne GmbH“ → „mueller-soehne-gmbh“ */
export function slugify(text, maxLen = 48) {
  const s = String(text ?? '')
    .replace(/[äöüßÄÖÜéèáàç]/g, (c) => UMLAUTE[c] ?? c)
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/&/g, ' ')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
  if (s.length <= maxLen) return s;
  const cut = s.slice(0, maxLen);
  return cut.includes('-') ? cut.slice(0, cut.lastIndexOf('-')) : cut;
}

/** Vergleichsschlüssel für Namen (Dubletten, Sperrliste) */
export const normName = (s) => slugify(s, 200).replace(/-(gmbh|ug|kg|ohg|ek|gbr|mbh|co|inh)\b/g, '').replace(/-+/g, '-');

export function readJson(file, fallback = undefined) {
  try {
    return JSON.parse(readFileSync(file, 'utf8'));
  } catch (e) {
    if (fallback !== undefined) return fallback;
    throw e;
  }
}

export function writeJson(file, data) {
  mkdirSync(dirname(file), { recursive: true });
  writeFileSync(file, JSON.stringify(data, null, 2) + '\n');
}

export function ensureDir(dir) {
  mkdirSync(dir, { recursive: true });
  return dir;
}

/** Pfad relativ zum Fabrik-Ordner auflösen (absolute Pfade bleiben) */
export const fabrikPfad = (p) => (isAbsolute(p) ? p : resolve(FABRIK_DIR, p));

/** Konfiguration laden: fabrik.config.json, Umgebungsvariablen überschreiben den Template-Pfad */
export function ladeKonfig() {
  const file = join(FABRIK_DIR, 'fabrik.config.json');
  if (!existsSync(file)) throw new Error('fabrik.config.json fehlt – Vorlage: fabrik.config.beispiel.json');
  const cfg = readJson(file);
  cfg.template ??= {};
  cfg.template.pfad = fabrikPfad(process.env.FABRIK_TEMPLATE || cfg.template.pfad || '../../handwerker-template');
  cfg.vorschau ??= {};
  cfg.brief ??= {};
  cfg.sperrliste = fabrikPfad(cfg.sperrliste || './sperrliste.txt');
  return cfg;
}

/** Laufordner: ausgabe/<lauf>/ ; ohne Angabe der zuletzt geänderte Lauf */
export function laufOrdner(lauf) {
  if (lauf) return join(AUSGABE_DIR, lauf);
  if (!existsSync(AUSGABE_DIR)) throw new Error('Noch kein Lauf vorhanden – zuerst: fabrik leads --ort … --gewerk …');
  const laeufe = readdirSync(AUSGABE_DIR)
    .map((n) => join(AUSGABE_DIR, n))
    .filter((p) => existsSync(join(p, 'lauf.json')))
    .sort((a, b) => statSync(join(b, 'lauf.json')).mtimeMs - statSync(join(a, 'lauf.json')).mtimeMs);
  if (!laeufe.length) throw new Error('Noch kein Lauf vorhanden – zuerst: fabrik leads --ort … --gewerk …');
  return laeufe[0];
}

export const ladeLeads = (dir) => readJson(join(dir, 'leads.json'), []);
export const speichereLeads = (dir, leads) => writeJson(join(dir, 'leads.json'), leads);

/** fetch mit Timeout und Wiederholungen (für Overpass/Nominatim) */
export async function fetchMitRetry(url, opts = {}, { versuche = 3, timeoutMs = 60000 } = {}) {
  let letzterFehler;
  for (let i = 0; i < versuche; i++) {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), timeoutMs);
    try {
      const res = await fetch(url, { ...opts, signal: ctrl.signal });
      clearTimeout(t);
      if (res.status === 429 || res.status >= 500) throw new Error(`HTTP ${res.status}`);
      return res;
    } catch (e) {
      clearTimeout(t);
      letzterFehler = e;
      await sleep(1500 * (i + 1));
    }
  }
  throw letzterFehler;
}

/** Playwright laden: lokale Installation oder global vorinstallierte (NODE_PATH) */
export function ladePlaywright() {
  const require = createRequire(join(FABRIK_DIR, 'package.json'));
  try {
    return require('playwright');
  } catch {
    throw new Error('Playwright fehlt: im Ordner vorschau-fabrik „npm install playwright“ und „npx playwright install chromium“ ausführen.');
  }
}

/** Chromium starten; fällt bei Versionskonflikt auf vorinstallierte Browser zurück */
export async function starteBrowser() {
  const { chromium } = ladePlaywright();
  const pfade = [process.env.CHROMIUM_PATH, '/opt/pw-browsers/chromium'].filter(Boolean);
  try {
    return await chromium.launch();
  } catch (e) {
    for (const p of pfade) {
      if (existsSync(p)) return chromium.launch({ executablePath: p });
    }
    throw e;
  }
}

/** Einfache Parallelisierung mit Obergrenze */
export async function parallel(items, limit, fn) {
  const results = new Array(items.length);
  let next = 0;
  const workers = Array.from({ length: Math.min(limit, items.length) }, async () => {
    while (next < items.length) {
      const i = next++;
      results[i] = await fn(items[i], i);
    }
  });
  await Promise.all(workers);
  return results;
}

export const log = (...a) => console.log(...a);
export const farbe = {
  gruen: (s) => `\x1b[32m${s}\x1b[0m`,
  gelb: (s) => `\x1b[33m${s}\x1b[0m`,
  rot: (s) => `\x1b[31m${s}\x1b[0m`,
  grau: (s) => `\x1b[2m${s}\x1b[0m`,
  fett: (s) => `\x1b[1m${s}\x1b[0m`,
};

/** Datum als „4. November 2026“ */
export const datumLang = (d = new Date()) =>
  new Intl.DateTimeFormat('de-DE', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'Europe/Berlin' }).format(d);

export const escHtml = (s) =>
  String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);

/** Telefonnummer in das Template-Format „+49 7531 123456“ bringen */
export function normTelefon(raw) {
  if (!raw) return undefined;
  let s = String(raw).split(/[;,]/)[0].trim();
  s = s.replace(/[^\d+()/ -]/g, '').replace(/\(0\)/g, '').replace(/\s+/g, ' ').trim();
  if (/^00/.test(s)) s = '+' + s.slice(2);
  if (/^0[1-9]/.test(s)) s = '+49 ' + s.slice(1);
  s = s.replace(/^\+49\s*0/, '+49 ');
  if (/^\+49\d/.test(s)) s = '+49 ' + s.slice(3);
  s = s.replace(/[()]/g, '').replace(/\s*\/\s*/g, ' ').replace(/\s*-\s*/g, ' ').replace(/\s+/g, ' ').trim();
  return /^\+?[0-9 ()/-]{6,}$/.test(s) ? s : undefined;
}

export const domainVon = (url) => {
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return undefined;
  }
};
