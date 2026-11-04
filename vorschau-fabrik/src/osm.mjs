// Leadsuche über OpenStreetMap (Nominatim + Overpass). Daten © OpenStreetMap-Mitwirkende, ODbL.
import { fetchMitRetry, normName, normTelefon, sleep, slugify } from './util.mjs';

const OVERPASS = [
  'https://overpass-api.de/api/interpreter',
  'https://maps.mail.ru/osm/tools/overpass/api/interpreter',
  'https://overpass.kumi.systems/api/interpreter',
  'https://overpass.private.coffee/api/interpreter',
];

/**
 * Gewerke des handwerker-templates → OSM-Tags.
 * `bezeichnung` überschreibt die Gewerk-Bezeichnung (gewerkBezeichnung) für Unterarten.
 */
export const GEWERK_TAGS = {
  elektro: [{ craft: 'electrician' }],
  shk: [{ craft: 'plumber' }, { craft: 'hvac' }, { craft: 'heating_engineer' }],
  dachdecker: [{ craft: 'roofer' }],
  zimmerei: [{ craft: 'carpenter', nameNicht: /schreiner|tischler/i }],
  tischler: [{ craft: 'joiner' }, { craft: 'cabinet_maker' }, { craft: 'carpenter', name: /schreiner|tischler/i }],
  maler: [{ craft: 'painter' }],
  fliesen: [{ craft: 'tiler' }],
  metallbau: [{ craft: 'metal_construction' }, { craft: 'blacksmith' }],
  galabau: [{ craft: 'gardener' }, { craft: 'landscaper' }],
  bau: [{ craft: 'builder' }, { craft: 'bricklayer' }],
  allgemein: [
    { craft: 'floorer', bezeichnung: 'Bodenleger' },
    { craft: 'parquet_layer', bezeichnung: 'Parkettleger' },
    { craft: 'glaziery', bezeichnung: 'Glaserei' },
    { craft: 'plasterer', bezeichnung: 'Stuckateur' },
    { craft: 'stonemason', bezeichnung: 'Steinmetz' },
    { craft: 'window_construction', bezeichnung: 'Fensterbau' },
    { craft: 'insulation', bezeichnung: 'Dämmtechnik' },
    { craft: 'scaffolder', bezeichnung: 'Gerüstbau' },
    { craft: 'upholsterer', bezeichnung: 'Raumausstattung' },
  ],
};

/** Gewerk-Bezeichnung aus dem Firmennamen ableiten (z. B. Schreinerei statt Tischlerei) */
export function bezeichnungAusName(gewerk, name) {
  const n = name.toLowerCase();
  if (gewerk === 'tischler' && /schreiner/.test(n)) return 'Schreinerei';
  if (gewerk === 'shk' && /heizung|sanit/.test(n)) return undefined;
  if (gewerk === 'zimmerei' && /holzbau/.test(n)) return 'Holzbau';
  if (gewerk === 'galabau' && /garten/.test(n)) return undefined;
  return undefined;
}

const UA = (agentur) => `vorschau-fabrik/1.0 (${agentur?.website || 'https://github.com/'})`;

/** Ort finden: liefert Koordinaten und (falls vorhanden) die Overpass-Area-ID */
export async function geocode(ort, agentur) {
  const url = `https://nominatim.openstreetmap.org/search?${new URLSearchParams({ q: ort, countrycodes: 'de', format: 'jsonv2', limit: '5' })}`;
  const res = await fetchMitRetry(url, { headers: { 'User-Agent': UA(agentur), 'Accept-Language': 'de' } }, { timeoutMs: 30000 });
  const list = await res.json();
  if (!list.length) throw new Error(`Ort „${ort}“ nicht gefunden.`);
  // Verwaltungsgrenzen (Stadt/Gemeinde) bevorzugen
  const best = list.find((r) => r.osm_type === 'relation' && /administrative|city|town|village/.test(`${r.type} ${r.addresstype}`)) ?? list[0];
  return {
    name: best.name || ort,
    anzeige: best.display_name,
    lat: Number(best.lat),
    lng: Number(best.lon),
    areaId: best.osm_type === 'relation' ? 3600000000 + Number(best.osm_id) : null,
  };
}

export async function overpass(query) {
  let letzter;
  // Zwei Runden über alle Server; bei Ratenlimit (429) etwas länger warten
  for (let runde = 0; runde < 2; runde++) {
    for (const ep of OVERPASS) {
      try {
        const ctrl = new AbortController();
        const t = setTimeout(() => ctrl.abort(), 100000);
        const res = await fetch(ep, {
          method: 'POST',
          body: new URLSearchParams({ data: query }),
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          signal: ctrl.signal,
        }).finally(() => clearTimeout(t));
        if (res.status === 429 || res.status === 504) {
          letzter = new Error(`HTTP ${res.status}`);
          await sleep(runde ? 20000 : 6000);
          continue;
        }
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();
        return json.elements ?? [];
      } catch (e) {
        letzter = e;
      }
    }
  }
  throw new Error(`Overpass nicht erreichbar (${letzter?.message ?? letzter})`);
}

