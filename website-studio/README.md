# Website-Studio · Prompt-Paket für Claude

Mit diesem Paket entwirft und entwickelt Claude vollständige Kunden-Websites in Agenturqualität: gutes Design, starke Texte, schnell, barrierefrei, SEO-optimiert und datenschutzfreundlich. Es funktioniert für jede Branche und lässt sich danach per Prompt anpassen.

## Inhalt

| Datei | Wofür |
|---|---|
| `MASTER-PROMPT.md` | Der Haupt-Prompt: Rolle, Workflow, Strategie, Texte, Design, Sektionen, Technik, Performance, SEO, Barrierefreiheit, Recht, Funktionen, Bilder, Anpassungs-Befehle, Qualitätssicherung, Übergabe und eine Bibliothek mit 26 Branchenprofilen |
| `BRIEFING-VORLAGE.md` | Kunden-Briefing zum Ausfüllen: Schnellstart, vollständige Fassung und ein Beispiel |
| `generator.html` | Briefing-Generator im Browser: Formular ausfüllen, Branche wählen, fertigen Prompt kopieren |
| `tools/` | Quelle und Build-Skript des Generators |

## Schnellstart in drei Schritten

1. **Master-Prompt hinterlegen**, siehe Varianten A–C unten.
2. **Briefing senden:** Vorlage ausfüllen oder den Generator nutzen. Minimum: Branche, Firmenname, Ort, Leistungen.
3. **Anpassen:** frei formulieren oder Befehle nutzen, z. B. `STIL: edler`, `SEKTION NEU: FAQ auf Startseite`, `PRÜFEN`.

## Variante A · Claude Code (empfohlen für echte Kundenprojekte)

Hier baut Claude ein echtes, deploybares Projekt (Astro), testet es selbst (Build, Screenshots, Barrierefreiheit, Lighthouse) und schreibt die Übergabedokumentation.

Lege einmalig einen Studio-Ordner an, mit dem Master-Prompt als `CLAUDE.md`. Claude Code liest `CLAUDE.md` auch aus übergeordneten Ordnern, deshalb gilt der Prompt automatisch für jedes Kundenprojekt darunter.

```bash
mkdir -p ~/website-studio/kunden
```

```bash
cp MASTER-PROMPT.md ~/website-studio/CLAUDE.md
```

Für jeden neuen Kunden einen Unterordner anlegen, das ausgefüllte Briefing als `BRIEFING.md` hineinlegen (dazu Logo und Fotos, falls vorhanden) und Claude Code dort starten:

```bash
mkdir -p ~/website-studio/kunden/morgenroth && cd ~/website-studio/kunden/morgenroth && claude
```

Dann in Claude schreiben:

> Lies BRIEFING.md und erstelle die Website.

Hinweise:
- Der Master-Prompt ist lang (rund 90.000 Zeichen inklusive aller Branchen). Claude Code zeigt bei so großen `CLAUDE.md`-Dateien eventuell einen Hinweis zur Größe an; das ist unkritisch. Wenn du Kontext sparen willst, erzeugst du im Generator eine Fassung mit nur deiner Branche (Ausgabe „Komplett“, Branchen „Nur gewählte“) und nutzt sie als `CLAUDE.md`.
- Mit Web-Zugriff recherchiert Claude die alte Website und Wettbewerber und kann lizenzfreie Fotos einbinden. Hinterlegst du einen `UNSPLASH_ACCESS_KEY` oder `PEXELS_API_KEY` als Umgebungsvariable, nutzt Claude die offizielle API.

## Variante B · Claude-Projekt auf claude.ai

1. Neues Projekt anlegen, z. B. „Website-Studio“.
2. Den Inhalt von `MASTER-PROMPT.md` in die Projektanweisungen einfügen oder die Datei als Projektwissen hochladen.
3. Pro Kunde einen neuen Chat starten und das Briefing senden (im Generator: Ausgabe „Nur Briefing“).

Im Chat arbeitet Claude im **Vorschaumodus**: Er liefert eine vollständige Startseite als HTML-Artefakt und weitere Seiten auf Anfrage. Ideal für Pitch-Demos und Abstimmungen; für den Livegang ist Variante A gedacht.

