import { test } from 'node:test';
import assert from 'node:assert/strict';
import { oeffnungszeitenText, parseOeffnungszeiten } from '../src/oeffnungszeiten.mjs';

test('Werktage mit Mittagspause und Samstag', () => {
  const r = parseOeffnungszeiten('Mo-Fr 07:30-12:00,13:00-17:00; Sa 08:00-12:00');
  assert.deepEqual(r.regulaer, [
    { tage: ['mo', 'di', 'mi', 'do', 'fr'], von: '07:30', bis: '12:00' },
    { tage: ['mo', 'di', 'mi', 'do', 'fr'], von: '13:00', bis: '17:00' },
    { tage: ['sa'], von: '08:00', bis: '12:00' },
  ]);
  assert.equal(oeffnungszeitenText(r), 'Mo–Fr 07:30–12:00 · Mo–Fr 13:00–17:00 · Sa 08:00–12:00');
});

test('spätere Regel überschreibt frühere, Feiertage werden ignoriert', () => {
  const r = parseOeffnungszeiten('Mo-Fr 08:00-18:00; We off; PH off');
  assert.deepEqual(r.regulaer, [{ tage: ['mo', 'di', 'do', 'fr'], von: '08:00', bis: '18:00' }]);
});

test('einstellige Stunden, Tageslisten, Kommentar', () => {
  const r = parseOeffnungszeiten('Mo,We 9:00-12:00 "Termine nach Vereinbarung"');
  assert.deepEqual(r.regulaer, [{ tage: ['mo', 'mi'], von: '09:00', bis: '12:00' }]);
  assert.equal(r.hinweis, 'Termine nach Vereinbarung');
});

test('24/7', () => {
  assert.deepEqual(parseOeffnungszeiten('24/7').regulaer, [{ tage: ['mo', 'di', 'mi', 'do', 'fr', 'sa', 'so'], von: '00:00', bis: '24:00' }]);
});

test('komplexe Regeln → null statt falscher Angaben', () => {
  assert.equal(parseOeffnungszeiten('Jan-Mar Mo-Fr 08:00-16:00'), null);
  assert.equal(parseOeffnungszeiten('Mo-Fr sunrise-sunset'), null);
  assert.equal(parseOeffnungszeiten(''), null);
  assert.equal(parseOeffnungszeiten(undefined), null);
});
