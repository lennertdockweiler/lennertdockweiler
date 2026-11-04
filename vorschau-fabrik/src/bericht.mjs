// Übersicht eines Laufs als HTML-Datei (lokal öffnen): Leads, Bewertung, Vorschau, Brief.
import { writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { oeffnungszeitenText } from './oeffnungszeiten.mjs';
import { domainVon, escHtml as e } from './util.mjs';

const badge = (score) => {
  if (score == null) return '<span class="b b-grau">–</span>';
  const cls = score < 50 ? 'b-rot' : score < 75 ? 'b-gelb' : 'b-gruen';
  return `<span class="b ${cls}">${score}</span>`;
};

export function schreibeBericht(laufDir, lauf, leads) {
  const ausgewaehlt = leads.filter((l) => l.variante);
  const zeilen = leads
    .slice()
    .sort((a, b) => (a.bewertung?.score ?? 101) - (b.bewertung?.score ?? 101))
    .map((l) => {
      const p = l.pruefung ?? {};
      const domain = domainVon(p.finalUrl || l.website);
      const befunde = (l.bewertung?.befunde ?? []).map((b) => `<li>${e(b.kurz)}</li>`).join('');
      const links = [
        l.website ? `<a href="${e(l.website)}">${e(domain)}</a>${l.websiteQuelle ? ' <small>(per Domain-Suche gefunden)</small>' : ''}` : `<a href="https://www.google.com/search?q=${encodeURIComponent(`${l.name} ${l.adresse.ort ?? ''}`)}">Google-Suche prüfen</a>`,
        l.variante?.url ? `<a href="${e(l.variante.url)}">Vorschau-URL</a>` : '',
        l.bilder?.nachherDesktop ? `<a href="${e(l.bilder.nachherDesktop)}">Screenshot Desktop</a>` : '',
        l.bilder?.vergleich ? `<a href="${e(l.bilder.vergleich)}">Vorher/Nachher</a>` : '',
        l.brief?.pdf ? `<a href="${e(l.brief.pdf)}"><b>Brief (PDF)</b></a>` : '',
      ].filter(Boolean);
      const status = l.ausgeschlossen
        ? `<span class="tag tag-aus">${e(l.ausgeschlossen)}</span>`
        : l.brief?.pdf
          ? '<span class="tag tag-ok">Brief fertig</span>'
          : l.variante?.gebaut
            ? '<span class="tag tag-ok">Vorschau gebaut</span>'
            : l.variante?.fehler
              ? `<span class="tag tag-aus">Variante: ${e(l.variante.fehler[0] ?? 'Fehler')}</span>`
              : '<span class="tag">Lead</span>';
      const luecken = (l.variante?.luecken ?? []).map((x) => `<li>${e(x)}</li>`).join('');
      return `<article class="lead">
        <div class="kopf">${badge(l.bewertung?.score)}<div><h2>${e(l.name)}</h2><p class="adr">${e([l.adresse.strasse, [l.adresse.plz, l.adresse.ort].filter(Boolean).join(' ')].filter(Boolean).join(', '))} · ${e(l.gewerkBezeichnung ?? l.gewerk)}${l.telefon ? ` · ${e(l.telefon)}` : ''}</p></div>${status}</div>
        <div class="grid">
          ${p.screenshot ? `<img src="${e(p.screenshot)}" alt="Website heute" loading="lazy">` : '<div class="leer">keine Website</div>'}
          ${l.bilder?.nachher ? `<img src="${e(l.bilder.nachher)}" alt="Entwurf" loading="lazy">` : '<div class="leer">noch kein Entwurf</div>'}
          <div class="txt">
            ${befunde ? `<h3>Befunde</h3><ul>${befunde}</ul>` : ''}
            ${luecken ? `<h3>Lücken im Entwurf</h3><ul class="luecken">${luecken}</ul>` : ''}
            ${l.oeffnungszeitenRoh ? `<p class="klein">Öffnungszeiten (OSM): ${e(oeffnungszeitenText(l.variante?.oeffnungszeiten) || l.oeffnungszeitenRoh)}</p>` : ''}
            <p class="links">${links.join(' · ')}</p>
          </div>
        </div>
      </article>`;
    })
    .join('\n');

  const html = `<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex">
<title>Vorschau-Fabrik – ${e(lauf.id)}</title>
<style>
  :root { --bg:#f6f5f2; --card:#fff; --ink:#17191c; --muted:#646a73; --line:#e4e1da; }
  @media (prefers-color-scheme: dark) { :root { --bg:#121417; --card:#1b1e22; --ink:#eceae6; --muted:#9aa0a8; --line:#2c3036; } }
  * { box-sizing:border-box } body { margin:0; background:var(--bg); color:var(--ink); font:15px/1.5 Inter,system-ui,sans-serif; }
  header.top { padding:28px 16px 8px; max-width:1100px; margin:0 auto; } h1 { margin:0 0 4px; font-size:24px; }
  .meta { color:var(--muted); margin:0 0 16px; } .zahlen { display:flex; gap:12px; flex-wrap:wrap; margin-bottom:8px; }
  .zahl { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:10px 14px; } .zahl b { display:block; font-size:22px; }
  main { max-width:1100px; margin:0 auto; padding:8px 16px 48px; display:grid; gap:14px; }
  .lead { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:16px; }
  .kopf { display:flex; gap:12px; align-items:center; } .kopf > div { flex:1; min-width:0 } h2 { font-size:17px; margin:0; } .adr { margin:2px 0 0; color:var(--muted); font-size:13px; }
  .b { display:inline-grid; place-items:center; width:44px; height:44px; border-radius:50%; font-weight:700; color:#fff; flex:none; }
  .b-rot { background:#c0392b } .b-gelb { background:#c98a00 } .b-gruen { background:#2e8b57 } .b-grau { background:#888 }
  .tag { font-size:12px; padding:3px 8px; border-radius:99px; border:1px solid var(--line); white-space:nowrap } .tag-ok { background:#e6f4ea; color:#1e6b3a; border-color:#bfe3c9 } .tag-aus { background:#fbeaea; color:#8a2a22; border-color:#f0c9c5 }
  .grid { display:grid; grid-template-columns:150px 150px 1fr; gap:14px; margin-top:12px; align-items:start; }
  .grid img, .leer { width:150px; aspect-ratio:390/844; object-fit:cover; object-position:top; border-radius:12px; border:1px solid var(--line); background:#ddd; }
  .leer { display:grid; place-items:center; color:var(--muted); font-size:13px; background:repeating-linear-gradient(135deg,transparent 0 10px,rgba(127,127,127,.12) 10px 20px); }
  h3 { font-size:13px; text-transform:uppercase; letter-spacing:.06em; color:var(--muted); margin:0 0 4px } ul { margin:0 0 10px; padding-left:18px } .luecken { color:#a05a00 }
  .klein { font-size:13px; color:var(--muted) } .links { font-size:14px } a { color:inherit }
  @media (max-width:700px) { .grid { grid-template-columns:1fr 1fr } .grid .txt { grid-column:1/-1 } .grid img, .leer { width:100% } .kopf { flex-wrap:wrap } }
</style></head><body>
<header class="top">
  <h1>${e(lauf.ort)} · ${e(lauf.gewerke.join(', '))}</h1>
  <p class="meta">Lauf ${e(lauf.id)} · erstellt ${e(new Date(lauf.erstellt).toLocaleString('de-DE'))} · Daten © OpenStreetMap-Mitwirkende (ODbL)</p>
  <div class="zahlen">
    <div class="zahl"><b>${leads.length}</b>Betriebe gefunden</div>
    <div class="zahl"><b>${leads.filter((l) => !l.website).length}</b>ohne Website</div>
    <div class="zahl"><b>${leads.filter((l) => (l.bewertung?.score ?? 100) < 50).length}</b>mit dringendem Bedarf</div>
    <div class="zahl"><b>${ausgewaehlt.filter((l) => l.variante?.gebaut).length}</b>Vorschauen gebaut</div>
    <div class="zahl"><b>${leads.filter((l) => l.brief?.pdf).length}</b>Briefe</div>
  </div>
</header>
<main>${zeilen}</main></body></html>`;
  writeFileSync(join(laufDir, 'bericht.html'), html);
  return 'bericht.html';
}
