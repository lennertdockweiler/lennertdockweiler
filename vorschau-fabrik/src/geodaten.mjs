// Deutsche Postleitzahlen + Orte mit Koordinaten (GeoNames, CC BY 4.0) für das Einsatzgebiet.
// Wird beim ersten Lauf einmalig heruntergeladen und in daten/ zwischengespeichert.
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { inflateRawSync } from 'node:zlib';
import { entfernungKm } from './osm.mjs';
import { FABRIK_DIR, fetchMitRetry } from './util.mjs';

const QUELLE = 'https://download.geonames.org/export/zip/DE.zip';
const CACHE = join(FABRIK_DIR, 'daten', 'geonames-DE.txt');

/** Erste Datei aus einem ZIP entpacken (über das zentrale Verzeichnis, Deflate oder unkomprimiert) */
export function entpackeZip(buf, name) {
  const eocd = buf.lastIndexOf(Buffer.from([0x50, 0x4b, 0x05, 0x06]));
  if (eocd < 0) throw new Error('Kein ZIP-Archiv');
  const anzahl = buf.readUInt16LE(eocd + 10);
  let pos = buf.readUInt32LE(eocd + 16);
  for (let i = 0; i < anzahl; i++) {
    const methode = buf.readUInt16LE(pos + 10);
    const groesse = buf.readUInt32LE(pos + 20);
    const nameLen = buf.readUInt16LE(pos + 28);
    const extraLen = buf.readUInt16LE(pos + 30);
    const kommentarLen = buf.readUInt16LE(pos + 32);
    const lokal = buf.readUInt32LE(pos + 42);
    const datei = buf.toString('utf8', pos + 46, pos + 46 + nameLen);
    if (!name || datei === name) {
      const start = lokal + 30 + buf.readUInt16LE(lokal + 26) + buf.readUInt16LE(lokal + 28);
      const daten = buf.subarray(start, start + groesse);
      return methode === 8 ? inflateRawSync(daten) : daten;
    }
    pos += 46 + nameLen + extraLen + kommentarLen;
  }
  throw new Error(`${name} nicht im ZIP gefunden`);
}

let speicher = null;

/** @returns {Promise<{plz:string, ort:string, kreis:string, lat:number, lng:number}[]>} */
export async function ladeGeodaten() {
  if (speicher) return speicher;
  if (!existsSync(CACHE)) {
    const res = await fetchMitRetry(QUELLE, {}, { timeoutMs: 60000 });
    if (!res.ok) throw new Error(`GeoNames-Download fehlgeschlagen (HTTP ${res.status})`);
    const txt = entpackeZip(Buffer.from(await res.arrayBuffer()), 'DE.txt');
    mkdirSync(join(FABRIK_DIR, 'daten'), { recursive: true });
    writeFileSync(CACHE, txt);
  }
  speicher = readFileSync(CACHE, 'utf8')
    .split('\n')
    .map((z) => z.split('\t'))
    // Spalte 12 (Genauigkeit) ist bei Großkunden-PLZ (Behörden, Firmen) leer → nur echte Orte
    .filter((f) => f.length >= 12 && /^\d{5}$/.test(f[1]) && f[11].trim() !== '')
    .map((f) => ({ plz: f[1], ort: f[2], kreis: f[7], lat: Number(f[9]), lng: Number(f[10]) }));
  return speicher;
}

/**
 * Einsatzgebiet rund um einen Betrieb: nächstgelegene Orte (mit ihren echten PLZ),
 * PLZ im Radius (Kerngebiet) und im erweiterten Ring (auf Anfrage).
 */
export function einsatzgebiet(daten, zentrum, radiusKm, { maxOrte = 8, ring = 15 } = {}) {
  const imUmkreis = daten.map((d) => ({ ...d, km: entfernungKm(zentrum, d) })).filter((d) => d.km <= radiusKm + ring);
  const orte = new Map();
  for (const d of imUmkreis.filter((d) => d.km <= radiusKm)) {
    // Ortsteile mit Klammerzusatz („Allensbach (Hegne)“) zum Hauptort zählen
    const name = d.ort.replace(/\s*\(.*\)\s*$/, '').trim();
    const key = `${name}|${d.kreis}`;
    const o = orte.get(key) ?? { name, lat: 0, lng: 0, n: 0, plz: new Set(), km: Infinity };
    o.lat += d.lat;
    o.lng += d.lng;
    o.n++;
    o.plz.add(d.plz);
    o.km = Math.min(o.km, d.km);
    orte.set(key, o);
  }
  const liste = [...orte.values()]
    .map((o) => ({ name: o.name, lat: Number((o.lat / o.n).toFixed(4)), lng: Number((o.lng / o.n).toFixed(4)), plz: [...o.plz].sort(), km: o.km, gewicht: o.plz.size }))
    .filter((o) => o.name.length <= 40);
  const eigener = liste.find((o) => o.name === zentrum.name) ?? liste.sort((a, b) => a.km - b.km)[0];
  const weitere = liste
    .filter((o) => o !== eigener)
    .sort((a, b) => b.gewicht - a.gewicht || a.km - b.km)
    .slice(0, maxOrte - 1)
    .sort((a, b) => a.km - b.km);
  const kern = [...new Set(imUmkreis.filter((d) => d.km <= radiusKm).map((d) => d.plz))].sort();
  const anfrage = [...new Set(imUmkreis.filter((d) => d.km > radiusKm).map((d) => d.plz))].filter((p) => !kern.includes(p)).sort();
  return {
    orte: [eigener, ...weitere].filter(Boolean).map(({ name, lat, lng, plz }) => ({ name, lat, lng, plz })),
    plz: kern.slice(0, 200),
    plzAufAnfrage: anfrage.slice(0, 200),
  };
}
