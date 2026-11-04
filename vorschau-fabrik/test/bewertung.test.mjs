import { test } from 'node:test';
import assert from 'node:assert/strict';
import { bewerte, briefBefunde } from '../src/bewertung.mjs';

const lead = { website: 'https://alt.example.de/' };
const gut = { erreichbar: true, https: true, viewportMeta: true, overflowPx: 0, kleineSchriftAnteil: 0.05, ladezeitMs: 1800, megabytes: 1.2, copyrightJahr: new Date().getFullYear(), impressumLink: true, telLink: true, telefonSichtbar: true, metaBeschreibung: true, finalUrl: 'https://alt.example.de/' };

test('keine Website = Score 0, nicht erreichbar = 5', () => {
  assert.equal(bewerte({}, { keineWebsite: true }).score, 0);
  const r = bewerte(lead, { erreichbar: false, fehler: 'Adresse nicht gefunden' });
  assert.equal(r.score, 5);
  assert.match(briefBefunde(r)[0].brief, /nicht erreichbar \(Adresse nicht gefunden\)/);
});

test('gute Website ohne Befunde', () => {
  const r = bewerte(lead, gut);
  assert.equal(r.score, 100);
  assert.equal(r.kategorie, 'gut');
});

test('typische Altlasten werden gewichtet und für den Brief sortiert', () => {
  const r = bewerte(lead, { ...gut, https: false, viewportMeta: false, copyrightJahr: 2016, ladezeitMs: 9100 });
  assert.equal(r.score, 100 - 25 - 25 - 15 - 15);
  assert.deepEqual(r.befunde.map((b) => b.code).slice(0, 2), ['kein-https', 'nicht-mobil']);
  assert.equal(briefBefunde(r).length, 3);
  assert.match(r.befunde.find((b) => b.code === 'langsam').brief, /In unserem Test/);
});

test('unsichere Befunde landen nicht im Brief', () => {
  // Impressum-Wort im HTML vorhanden → kein Vorwurf; keine Telefonnummer sichtbar → kein Tel-Befund
  const r = bewerte(lead, { ...gut, impressumLink: false, impressumImHtml: true, telLink: false, telefonSichtbar: false });
  assert.equal(r.befunde.length, 0);
  const traege = bewerte(lead, { ...gut, ladezeitMs: 5600 });
  assert.equal(briefBefunde(traege).length, 0, 'mittlere Ladezeit nur im Bericht, nicht im Brief');
});
