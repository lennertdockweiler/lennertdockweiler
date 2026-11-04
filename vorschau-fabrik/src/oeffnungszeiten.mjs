// OSM opening_hours (häufige Formen) → Format des handwerker-templates.
// Unterstützt: „Mo-Fr 07:30-12:00,13:00-17:00; Sa 08:00-12:00“, „24/7“, „Mo,We 08:00-12:00“,
// „off“/„closed“, Kommentare in Anführungszeichen. Komplexe Regeln (Monate, Wochen, Feiertage) → null.

const TAG = { mo: 'mo', tu: 'di', we: 'mi', th: 'do', fr: 'fr', sa: 'sa', su: 'so' };
const REIHENFOLGE = ['mo', 'di', 'mi', 'do', 'fr', 'sa', 'so'];
const OSM_TAGE = ['mo', 'tu', 'we', 'th', 'fr', 'sa', 'su'];

function tageAus(spec) {
  const tage = new Set();
  for (const teil of spec.split(',')) {
    const t = teil.trim().toLowerCase();
    if (!t) continue;
    const m = /^(mo|tu|we|th|fr|sa|su)(?:\s*-\s*(mo|tu|we|th|fr|sa|su))?$/.exec(t);
    if (!m) return null;
    const a = OSM_TAGE.indexOf(m[1]);
    const b = m[2] ? OSM_TAGE.indexOf(m[2]) : a;
    for (let i = a; ; i = (i + 1) % 7) {
      tage.add(TAG[OSM_TAGE[i]]);
      if (i === b) break;
    }
  }
  return tage;
}

const zeitOk = (z) => /^([01]\d|2[0-4]):[0-5]\d$/.test(z);
const pad = (z) => (/^\d:\d\d$/.test(z) ? `0${z}` : z);

function zeitenAus(spec) {
  const out = [];
  for (const teil of spec.split(',')) {
    const t = teil.trim();
    if (!t) continue;
    const m = /^(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})\+?$/.exec(t);
    if (!m) return null;
    const von = pad(m[1]);
    const bis = pad(m[2]);
    if (!zeitOk(von) || !zeitOk(bis)) return null;
    out.push({ von, bis });
  }
  return out;
}

/**
 * @returns {{ regulaer: {tage:string[],von:string,bis:string}[], hinweis?: string } | null}
 */
export function parseOeffnungszeiten(raw) {
  if (!raw || typeof raw !== 'string') return null;
  let s = raw.trim();
  let hinweis;
  const kommentar = /"([^"]{3,120})"/.exec(s);
  if (kommentar) {
    hinweis = kommentar[1];
    s = s.replace(/"[^"]*"/g, '').trim();
  }
  if (s === '24/7') {
    return { regulaer: [{ tage: [...REIHENFOLGE], von: '00:00', bis: '24:00' }], ...(hinweis ? { hinweis } : {}) };
  }
  // Monate, Wochen, Feiertage, Sonnenauf-/untergang: zu komplex → lieber gar nichts behaupten
  if (/\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|week|sunrise|sunset|dawn|dusk|easter)\b/i.test(s)) return null;

  const plan = new Map(); // tag -> [{von,bis}]
  for (let regel of s.split(/;|\|\|/)) {
    regel = regel.trim().replace(/\bPH\s+(off|closed)\b/gi, '').replace(/\bPH\b[^;]*/gi, '').trim();
    if (!regel) continue;
    const m = /^((?:(?:mo|tu|we|th|fr|sa|su)(?:\s*-\s*(?:mo|tu|we|th|fr|sa|su))?\s*,?\s*)+)\s*(.*)$/i.exec(regel);
    let tage;
    let rest;
    if (m) {
      tage = tageAus(m[1].replace(/\s+/g, '').replace(/,$/, ''));
      rest = m[2].trim();
    } else {
      tage = new Set(REIHENFOLGE);
      rest = regel;
    }
    if (!tage) return null;
    if (/^(off|closed)$/i.test(rest)) {
      for (const t of tage) plan.set(t, []);
      continue;
    }
    const zeiten = zeitenAus(rest);
    if (!zeiten || !zeiten.length) return null;
    for (const t of tage) plan.set(t, zeiten);
  }

  // Gleiche Zeitfenster über mehrere Tage zusammenfassen
  const gruppen = new Map();
  for (const tag of REIHENFOLGE) {
    for (const z of plan.get(tag) ?? []) {
      const key = `${z.von}-${z.bis}`;
      if (!gruppen.has(key)) gruppen.set(key, { tage: [], von: z.von, bis: z.bis });
      gruppen.get(key).tage.push(tag);
    }
  }
  const regulaer = [...gruppen.values()].sort((a, b) => REIHENFOLGE.indexOf(a.tage[0]) - REIHENFOLGE.indexOf(b.tage[0]) || a.von.localeCompare(b.von));
  if (!regulaer.length) return null;
  return { regulaer, ...(hinweis ? { hinweis: hinweis.slice(0, 120) } : {}) };
}

/** Lesbare Kurzform, z. B. für Briefe und Berichte */
export function oeffnungszeitenText(oz) {
  if (!oz?.regulaer?.length) return '';
  const name = { mo: 'Mo', di: 'Di', mi: 'Mi', do: 'Do', fr: 'Fr', sa: 'Sa', so: 'So' };
  return oz.regulaer
    .map((r) => {
      const idx = r.tage.map((t) => REIHENFOLGE.indexOf(t));
      const zusammenhaengend = idx.every((v, i) => i === 0 || v === idx[i - 1] + 1);
      const tage = r.tage.length > 2 && zusammenhaengend ? `${name[r.tage[0]]}–${name[r.tage.at(-1)]}` : r.tage.map((t) => name[t]).join(', ');
      return `${tage} ${r.von}–${r.bis}`;
    })
    .join(' · ');
}
