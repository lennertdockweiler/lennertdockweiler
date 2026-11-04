#!/usr/bin/env node
// Vorschau-Fabrik: vom Lead zur fertigen Demo-Website und zum Brief.
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { bewerte } from './bewertung.mjs';
import { vergleichsBild, vorschauScreenshots } from './bilder.mjs';
import { adressCsv, erzeugeBrief, sammelPdf } from './brief.mjs';
import { schreibeBericht } from './bericht.mjs';
import { kurznameAus } from './extraktion.mjs';
import { parseOeffnungszeiten } from './oeffnungszeiten.mjs';
import { einsatzgebiet, ladeGeodaten } from './geodaten.mjs';
import { ergaenzeAdressen, GEWERK_TAGS, geocode, sucheBetriebe } from './osm.mjs';
import { pruefeWebsite } from './pruefung.mjs';
import { sucheWebsite } from './websuche.mjs';
import { baueVariante as baueTemplateVariante, pruefeVariante, schreibeVariante, templateInfo, variantFrei, veroeffentliche, vorschauUrl } from './template.mjs';
import { AUSGABE_DIR, ensureDir, farbe, ladeKonfig, ladeLeads, laufOrdner, log, normName, parallel, readJson, slugify, speichereLeads, starteBrowser, writeJson } from './util.mjs';
import { baueVariante, creditsText } from './variante.mjs';

const ALIAS = {
  elektriker: 'elektro', elektrik: 'elektro', strom: 'elektro',
  sanitaer: 'shk', sanitär: 'shk', heizung: 'shk', installateur: 'shk', klempner: 'shk',
  dach: 'dachdecker', dachdeckerei: 'dachdecker',
  zimmerer: 'zimmerei', holzbau: 'zimmerei',
  schreiner: 'tischler', schreinerei: 'tischler', tischlerei: 'tischler',
  maler: 'maler', lackierer: 'maler', malerbetrieb: 'maler',
  fliesenleger: 'fliesen', fliese: 'fliesen',
  schlosser: 'metallbau', metall: 'metallbau',
  garten: 'galabau', gartenbau: 'galabau', landschaftsbau: 'galabau', gaertner: 'galabau', gärtner: 'galabau',
  maurer: 'bau', bauunternehmen: 'bau', rohbau: 'bau',
  handwerk: 'allgemein', sonstige: 'allgemein',
};

function args(argv) {
  const out = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith('--')) {
      const key = a.slice(2);
      const next = argv[i + 1];
      if (next === undefined || next.startsWith('--')) out[key] = true;
      else {
        out[key] = next;
        i++;
      }
    } else out._.push(a);
  }
  return out;
}

function gewerkeAus(text) {
  if (!text || text === true) throw new Error('Bitte --gewerk angeben, z. B. --gewerk maler,elektro (Liste: fabrik gewerke)');
  if (String(text).toLowerCase() === 'alle') return Object.keys(GEWERK_TAGS);
  return String(text)
    .split(',')
    .map((g) => g.trim().toLowerCase())
    .filter(Boolean)
    .map((g) => {
      const key = GEWERK_TAGS[g] ? g : ALIAS[g];
      if (!key) throw new Error(`Unbekanntes Gewerk „${g}“. Verfügbar: ${Object.keys(GEWERK_TAGS).join(', ')}`);
      return key;
    });
}

