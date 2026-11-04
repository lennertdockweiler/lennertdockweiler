# Vorschau-Fabrik

Vom Lead zur fertigen Demo-Website **und zum Brief** – automatisch. Die Fabrik findet Handwerksbetriebe
einer Stadt, prüft ihre Websites, baut mit dem **handwerker-template** für jeden Betrieb einen
persönlichen Entwurf und erzeugt einen druckfertigen Brief mit QR-Code zu diesem Entwurf.

**Es werden keine E-Mails verschickt.** Werbe-E-Mails an Firmen sind in Deutschland ohne vorherige
Einwilligung unzulässig (§ 7 UWG). Ergebnis sind Brief-PDFs zum Ausdrucken und Versenden.

```
OpenStreetMap ─▶ Website-Check ─▶ site.config.json ─▶ Astro-Build ─▶ Screenshots ─▶ Brief (PDF, DIN 5008)
   Leads           Befunde, Score     handwerker-template   dist/<slug>    vorher/nachher   QR-Code → Entwurf
```

## Was am Ende herauskommt

Pro Lauf liegt alles in `ausgabe/<lauf>/`:

| Datei | Inhalt |
|---|---|
| `bericht.html` | Übersicht aller Betriebe: Score, Befunde, Screenshots, Lücken im Entwurf, Links |
| `briefe/alle-briefe.pdf` | Alle Briefe in einer Datei, **duplex drucken** (Seite 2 = Rückseite mit Vorher/Nachher) |
| `briefe/<slug>.pdf` | Einzelbrief |
| `briefe/adressen.csv` | Adressen für Etiketten/Serienbrief (Excel-kompatibel) |
| `vergleich/<slug>.png` | Vorher/Nachher-Bild (z. B. fürs Gespräch) |
| `leads.json` | Alle Rohdaten des Laufs |

Die Entwürfe selbst sind normale Varianten im Template (`variants/<slug>/`) und werden wie gewohnt
mit `npm run publish` nach `website-entwuerfe` veröffentlicht.

## Einrichtung (einmalig)

1. **Template-Branch mit optionalem Gründungsjahr** einspielen (`handwerker-template`, Branch
   `claude/bold-carson-trxjm8`). Ohne ihn müsste die Fabrik ein Gründungsjahr erfinden.
2. Template-Abhängigkeiten: `cd handwerker-template && npm ci`
3. Fabrik: `cd vorschau-fabrik && npm install`
   Lokal zusätzlich Playwright: `npm install playwright && npx playwright install chromium`
   (In Claude-Cloud-Sessions ist Chromium schon da.)
4. `fabrik.config.json` prüfen: Agentur-Angaben (erscheinen im Brief und im Demo-Banner),
   Pfad zum Template (Standard: `handwerker-template` neben diesem Repo, sonst `FABRIK_TEMPLATE=/pfad`).

## Benutzung

```bash
# Alles in einem Rutsch: Leads → Check → 10 Entwürfe → Screenshots → Briefe → Bericht
node src/cli.mjs alles --ort Konstanz --gewerk maler,elektro --region "am Bodensee" --anzahl 10
```

Einzelschritte (ohne `--lauf` gilt immer der zuletzt bearbeitete Lauf):

| Befehl | Was passiert |
|---|---|
| `leads --ort <Ort> --gewerk <liste\|alle>` | Betriebe aus OpenStreetMap, Adressen ergänzen, Sperrliste anwenden. `--umkreis 15` sucht im Radius statt im Gemeindegebiet. |
| `pruefen` | Domain-Suche für Betriebe ohne Website, dann Website-Check im Smartphone-Modus |
| `vorschauen [--anzahl 10] [--max-score 60] [--nur a,b]` | Varianten schreiben, `variant:check`, bauen |
| `bilder` | Screenshots (mobil/desktop) und Vorher/Nachher-Bild |
| `briefe [--datum 2026-11-10]` | Brief-PDFs, Sammel-PDF, Adress-CSV |
| `bericht` | `bericht.html` neu erzeugen |
| `veroeffentlichen --ja` | ruft `npm run publish -- <slugs>` im Template auf (öffentlich, noindex) |
| `gewerke` | Gewerke und OSM-Zuordnung |

Gewerke: `elektro, shk, dachdecker, zimmerei, tischler, maler, fliesen, metallbau, galabau, bau, allgemein`
(auch `elektriker`, `schreiner`, `sanitär`, `gärtner` … werden verstanden).

