import { test } from 'node:test';
import assert from 'node:assert/strict';
import { baueVariante, ehrlicheTexte } from '../src/variante.mjs';

// Ausschnitt der echten Preset-Texte des handwerker-templates
const info = {
  gruendungsjahrOptional: true,
  basisTexte: {
    heroHeadline: 'Saubere Arbeit. Klare Absprachen. Seit {gruendungsjahr}.',
    heroSubline: '{kurzname} ist {{Ihr|dein}} Meisterbetrieb in {ort} und {region}. Wir planen ehrlich.',
    heroStatement: 'Gut gemacht hält länger.',
    ueberUnsTitel: 'Ein Familienbetrieb mit Anspruch',
    metaBeschreibung: '{name} – {gewerk} in {ort}. Meisterbetrieb seit {gruendungsjahr}. Jetzt Projekt anfragen.',
  },
  presets: {
    shk: {
      bezeichnung: 'Sanitär, Heizung & Klima',
      betriebsart: 'SHK-Fachbetrieb',
      leistungen: [{ slug: 'waermepumpe' }, { slug: 'badsanierung' }, { slug: 'notdienst' }],
      faq: [
        { frage: 'Was kostet der Notdienst?', antwort: 'Pauschale vorab.' },
        { frage: 'Wie lange dauert eine Badsanierung?', antwort: 'Meist zwei bis drei Wochen.' },
      ],
      werte: [{ titel: 'Erreichbar, wenn es zählt', text: 'Rund um die Uhr im Notdienst, bevorzugt für Wartungskunden.' }],
      texte: {
        heroSubline: 'Wärmepumpen, Bäder und Heiztechnik vom Meisterbetrieb in {ort} – mit Notdienst rund um die Uhr.',
        heroStatement: 'Heiß auf Wärme. Cool im Notfall.',
        metaBeschreibung: '{name}: SHK-Meisterbetrieb in {ort}. Wärmepumpe, Badsanierung, Heizung, Klima und 24h-Notdienst. Jetzt Anfrage stellen.',
      },
    },
  },
};

const lead = {
  id: 'node/1',
  slug: 'bad-sommer',
  name: 'Bad & Heizung Sommer GmbH',
  gewerk: 'shk',
  adresse: { strasse: 'Seestraße 1', plz: '78467', ort: 'Konstanz' },
  geo: { lat: 47.67, lng: 9.17 },
  oeffnungszeitenRoh: 'Mo-Fr 08:00-17:00',
  pruefung: {},
};

test('Ehrlichkeits-Filter: kein Meister-, Notdienst- oder Familien-Versprechen', () => {
  const t = ehrlicheTexte(info, 'shk', { meisterbetrieb: false, notdienst: false });
  const alles = Object.values(t).join(' | ');
  assert.doesNotMatch(alles, /Meister|Notdienst|Notfall|rund um die Uhr|Familienbetrieb/);
  assert.equal(t.heroSubline, 'Wärmepumpen, Bäder und Heiztechnik aus {ort}.');
  assert.equal(t.heroStatement, 'Heiß auf Wärme. Cool im Sommer.');
  assert.equal(t.metaBeschreibung, '{name}: SHK-Betrieb in {ort}. Wärmepumpe, Badsanierung, Heizung, Klima. Jetzt Anfrage stellen.');
});

test('Meisterbetrieb mit Nachweis behält die Preset-Texte', () => {
  const t = ehrlicheTexte(info, 'shk', { meisterbetrieb: true, notdienst: true });
  assert.equal(t.heroSubline, undefined);
});

test('Variante: keine erfundenen Fakten, Notdienst-Leistung raus, Banner kurz', () => {
  const { config, luecken } = baueVariante(lead, info, { index: 0, laufId: 't', agentur: { name: 'Studio X', telefon: '0151 1234567', email: 'a@b.de' } });
  assert.equal(config.betrieb.gruendungsjahr, undefined);
  assert.equal(config.betrieb.bewertungen, undefined);
  assert.equal(config.meisterbetrieb, false);
  assert.equal(config.notdienst.aktiv, false);
  assert.deepEqual(config.leistungen.map((l) => l.slug), ['waermepumpe', 'badsanierung']);
  assert.deepEqual(config.faq.map((f) => f.frage), ['Wie lange dauert eine Badsanierung?']);
  assert.ok(config.demo.banner.text.length <= 120);
  assert.equal(config.meta.noindex, true);
  assert.equal(config.betrieb.oeffnungszeiten.regulaer[0].von, '08:00');
  assert.equal(config.demo.agentur.telefon, '+49 151 1234567');
  assert.ok(luecken.includes('Telefonnummer fehlt'));
  assert.ok(config.sektionen.some((s) => s.typ === 'hero'));
  assert.ok(!config.sektionen.some((s) => s.typ === 'bewertungen' || s.typ === 'usps' || s.typ === 'karriere'));
});

test('Variante: bekanntes Gründungsjahr und Website-Farben werden übernommen', () => {
  const l = { ...lead, pruefung: { farben: { primaer: '#123456', akzent: '#ABCDEF' }, extrakt: { gruendungsjahr: 1987, inhaber: 'Eva Sommer' } } };
  const { config } = baueVariante(l, info, { index: 1, laufId: 't', agentur: { name: 'Studio X' } });
  assert.equal(config.betrieb.gruendungsjahr, 1987);
  assert.equal(config.betrieb.inhaber, 'Eva Sommer');
  assert.deepEqual(config.branding.farben, { primaer: '#123456', akzent: '#ABCDEF' });
});

test('Ohne optionales Gründungsjahr im Template wird die Lücke gemeldet', () => {
  const { luecken } = baueVariante(lead, { ...info, gruendungsjahrOptional: false }, { index: 0, laufId: 't', agentur: { name: 'X' } });
  assert.ok(luecken.some((x) => x.startsWith('Gründungsjahr unbekannt')));
});
