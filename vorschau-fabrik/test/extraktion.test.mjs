import { test } from 'node:test';
import assert from 'node:assert/strict';
import { emailAus, extrahiere, gruendungsjahrAus, impressumFakten, inhaberAus, kurznameAus, meisterAus, rechtsformAus } from '../src/extraktion.mjs';

test('Inhaber aus typischen Impressum-Formulierungen', () => {
  assert.equal(inhaberAus('Inhaber: Thomas Müller\nTelefon: 0751 1234'), 'Thomas Müller');
  assert.equal(inhaberAus('Vertreten durch den Geschäftsführer: Dr. Anna-Lena Berg'), 'Dr. Anna-Lena Berg');
  assert.equal(inhaberAus('Geschäftsführer\nHans Peter Schmidt, Maria Schmidt'), 'Hans Peter Schmidt');
  assert.equal(inhaberAus('Vertreten durch: die Komplementär-GmbH'), undefined);
});

test('Kurzname und Rechtsform', () => {
  assert.equal(kurznameAus('Elektro Moser GmbH & Co. KG'), 'Elektro Moser');
  assert.equal(kurznameAus('Malerbetrieb Huber e.K.'), 'Malerbetrieb Huber');
  assert.equal(kurznameAus('Schreinerei Müller - Inh. Peter Müller'), 'Schreinerei Müller');
  assert.ok(kurznameAus('Meisterbetrieb für Sanitär und Heizung Hans Peter Schmidt-Meier').length <= 32);
  assert.equal(rechtsformAus('Muster UG (haftungsbeschränkt)'), 'UG (haftungsbeschränkt)');
  assert.equal(rechtsformAus('Beispiel GmbH & Co. KG'), 'GmbH & Co. KG');
});

test('E-Mail auch verschleiert, keine Bilddateien', () => {
  assert.equal(emailAus('Schreiben Sie an info (at) maler-huber (dot) de'), 'info@maler-huber.de');
  assert.equal(emailAus('logo@2x.png kontakt@elektro.de'), 'kontakt@elektro.de');
});

test('Gründungsjahr: frühestes plausibles Jahr, keine Zukunft', () => {
  assert.equal(gruendungsjahrAus('Malerbetrieb aus Konstanz – seit 1864', 'Gegründet 1999'), 1864);
  assert.equal(gruendungsjahrAus('seit 2099 dabei'), undefined);
  assert.equal(gruendungsjahrAus('seit Jahren zuverlässig'), undefined);
});

test('Meisterbetrieb und Impressum-Fakten', () => {
  assert.deepEqual(meisterAus('Ihr Meisterbetrieb in Konstanz'), { meisterbetrieb: true, meisterTitel: undefined });
  assert.equal(meisterAus('Bürgermeister Müller lobt').meisterbetrieb, false);
  const f = impressumFakten('Handwerkskammer Konstanz\nWebersteig 3, 78462 Konstanz\nEingetragen in die Handwerksrolle Nr. 12345\nUSt-IdNr.: DE 123 456 789\nAmtsgericht Freiburg HRB 7001');
  assert.equal(f.handwerkskammer, 'Handwerkskammer Konstanz');
  assert.equal(f.handwerkskammerAdresse, 'Webersteig 3, 78462 Konstanz');
  assert.equal(f.handwerksrolleNr, '12345');
  assert.equal(f.ustId, 'DE123456789');
  assert.equal(f.registergericht, 'Amtsgericht Freiburg');
  assert.equal(f.registernummer, 'HRB 7001');
  const ohneAdresse = impressumFakten('Handwerkskammer Konstanz\n\nBetriebsnummer: 44188\n\nUst-ID-Nr.: DE 269160429');
  assert.equal(ohneAdresse.handwerkskammerAdresse, undefined);
  assert.equal(ohneAdresse.handwerksrolleNr, '44188');
});

test('extrahiere kombiniert die Quellen', () => {
  const x = extrahiere({ start: 'Tradition seit 1952. Tel. 07531 123456', impressum: 'Inhaber: Eva Kunz\nE-Mail: info@kunz.de' });
  assert.equal(x.inhaber, 'Eva Kunz');
  assert.equal(x.email, 'info@kunz.de');
  assert.equal(x.gruendungsjahr, 1952);
});
