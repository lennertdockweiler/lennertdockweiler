import { test } from 'node:test';
import assert from 'node:assert/strict';
import { briefDaten } from '../src/brief.mjs';
import { einsatzgebiet } from '../src/geodaten.mjs';
import { normTelefon, slugify } from '../src/util.mjs';
import { domainKandidaten } from '../src/websuche.mjs';

const cfg = { agentur: { name: 'Studio X', telefon: '+49 151 1', email: 'hallo@studio-x.de' }, vorschau: { loeschenNachWochen: 6 } };
const basis = { name: 'Elektro Moser', gewerk: 'elektro', adresse: { strasse: 'Turmstraße 7', plz: '78467', ort: 'Konstanz' }, variante: { kurzname: 'Elektro Moser', url: 'https://x.github.io/e/elektro-moser/' } };

test('Brief ohne Website: Suchsatz, Aufzählung, Widerspruchshinweis', () => {
  const d = briefDaten({ ...basis, bewertung: { kategorie: 'keine-website', befunde: [] } }, cfg);
  assert.match(d.absaetze[0], /^wer heute in Konstanz einen Elektriker sucht/);
  assert.match(d.datenschutz, /Art\. 21 DSGVO/);
  assert.equal(d.anrede, 'Sehr geehrte Damen und Herren,');
  assert.deepEqual(d.empfaenger, ['Elektro Moser', 'Turmstraße 7', '78467 Konstanz']);
});

test('Brief mit Befunden und bekanntem Inhaber', () => {
  const lead = {
    ...basis,
    website: 'https://elektro-moser.de',
    pruefung: { finalUrl: 'https://www.elektro-moser.de/', screenshot: 'screens/x.png', extrakt: { inhaber: 'Karl Moser' } },
    bewertung: { kategorie: 'dringend', befunde: [{ brief: 'A.' }, { brief: '' }, { brief: 'B.' }, { brief: 'C.' }, { brief: 'D.' }] },
  };
  const d = briefDaten(lead, cfg);
  assert.equal(d.anrede, 'Guten Tag Karl Moser,');
  assert.deepEqual(d.liste, ['A.', 'B.', 'C.']);
  assert.match(d.absaetze[1], /mit Ihren Leistungen und Ihrer Adresse\.$/);
  assert.match(d.ps, /Rückseite sehen Sie Ihre heutige Website/);
});

test('Einsatzgebiet aus PLZ-Daten', () => {
  const daten = [
    { plz: '78462', ort: 'Konstanz', kreis: 'K', lat: 47.66, lng: 9.17 },
    { plz: '78467', ort: 'Konstanz', kreis: 'K', lat: 47.67, lng: 9.16 },
    { plz: '78476', ort: 'Allensbach', kreis: 'K', lat: 47.71, lng: 9.07 },
    { plz: '78315', ort: 'Radolfzell am Bodensee', kreis: 'K', lat: 47.74, lng: 8.97 },
    { plz: '88045', ort: 'Friedrichshafen', kreis: 'B', lat: 47.65, lng: 9.48 },
  ];
  const g = einsatzgebiet(daten, { name: 'Konstanz', lat: 47.665, lng: 9.17 }, 12);
  assert.equal(g.orte[0].name, 'Konstanz');
  assert.deepEqual(g.orte[0].plz, ['78462', '78467']);
  assert.ok(g.orte.some((o) => o.name === 'Allensbach'));
  assert.deepEqual(g.plz, ['78462', '78467', '78476']);
  assert.ok(g.plzAufAnfrage.includes('78315'));
});

test('Domain-Kandidaten, Telefon-Format, Slugs', () => {
  const k = domainKandidaten({ name: 'Elektro Moser GmbH', adresse: { ort: 'Konstanz' } });
  assert.ok(k.includes('https://www.elektro-moser.de/'));
  assert.ok(k.includes('https://www.moser-elektro.de/'));
  assert.equal(normTelefon('07531 / 91 49 70'), '+49 7531 91 49 70');
  assert.equal(normTelefon('+49 (0) 7531 / 5925-0'), '+49 7531 5925 0');
  assert.equal(normTelefon('0049 7531 123'), '+49 7531 123');
  assert.equal(slugify('Müller & Söhne GmbH'), 'mueller-soehne-gmbh');
});