function ladeSperrliste(file) {
  if (!existsSync(file)) return [];
  return readFileSync(file, 'utf8')
    .split('\n')
    .map((l) => l.replace(/#.*/, '').trim())
    .filter(Boolean)
    .map((l) => {
      const [name, plz] = l.split('|').map((s) => s.trim());
      return { name: normName(name), plz };
    });
}

/* ───────────────────────────── Schritte ───────────────────────────── */

async function schrittLeads(a, cfg) {
  const ortText = a.ort;
  if (!ortText || ortText === true) throw new Error('Bitte --ort angeben, z. B. --ort Konstanz');
  const gewerke = gewerkeAus(a.gewerk);
  const umkreisKm = a.umkreis ? Number(a.umkreis) : undefined;
  const radiusKm = Number(a.radius ?? cfg.vorschau.radiusKm ?? 25);
  log(`\n${farbe.fett('1/6 Leads')}  ${ortText} · ${gewerke.join(', ')}${umkreisKm ? ` · Umkreis ${umkreisKm} km` : ''}`);

  const ort = await geocode(ortText, cfg.agentur);
  log(farbe.grau(`   Ort: ${ort.anzeige}`));
  const leads = await sucheBetriebe(ort, gewerke, { umkreisKm });
  log(`   ${leads.length} Betriebe in OpenStreetMap gefunden`);
  await ergaenzeAdressen(leads, cfg.agentur);

  const sperre = ladeSperrliste(cfg.sperrliste);
  const slugs = new Set();
  for (const l of leads) {
    let s = slugify(kurznameAus(l.name), 40) || 'betrieb';
    let n = 2;
    while (slugs.has(s)) s = `${slugify(kurznameAus(l.name), 36)}-${n++}`;
    slugs.add(s);
    l.slug = s;
    const nn = normName(l.name);
    if (sperre.some((x) => x.name === nn && (!x.plz || x.plz === l.adresse.plz))) l.ausgeschlossen = 'Sperrliste (Widerspruch)';
    else if (!l.adresse.strasse || !/^\d{5}$/.test(l.adresse.plz ?? '') || !l.adresse.ort) l.ausgeschlossen = 'Adresse unvollständig';
    else if (!l.geo) l.ausgeschlossen = 'Keine Koordinaten';
  }

  const datum = new Date().toISOString().slice(0, 10);
  const id = String(a.lauf && a.lauf !== true ? a.lauf : `${slugify(ort.name)}-${gewerke.join('-')}-${datum}`);
  const dir = ensureDir(join(AUSGABE_DIR, id));
  writeJson(join(dir, 'lauf.json'), { id, ort: ort.name, ortAnzeige: ort.anzeige, zentrum: { lat: ort.lat, lng: ort.lng }, gewerke, umkreisKm, radiusKm, region: a.region && a.region !== true ? a.region : cfg.vorschau.region || '', erstellt: new Date().toISOString() });
  speichereLeads(dir, leads);
  const nutzbar = leads.filter((l) => !l.ausgeschlossen);
  log(`   ${farbe.gruen(nutzbar.length)} mit vollständiger Adresse · ${nutzbar.filter((l) => !l.website).length} ohne Website · ${leads.length - nutzbar.length} ausgeschlossen`);
  log(farbe.grau(`   → ausgabe/${id}/leads.json`));
  return dir;
}

async function schrittPruefen(dir, a) {
  const leads = ladeLeads(dir);
  const offen = leads.filter((l) => !l.ausgeschlossen && (a.neu || !l.bewertung));
  log(`\n${farbe.fett('2/6 Website-Check')}  ${offen.filter((l) => l.website).length} Websites, ${offen.filter((l) => !l.website).length} ohne Website`);
  // Ohne Website in OSM? Erst naheliegende Domains prüfen – sonst droht ein falscher Brief
  await parallel(offen.filter((l) => !l.website), 4, async (l) => {
    const gefunden = await sucheWebsite(l);
    if (gefunden) {
      l.website = gefunden;
      l.websiteQuelle = 'Domain-Suche';
      log(farbe.grau(`   Website gefunden: ${l.name} → ${gefunden}`));
    }
  });
  const browser = await starteBrowser();
  try {
    await parallel(offen, Number(a.parallel ?? 3), async (l) => {
      try {
        l.pruefung = await pruefeWebsite(browser, l, dir);
      } catch (e) {
        l.pruefung = { url: l.website, erreichbar: false, fehler: 'Prüfung fehlgeschlagen', fehlerDetail: String(e.message ?? e) };
      }
      l.bewertung = bewerte(l, l.pruefung);
      log(`   ${String(l.bewertung.score).padStart(3)}  ${l.name}${l.website ? farbe.grau(`  ${l.bewertung.befunde.slice(0, 3).map((b) => b.kurz).join(' · ')}`) : farbe.grau('  keine Website')}`);
    });
  } finally {
    await browser.close();
  }
  speichereLeads(dir, leads);
}

function auswahl(leads, a, cfg) {
  if (a.nur && a.nur !== true) {
    const nur = String(a.nur).split(',').map((s) => s.trim());
    return leads.filter((l) => nur.includes(l.slug));
  }
  const maxScore = Number(a['max-score'] ?? cfg.vorschau.maxScore ?? 60);
  const anzahl = Number(a.anzahl ?? cfg.vorschau.anzahl ?? 10);
  return leads
    .filter((l) => !l.ausgeschlossen && l.bewertung && l.bewertung.score <= maxScore)
    .sort((x, y) => x.bewertung.score - y.bewertung.score || (!!y.telefon - !!x.telefon))
    .slice(0, anzahl);
}

async function schrittVorschauen(dir, a, cfg) {
  const lauf = readJson(join(dir, 'lauf.json'));
  const leads = ladeLeads(dir);
  const info = templateInfo(cfg.template.pfad);
  const geodaten = await ladeGeodaten().catch((e) => {
    log(farbe.gelb(`   ▲ PLZ-Daten nicht verfügbar (${e.message}) – Einsatzgebiet nur mit dem eigenen Ort.`));
    return [];
  });
  const ziel = auswahl(leads, a, cfg);
  log(`\n${farbe.fett('3/6 Vorschauen')}  ${ziel.length} Entwürfe im Template ${farbe.grau(cfg.template.pfad)}`);
  if (!info.gruendungsjahrOptional) log(farbe.gelb('   ▲ Template ohne optionales Gründungsjahr – bitte Template-Branch mit „gruendungsjahr optional“ einspielen.'));

  let i = 0;
  for (const l of ziel) {
    let slug = l.slug;
    let n = 2;
    while (!variantFrei(cfg.template.pfad, slug)) slug = `${l.slug}-${n++}`;
    // Von Hand (oder von Claude) veredelte Varianten nicht überschreiben – nur neu prüfen und bauen
    const vorhanden = readJson(join(cfg.template.pfad, 'variants', slug, 'site.config.json'), null);
    const veredelt = !!vorhanden?.['//fabrik']?.veredelt;
    const erzeugt = baueVariante({ ...l, slug }, info, {
      index: i++,
      laufId: lauf.id,
      agentur: cfg.agentur,
      region: lauf.region,
      radiusKm: lauf.radiusKm,
      gebiet: geodaten.length ? einsatzgebiet(geodaten, { name: l.adresse.ort, lat: l.geo.lat, lng: l.geo.lng }, lauf.radiusKm) : null,
    });
    const config = veredelt ? vorhanden : erzeugt.config;
    const luecken = veredelt ? (l.variante?.luecken ?? []).concat('veredelt – Config von Hand gepflegt') : erzeugt.luecken;
    if (!veredelt) schreibeVariante(cfg.template.pfad, slug, config, creditsText());
    const check = pruefeVariante(cfg.template.pfad, slug);
    l.variante = {
      slug,
      kurzname: config.betrieb.kurzname,
      url: vorschauUrl(info, slug),
      luecken,
      hinweise: check.hinweise,
      oeffnungszeitenBekannt: !!parseOeffnungszeiten(l.oeffnungszeitenRoh),
      oeffnungszeiten: config.betrieb.oeffnungszeiten,
    };
    if (!check.ok) {
      l.variante.fehler = check.fehler.length ? check.fehler : ['variant:check fehlgeschlagen'];
      log(`   ${farbe.rot('✖')} ${l.name}: ${l.variante.fehler.join(' | ')}`);
      continue;
    }
    if (a['ohne-build']) {
      log(`   ${farbe.gruen('✔')} ${slug} (Config geschrieben, nicht gebaut)`);
      continue;
    }
    const b = baueTemplateVariante(cfg.template.pfad, slug);
    l.variante.gebaut = b.ok;
    l.variante.dist = b.dist;
    if (!b.ok) {
      l.variante.fehler = ['Build fehlgeschlagen'];
      l.variante.buildLog = b.log;
      log(`   ${farbe.rot('✖')} ${slug}: Build fehlgeschlagen\n${farbe.grau(b.log)}`);
    } else log(`   ${farbe.gruen('✔')} ${slug}  ${farbe.grau(`${b.sekunden}s${luecken.length ? ` · Lücken: ${luecken.join(', ')}` : ''}`)}`);
    speichereLeads(dir, leads);
  }
  speichereLeads(dir, leads);
}

async function schrittBilder(dir) {
  const leads = ladeLeads(dir);
  const ziel = leads.filter((l) => l.variante?.gebaut);
  log(`\n${farbe.fett('4/6 Screenshots')}  ${ziel.length} Entwürfe`);
  const browser = await starteBrowser();
  try {
    for (const l of ziel) {
      l.bilder = await vorschauScreenshots(browser, l, l.variante.dist, dir);
      l.bilder.vergleich = await vergleichsBild(browser, l, dir);
      log(`   ${farbe.gruen('✔')} ${l.variante.slug}${l.bilder.overflowPx > 0 ? farbe.gelb(`  ▲ ${l.bilder.overflowPx}px Overflow`) : ''}${l.bilder.jsFehler?.length ? farbe.gelb(`  ▲ JS: ${l.bilder.jsFehler[0]}`) : ''}`);
    }
  } finally {
    await browser.close();
  }
  speichereLeads(dir, leads);
}

async function schrittBriefe(dir, a, cfg) {
  const leads = ladeLeads(dir);
  const ziel = leads.filter((l) => l.variante?.gebaut && l.variante.url);
  log(`\n${farbe.fett('5/6 Briefe')}  ${ziel.length} Briefe`);
  const datum = a.datum && a.datum !== true ? new Date(`${a.datum}T12:00:00`) : new Date();
  const browser = await starteBrowser();
  try {
    for (const l of ziel) {
      l.brief = await erzeugeBrief(browser, l, cfg, dir, { datum });
      log(`   ${farbe.gruen('✔')} ${l.brief.pdf}${l.brief.schriftgroesse < 10.3 ? farbe.grau(`  (Schrift ${l.brief.schriftgroesse.toFixed(1)} pt)`) : ''}`);
    }
  } finally {
    await browser.close();
  }
  if (ziel.length) {
    const alle = await sammelPdf(dir, ziel.map((l) => l.brief.pdf));
    const csv = adressCsv(dir, ziel);
    log(farbe.grau(`   → ${alle} (Duplex drucken: Seite 2 = Rückseite) · ${csv}`));
  }
  speichereLeads(dir, leads);
}

function schrittBericht(dir) {
  const lauf = readJson(join(dir, 'lauf.json'));
  const file = schreibeBericht(dir, lauf, ladeLeads(dir));
  log(`\n${farbe.fett('6/6 Bericht')}  → ${join(dir, file)}`);
}

/* ───────────────────────────── Befehle ───────────────────────────── */

const HILFE = `
Vorschau-Fabrik – vom Lead zur Demo-Website und zum Brief

  node src/cli.mjs alles --ort Konstanz --gewerk maler [--anzahl 10] [--region "am Bodensee"]

Einzelschritte (ohne --lauf gilt der zuletzt bearbeitete Lauf):
  leads       --ort <Ort> --gewerk <g1,g2|alle> [--umkreis <km>] [--radius <km>] [--region "am Bodensee"] [--lauf <name>]
  pruefen     [--lauf <name>] [--parallel 3] [--neu]
  vorschauen  [--lauf <name>] [--anzahl 10] [--max-score 60] [--nur slug1,slug2] [--ohne-build]
  bilder      [--lauf <name>]
  briefe      [--lauf <name>] [--datum JJJJ-MM-TT]
  bericht     [--lauf <name>]
  veroeffentlichen [--lauf <name>] [--nur slug1,slug2] --ja   (pusht die Entwürfe ins öffentliche Repo!)
  gewerke     Liste der Gewerke und OSM-Zuordnung

Es werden keine E-Mails verschickt. Ergebnis sind Brief-PDFs zum Ausdrucken.
`;

async function main() {
  const a = args(process.argv.slice(2));
  const befehl = a._[0];
  if (!befehl || befehl === 'hilfe' || a.help) return log(HILFE);
  if (befehl === 'gewerke') {
    for (const [g, tags] of Object.entries(GEWERK_TAGS)) log(`  ${g.padEnd(11)} ${tags.map((t) => `craft=${t.craft}${t.bezeichnung ? ` (${t.bezeichnung})` : ''}`).join(', ')}`);
    return;
  }
  const cfg = ladeKonfig();
  const dirAus = () => laufOrdner(a.lauf && a.lauf !== true ? a.lauf : undefined);

  switch (befehl) {
    case 'leads':
      await schrittLeads(a, cfg);
      break;
    case 'pruefen':
      await schrittPruefen(dirAus(), a);
      break;
    case 'vorschauen':
      await schrittVorschauen(dirAus(), a, cfg);
      break;
    case 'bilder':
      await schrittBilder(dirAus());
      break;
    case 'briefe':
      await schrittBriefe(dirAus(), a, cfg);
      break;
    case 'bericht':
      schrittBericht(dirAus());
      break;
    case 'alles': {
      const dir = await schrittLeads(a, cfg);
      await schrittPruefen(dir, a);
      await schrittVorschauen(dir, a, cfg);
      await schrittBilder(dir);
      await schrittBriefe(dir, a, cfg);
      schrittBericht(dir);
      break;
    }
    case 'veroeffentlichen': {
      const dir = dirAus();
      const leads = ladeLeads(dir);
      const nur = a.nur && a.nur !== true ? String(a.nur).split(',') : null;
      const slugs = leads.filter((l) => l.variante?.gebaut && (!nur || nur.includes(l.variante.slug))).map((l) => l.variante.slug);
      if (!slugs.length) throw new Error('Keine gebauten Entwürfe in diesem Lauf.');
      if (!a.ja) {
        log(`\nDas veröffentlicht ${slugs.length} Entwürfe öffentlich (GitHub Pages, noindex):\n  ${slugs.join(', ')}\n\nZum Ausführen: --ja anhängen.`);
        return;
      }
      if (!veroeffentliche(cfg.template.pfad, slugs)) throw new Error('Veröffentlichen fehlgeschlagen.');
      for (const l of leads) if (slugs.includes(l.variante?.slug)) l.variante.veroeffentlicht = new Date().toISOString();
      speichereLeads(dir, leads);
      break;
    }
    default:
      log(HILFE);
      process.exitCode = 1;
  }
}

main().catch((e) => {
  console.error(farbe.rot(`\n✖ ${e.message ?? e}`));
  process.exit(1);
});
