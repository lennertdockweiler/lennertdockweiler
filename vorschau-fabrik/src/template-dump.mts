/**
 * Liest Gewerk-Presets, Basistexte und Schema-Konstanten aus dem handwerker-template
 * und gibt sie als JSON aus. Aufruf (im Template-Ordner, damit tsx gefunden wird):
 *   node --import tsx <pfad>/template-dump.mts <template-pfad>
 */
import { pathToFileURL } from 'node:url';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const root = process.argv[2] ?? process.cwd();
const imp = (p: string) => import(pathToFileURL(join(root, p)).href);

const gewerke = await imp('src/data/gewerke/index.ts');
const schema = await imp('variants/_schema.ts');
const schemaText = readFileSync(join(root, 'variants/_schema.ts'), 'utf8');

const presets: Record<string, unknown> = {};
for (const [key, p] of Object.entries(gewerke.GEWERK_PRESETS as Record<string, any>)) {
  presets[key] = {
    key: p.key,
    bezeichnung: p.bezeichnung,
    betriebsart: p.betriebsart,
    berufsbezeichnung: p.berufsbezeichnung,
    notdienstRelevant: p.notdienstRelevant,
    leistungen: p.leistungen.map((l: any) => ({ slug: l.slug, titel: l.titel, kurztext: l.kurztext, text: l.text, faq: l.faq ?? [] })),
    faq: p.faq,
    werte: p.werte,
    texte: p.texte,
  };
}

let veroeffentlichen = null;
try {
  veroeffentlichen = JSON.parse(readFileSync(join(root, 'veroeffentlichen.config.json'), 'utf8'));
} catch {}

process.stdout.write(
  JSON.stringify({
    gewerke: schema.GEWERKE,
    stilPresets: schema.STIL_PRESETS,
    schriften: schema.SCHRIFTEN,
    gruendungsjahrOptional: (schema.siteConfigSchema.shape.betrieb.shape.gruendungsjahr.safeParse(undefined).success as boolean) || /gruendungsjahr:\s*z[\s\S]{0,240}?\.optional\(\)/.test(schemaText),
    basisTexte: gewerke.basisTexte,
    basisWerte: gewerke.basisWerte,
    presets,
    veroeffentlichen,
  }),
);