const quote = (s) => String(s).replace(/"/g, '\\"');

function bereichsFilter(ort, umkreisKm) {
  if (umkreisKm || !ort.areaId) return `(around:${Math.round((umkreisKm || 10) * 1000)},${ort.lat},${ort.lng})`;
  return '(area.a)';
}

/** Betriebe der gewählten Gewerke im Ort bzw. Umkreis */
export async function sucheBetriebe(ort, gewerke, { umkreisKm } = {}) {
  const filter = bereichsFilter(ort, umkreisKm);
  const crafts = new Set();
  for (const g of gewerke) for (const t of GEWERK_TAGS[g] ?? []) crafts.add(t.craft);
  if (!crafts.size) throw new Error(`Unbekannte Gewerke: ${gewerke.join(', ')}`);
  const re = [...crafts].map(quote).join('|');
  const q = `[out:json][timeout:90];
${filter === '(area.a)' ? `area(id:${ort.areaId})->.a;` : ''}
(
  nwr${filter}["craft"~"^(${re})$"]["name"];
);
out center tags;`;
  const elements = await overpass(q);
  const leads = [];
  const gesehen = new Set();
  for (const el of elements) {
    const t = el.tags ?? {};
    const zuordnung = ordneGewerk(t, gewerke);
    if (!zuordnung) continue;
    const lead = baueLead(el, zuordnung);
    const key = `${normName(lead.name)}|${slugify(lead.adresse.strasse ?? '')}`;
    if (gesehen.has(key)) continue;
    gesehen.add(key);
    leads.push(lead);
  }
  return leads;
}

function ordneGewerk(tags, gewerke) {
  for (const g of gewerke) {
    for (const regel of GEWERK_TAGS[g] ?? []) {
      if (tags.craft !== regel.craft) continue;
      if (regel.name && !regel.name.test(tags.name ?? '')) continue;
      if (regel.nameNicht && regel.nameNicht.test(tags.name ?? '')) continue;
      return { gewerk: g, bezeichnung: regel.bezeichnung ?? bezeichnungAusName(g, tags.name ?? '') };
    }
  }
  return null;
}

const ersteUrl = (...werte) => {
  for (const w of werte) {
    if (!w) continue;
    const s = String(w).split(';')[0].trim();
    if (!s) continue;
    const mitSchema = /^https?:\/\//i.test(s) ? s : `https://${s.replace(/^\/+/, '')}`;
    try {
      return new URL(mitSchema).toString();
    } catch {}
  }
  return undefined;
};

export function baueLead(el, { gewerk, bezeichnung }) {
  const t = el.tags ?? {};
  const lat = el.lat ?? el.center?.lat;
  const lng = el.lon ?? el.center?.lon;
  const strasse = [t['addr:street'], t['addr:housenumber']].filter(Boolean).join(' ') || undefined;
  const start = /^(1[89]\d\d|20\d\d)/.exec(t.start_date ?? '')?.[1];
  const social = [];
  for (const [netzwerk, key] of [['facebook', 'contact:facebook'], ['instagram', 'contact:instagram'], ['facebook', 'facebook'], ['instagram', 'instagram']]) {
    const u = ersteUrl(t[key]);
    if (u && !social.some((s) => s.netzwerk === netzwerk)) social.push({ netzwerk, url: u });
  }
  return {
    id: `${el.type}/${el.id}`,
    name: String(t.name).trim(),
    gewerk,
    gewerkBezeichnung: bezeichnung,
    craft: t.craft,
    adresse: {
      strasse,
      plz: t['addr:postcode'],
      ort: t['addr:city'] || t['addr:place'] || t['addr:suburb'],
    },
    geo: lat != null ? { lat: Number(lat.toFixed(5)), lng: Number(lng.toFixed(5)) } : undefined,
    telefon: normTelefon(t.phone || t['contact:phone'] || t.mobile || t['contact:mobile']),
    email: (t.email || t['contact:email'] || '').split(';')[0].trim() || undefined,
    website: ersteUrl(t.website, t['contact:website'], t.url),
    oeffnungszeitenRoh: t.opening_hours,
    gruendungsjahr: start ? Number(start) : undefined,
    operator: t.operator,
    socialLinks: social,
    quelle: 'OpenStreetMap',
  };
}

/** Fehlende PLZ/Ort per Nominatim-Rückwärtssuche ergänzen (max. 1 Anfrage/Sekunde) */
export async function ergaenzeAdressen(leads, agentur, { max = 40 } = {}) {
  let n = 0;
  for (const l of leads) {
    if (!l.geo || (l.adresse.plz && l.adresse.ort && l.adresse.strasse) || n >= max) continue;
    n++;
    const url = `https://nominatim.openstreetmap.org/reverse?${new URLSearchParams({ lat: l.geo.lat, lon: l.geo.lng, format: 'jsonv2', zoom: '18', addressdetails: '1' })}`;
    try {
      const res = await fetchMitRetry(url, { headers: { 'User-Agent': UA(agentur), 'Accept-Language': 'de' } }, { timeoutMs: 20000, versuche: 2 });
      const a = (await res.json()).address ?? {};
      l.adresse.plz ??= a.postcode;
      l.adresse.ort ??= a.city || a.town || a.village || a.municipality;
      if (!l.adresse.strasse && a.road && a.house_number) {
        l.adresse.strasse = `${a.road} ${a.house_number}`;
        l.adresseErgaenzt = true;
      }
    } catch {}
    await sleep(1100);
  }
}

export const entfernungKm = (a, b) => {
  const R = 6371;
  const dLat = ((b.lat - a.lat) * Math.PI) / 180;
  const dLng = ((b.lng - a.lng) * Math.PI) / 180;
  const x = Math.sin(dLat / 2) ** 2 + Math.cos((a.lat * Math.PI) / 180) * Math.cos((b.lat * Math.PI) / 180) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(x));
};