## Variante C · Einzelner Chat

Im Generator „Komplett“ wählen und den kopierten Prompt als erste Nachricht senden. Er enthält Master-Prompt, Branchenprofil und Briefing.

## Anpassen per Prompt

Freie Formulierungen funktionieren immer. Für schnelle, eindeutige Änderungen gibt es Befehle:

| Befehl | Beispiel |
|---|---|
| `STIL:` | `STIL: edler und ruhiger, mehr Weißraum` |
| `FARBEN:` | `FARBEN: aus dem Logo ableiten` oder `FARBEN: 3 Vorschläge` |
| `SCHRIFT:` | `SCHRIFT: 3 Vorschläge, eher klassisch` |
| `TON:` | `TON: du-Form, lockerer` |
| `TEXT:` | `TEXT: Hero – mehr Fokus auf schnelle Termine` |
| `SEKTION NEU:` / `SEKTION WEG:` / `SEKTION VARIANTE:` | `SEKTION NEU: Ablauf auf Startseite nach Leistungen` |
| `VARIANTEN:` | `VARIANTEN: Hero 3` |
| `SEITE NEU:` | `SEITE NEU: Wärmepumpe – Leistungsseite` |
| `FUNKTION:` | `FUNKTION: Online-Termin über Doctolib` |
| `BILDER:` | `BILDER: Fotos aus /fotos einsetzen` |
| `SEO:` | `SEO: Fokus Badsanierung Bielefeld` |
| `SPRACHE:` | `SPRACHE: Englisch ergänzen` |
| `DATEN:` | `DATEN: Freitag nur bis 13 Uhr geöffnet` |
| `POLIEREN` · `PRÜFEN` · `ERKLÄREN` · `PITCH` · `STATUS` · `ÜBERGABE` | ohne Zusatz |

Die vollständige Liste mit Wirkung steht im Master-Prompt im Abschnitt `<anpassung>`.

## Branche festlegen oder spezialisieren

- Die Branchen-Bibliothek enthält 26 Profile, von Handwerk über Praxen und Kanzleien bis Gastronomie. Für andere Branchen leitet Claude selbst ein Profil nach demselben Schema ab.
- **Wenn du dich auf eine Branche spezialisierst**, lohnt es sich, ihr Profil im Master-Prompt mit deinem Wissen auszubauen: typische Kundenfragen, bewährte Seitenstrukturen, Tools der Branche, Formulierungen, die funktionieren. Die anderen Profile kannst du löschen.
- Nach Änderungen am Master-Prompt den Generator neu bauen:

```bash
python3 tools/build-generator.py
```

## Tipps für Top-Ergebnisse

- **Echtes Material schlägt alles:** echte Fotos, Belege (Zahlen, Zertifikate), Kundenstimmen und die URL der alten Website.
- **Vorbilder nennen** (mit Begründung, was gefällt), **No-Gos nennen.**
- **Pitch-Demo zuerst:** Für Akquise `PROJEKTZWECK: pitch-demo`, danach mit echten Daten auf `produktion` umstellen.
- **Vor der Übergabe immer `PRÜFEN`** und die `TODO-LIVEGANG.md` abarbeiten.

## Grenzen & Verantwortung

- **Rechtstexte** (Impressum, Datenschutzerklärung, AGB) erstellt Claude als strukturierte Entwürfe. Lass sie über einen Generator (z. B. eRecht24, Datenschutz-Generator von Dr. Schwenke) oder anwaltlich prüfen. Die rechtlichen Hinweise im Prompt entsprechen dem Stand November 2026.
- **Fakten:** Claude erfindet keine Bewertungen, Zahlen oder Zertifikate. Fehlende Angaben werden als Platzhalter markiert und in `TODO-LIVEGANG.md` gesammelt.
- **Externe Tools** (Buchungssysteme, Maklersoftware, Formular-Backends) brauchen Zugänge des Kunden; Claude bindet sie datenschutzfreundlich ein.
