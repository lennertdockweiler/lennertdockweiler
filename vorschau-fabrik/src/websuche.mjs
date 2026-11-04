// Für Betriebe ohne Website in OpenStreetMap: naheliegende Domains ausprobieren,
// damit kein Brief „Sie haben keine Website“ an einen Betrieb mit Website geht.
import { kurznameAus } from './extraktion.mjs';
import { slugify } from './util.mjs';

const FUELLWOERTER = /^(gmbh|ug|kg|ohg|ek|gbr|und|inh|inhaber|der|die|das|co)$/;

export function domainKandidaten(lead) {
  const woerter = slugify(kurznameAus(lead.name), 80).split('-').filter((w) => w && !FUELLWOERTER.test(w));
  const ort = slugify(lead.adresse?.ort ?? '', 30).split('-')[0];
  const basen = new Set();
  if (woerter.length) {
    basen.add(woerter.join('-'));
    basen.add(woerter.join(''));
    if (woerter.length >= 2) basen.add([...woerter].reverse().join('-'));
    if (ort) basen.add(`${woerter.join('-')}-${ort}`);
    const letztes = woerter[woerter.length - 1];
    if (woerter.length >= 2 && letztes.length >= 4) basen.add(letztes);
  }
  return [...basen].filter((b) => b.length >= 4 && b.length <= 50).slice(0, 6).map((b) => `https://www.${b}.de/`);
}

/** Prüft, ob unter einer Kandidaten-Domain eine Seite erreichbar ist, die zum Betrieb passt */
export async function sucheWebsite(lead, { timeoutMs = 8000 } = {}) {
  const namensteile = slugify(kurznameAus(lead.name), 80).split('-').filter((w) => w.length >= 4 && !FUELLWOERTER.test(w));
  for (const url of domainKandidaten(lead)) {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), timeoutMs);
    try {
      const res = await fetch(url, { redirect: 'follow', signal: ctrl.signal, headers: { 'User-Agent': 'Mozilla/5.0 (vorschau-fabrik)' } });
      if (!res.ok) continue;
      const html = (await res.text()).slice(0, 400000);
      const text = slugify(html.replace(/<[^>]+>/g, ' '), 400000);
      const passtName = namensteile.length && namensteile.every((w) => text.includes(w));
      const passtOrt = (lead.adresse?.plz && html.includes(lead.adresse.plz)) || (lead.adresse?.ort && text.includes(slugify(lead.adresse.ort)));
      if (passtName && passtOrt) return res.url || url;
    } catch {
      // Domain existiert nicht oder antwortet nicht
    } finally {
      clearTimeout(t);
    }
  }
  return null;
}
