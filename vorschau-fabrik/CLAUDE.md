# Vorschau-Fabrik – Hinweise für Claude

Dieses Werkzeug erzeugt Demo-Websites (handwerker-template) und Werbebriefe für echte Betriebe.
Lies `README.md` für Befehle und Hintergrund. Arbeite auf Deutsch.

## Harte Regeln

- **Niemals E-Mails, Nachrichten oder Kontaktformulare an Betriebe senden.** Ergebnis sind nur Brief-PDFs.
- **Nichts erfinden.** Keine Bewertungen, Kennzahlen, Referenzen, Mitarbeiterzahlen, Meister- oder
  Notdienst-Aussagen ohne Beleg aus `texte/<slug>.json` (Website-Text) oder OpenStreetMap.
- **Nicht veröffentlichen** (`veroeffentlichen --ja`, `npm run publish`), ohne dass der Nutzer es in
  diesem Gespräch ausdrücklich freigibt. Veröffentlichen pusht in ein öffentliches Repo.
- `meta.noindex` bleibt `true`, das Demo-Banner bleibt aktiv.
- Betriebe aus `sperrliste.txt` nie wieder aufnehmen.

## Ablauf eines Auftrags

1. `npm install` (Fabrik) und `npm ci` im Template, falls `node_modules` fehlen.
2. `node src/cli.mjs alles --ort <Ort> --gewerk <gewerke> --anzahl <n> [--region "am …"]`
3. `ausgabe/<lauf>/bericht.html` auswerten: Lücken, Befunde, Betriebe ohne Website.
4. Auf Wunsch **veredeln** (siehe unten), dann `vorschauen --nur <slugs>`, `bilder`, `briefe`, `bericht`.
5. Dem Nutzer berichten: Anzahl Leads, gebaute Entwürfe, offene Lücken, Pfad zu `briefe/alle-briefe.pdf`.
   PDFs und Vergleichsbilder mit SendUserFile schicken.

## Veredeln eines Entwurfs

Für `variants/<slug>/site.config.json` im Template, Quelle `ausgabe/<lauf>/texte/<slug>.json`:

- `betrieb.inhaber`, `rechtliches.vertretungsberechtigt`: nur aus dem Impressum.
- `betrieb.gruendungsjahr`: nur bei eindeutiger Angabe („seit 1987“, „gegründet 1987“).
- `leistungen`: Preset-Leistungen abwählen, die der Betrieb laut Website nicht anbietet;
  eigene Leistungen nur mit Beleg (dann `titel`, `kurztext`, `text`, `icon` Pflicht).
- `oeffnungszeiten`, `telefon`, `email`: aus Website/Impressum, wenn im Entwurf Platzhalter stehen.
- `meisterbetrieb: true` nur mit Handwerkskammer **und** Handwerksrollen-Nr.
- Texte (`texte.*`) dürfen konkreter werden, aber keine neuen Versprechen enthalten.
- Danach in der Config `"//fabrik": { …, "veredelt": true }` setzen. Veredelte Varianten
  überschreibt die Fabrik nicht mehr, sie prüft und baut sie nur:
  `node src/cli.mjs vorschauen --nur <slug>`, dann `bilder` und `briefe`.

## Entwickeln

- Node ≥ 20, ESM, keine Build-Schritte. Tests: `npm test` (node:test).
- Playwright wird über `createRequire` geladen (lokal oder global vorinstalliert, siehe `src/util.mjs`).
- Overpass-Server sind zeitweise überlastet (429/504) – `src/osm.mjs` wechselt automatisch.
