// Anbindung an das handwerker-template: Infos lesen, Varianten schreiben, prüfen, bauen, servieren.
import { spawnSync } from 'node:child_process';
import { createServer } from 'node:http';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { readFile, stat } from 'node:fs/promises';
import { extname, join } from 'node:path';
import { FABRIK_DIR, readJson } from './util.mjs';

let cache = null;

export function pruefeTemplate(pfad) {
  if (!existsSync(join(pfad, 'variants/_schema.ts'))) {
    throw new Error(`handwerker-template nicht gefunden unter ${pfad}. Pfad in fabrik.config.json (template.pfad) oder FABRIK_TEMPLATE setzen.`);
  }
  if (!existsSync(join(pfad, 'node_modules/astro'))) {
    throw new Error(`Im Template fehlen die Abhängigkeiten. Einmalig ausführen:\n  cd ${pfad} && npm ci`);
  }
}

/** Gewerk-Presets, Texte, Veröffentlichungs-Einstellungen (via tsx aus dem Template gelesen) */
export function templateInfo(pfad) {
  if (cache?.pfad === pfad) return cache.info;
  pruefeTemplate(pfad);
  const r = spawnSync('node', ['--import', 'tsx', join(FABRIK_DIR, 'src/template-dump.mts'), pfad], { cwd: pfad, encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 });
  if (r.status !== 0) throw new Error(`Template-Infos nicht lesbar:\n${r.stderr}`);
  const info = JSON.parse(r.stdout);
  cache = { pfad, info };
  return info;
}

const variantDir = (pfad, slug) => join(pfad, 'variants', slug);

/** Gehört der Ordner einer Variante der Fabrik (oder ist er frei)? */
export function variantFrei(pfad, slug) {
  const file = join(variantDir(pfad, slug), 'site.config.json');
  if (!existsSync(file)) return true;
  return !!readJson(file, {})['//fabrik'];
}

export function schreibeVariante(pfad, slug, config, credits) {
  const dir = variantDir(pfad, slug);
  mkdirSync(join(dir, 'assets'), { recursive: true });
  writeFileSync(join(dir, 'site.config.json'), JSON.stringify(config, null, 2) + '\n');
  if (credits) writeFileSync(join(dir, 'CREDITS.md'), credits);
}

/** variant:check des Templates: liefert Fehler und Hinweise */
export function pruefeVariante(pfad, slug) {
  const r = spawnSync('node', ['--import', 'tsx', 'scripts/check-variant.mjs', slug], { cwd: pfad, encoding: 'utf8', env: { ...process.env, NO_COLOR: '1' } });
  const text = (r.stdout + r.stderr).replace(/\x1b\[[0-9;]*m/g, '');
  const punkte = (titel) => {
    const block = text.split(titel)[1]?.split(/\n[✖▲✔]/)[0] ?? '';
    return block.split('\n').map((l) => l.replace(/^\s*•\s*/, '').trim()).filter(Boolean).filter((l) => !/^\d+ (Fehler|Hinweis)/.test(l));
  };
  return {
    ok: r.status === 0,
    fehler: /✖ \d+ Fehler/.test(text) ? punkte(/✖ \d+ Fehler:/) : [],
    hinweise: /▲ \d+ Hinweis/.test(text) ? punkte(/▲ \d+ Hinweis\(e\):/) : [],
    ausgabe: text.trim(),
  };
}

/** Variante nach dist/<slug>/ bauen (Basis-Pfad /) */
export function baueVariante(pfad, slug) {
  const t0 = Date.now();
  const r = spawnSync('npx', ['astro', 'build'], {
    cwd: pfad,
    encoding: 'utf8',
    env: { ...process.env, VARIANT: slug, OUT_DIR: `./dist/${slug}`, ASTRO_TELEMETRY_DISABLED: '1' },
    maxBuffer: 256 * 1024 * 1024,
  });
  return { ok: r.status === 0, sekunden: Math.round((Date.now() - t0) / 1000), log: (r.stdout + r.stderr).split('\n').slice(-25).join('\n'), dist: join(pfad, 'dist', slug) };
}

/** Öffentliche Adresse einer Variante laut veroeffentlichen.config.json */
export function vorschauUrl(info, slug) {
  const v = info.veroeffentlichen;
  if (!v?.url) return null;
  const pfad = v.pfade?.[slug] ?? slug;
  return `${v.url.replace(/\/$/, '')}/${pfad}/`;
}

/** Veröffentlichen über das Publish-Skript des Templates (pusht ins öffentliche Repo) */
export function veroeffentliche(pfad, slugs) {
  const r = spawnSync('npm', ['run', 'publish', '--', ...slugs], { cwd: pfad, stdio: 'inherit', env: { ...process.env, ASTRO_TELEMETRY_DISABLED: '1' } });
  return r.status === 0;
}

const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg', '.webp': 'image/webp', '.avif': 'image/avif', '.woff2': 'font/woff2', '.json': 'application/json', '.txt': 'text/plain', '.xml': 'application/xml' };

/** Minimaler statischer Server für gebaute Varianten */
export function serve(dir) {
  return new Promise((resolve) => {
    const server = createServer(async (req, res) => {
      const url = decodeURIComponent((req.url ?? '/').split('?')[0]);
      let file = join(dir, url);
      try {
        if ((await stat(file)).isDirectory()) file = join(file, 'index.html');
        const body = await readFile(file);
        res.writeHead(200, { 'Content-Type': TYPES[extname(file)] ?? 'application/octet-stream' });
        res.end(body);
      } catch {
        res.writeHead(404, { 'Content-Type': 'text/html; charset=utf-8' });
        res.end(await readFile(join(dir, '404.html')).catch(() => 'Not found'));
      }
    });
    server.listen(0, '127.0.0.1', () => resolve({ server, url: `http://127.0.0.1:${server.address().port}` }));
  });
}

export const leseVeroeffentlichenConfig = (pfad) => readJson(join(pfad, 'veroeffentlichen.config.json'), null);
export const leseDatei = (p) => readFileSync(p, 'utf8');