**Reihenfolge vor dem Versand:** `alles` → Bericht durchsehen (Lücken!) → Entwürfe ggf. veredeln →
`veroeffentlichen --ja` → Links testen → `briefe` → drucken.

## Score und Befunde

0 = dringender Bedarf, 100 = gute Website. Bewertet werden u. a. HTTPS, Smartphone-Tauglichkeit,
Ladezeit, Seitengewicht, veraltetes Copyright, Impressum-Link, extern geladene Google Fonts,
antippbare Telefonnummer und Seitenbeschreibung. In den Brief kommen höchstens drei Befunde, und nur
solche, die eindeutig messbar sind (z. B. „Kein Impressum“ nur, wenn das Wort nirgends im HTML steht).

Betriebe ohne Website in OpenStreetMap werden vorher per **Domain-Suche** geprüft
(`elektro-moser.de`, `moser-elektro.de` …). Im Testlauf Konstanz hatten so 4 von 12 vermeintlich
„websitelosen“ Betrieben doch eine Website. Trotzdem: Im Bericht steht bei jedem Betrieb ohne Website
ein Link „Google-Suche prüfen“ – vor dem Versand kurz anklicken.

## Ehrlichkeit der Entwürfe

Die Entwürfe zeigen echte Betriebe öffentlich (noindex, nicht verlinkt). Deshalb erfindet die Fabrik nichts:

- **Keine Bewertungen**, keine Mitarbeiterzahlen, keine Referenzen, keine Stellenanzeigen, keine fremden Fotos (Platzhalter).
- **Meisterbetrieb** nur, wenn Impressum Handwerkskammer und Handwerksrollen-Nr. nennt; sonst werden
  Preset-Texte wie „vom Meisterbetrieb“ neutral umformuliert.
- **Notdienst** nie: Notdienst-Leistungen, -FAQ und Texte wie „Cool im Notfall“ werden entfernt.
- **Gründungsjahr** nur, wenn es auf der Website steht („seit 1864“) oder in OSM; sonst entfallen alle „Seit …“-Angaben.
- Übernommen werden: Name, Adresse, Koordinaten, Telefon/E-Mail/Öffnungszeiten (OSM oder Impressum),
  Markenfarben der alten Website, Register- und USt-Angaben aus dem Impressum.
- Fehlt etwas (z. B. Telefon), steht es als **„Lücke im Entwurf“** im Bericht. Das Demo-Banner sagt
  „Unverbindlicher Entwurf von … – Inhalte teils beispielhaft“.

## Rechtliches

- **Brief statt E-Mail** (§ 7 UWG). Briefwerbung an Firmen ist zulässig, solange kein Widerspruch vorliegt.
- Jeder Brief enthält einen **Datenschutzhinweis** mit Quelle der Adresse und dem **Widerspruchsrecht
  (Art. 21 DSGVO)**. Wer widerspricht, kommt in `sperrliste.txt` (Vorlage: `sperrliste.beispiel.txt`)
  und wird nie wieder angeschrieben – Datei dauerhaft aufbewahren.
- Der Brief verspricht, den Entwurf nach `loeschenNachWochen` (Standard 6) zu löschen – daran halten.
- Daten: © OpenStreetMap-Mitwirkende (ODbL), PLZ/Orte: GeoNames (CC BY 4.0). Beides steht in den
  `CREDITS.md` der Varianten und damit im Impressum der Entwürfe.
- Keine Rechtsberatung – bei Unsicherheit kurz anwaltlich prüfen lassen.

## Mit Claude in der Cloud

Die Fabrik ist für Claude-Code-Cloud-Sessions gebaut (siehe `CLAUDE.md`). Typische Aufträge:

- „Lauf die Vorschau-Fabrik für Dachdecker in Singen und Radolfzell, 8 Entwürfe.“
- „Veredle die Entwürfe aus dem letzten Lauf“ – Claude liest die Website-Texte in `texte/<slug>.json`,
  ergänzt Inhaber, Gründungsjahr, Leistungen und Öffnungszeiten aus belegten Angaben, prüft und baut neu.
  Veredelte Varianten tragen `"veredelt": true` im Block `//fabrik` und werden danach nie mehr überschrieben.
- Mehrere Städte gleichzeitig: je Stadt eine eigene Session.

## Tests

```bash
npm test
```
