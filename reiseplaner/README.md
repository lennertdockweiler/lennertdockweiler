# Reiseplaner

Persönlicher Reiseplaner für Handy und Desktop, veröffentlicht als Artifact auf claude.ai:
https://claude.ai/artifact/HM4YKYcQFgxeCKjohMxnx5

## Funktionen

- **Abflugtafel**: nächste Reise mit Countdown, alle Reisen nach Geplant/Unterwegs/Vergangen
- **Ablauf**: Tag-für-Tag-Plan mit Flügen, Zügen, Unterkünften (Check-in/Check-out), Aktivitäten und Buchungsnummern
- **Import mit Claude**: Buchungsbestätigungen aus Gmail, als eingefügter Text oder als Screenshot auslesen lassen (PINs und Zahlungsdaten werden nicht übernommen)
- **Google Kalender**: Einträge mit korrekter Ortszeit eintragen; Ablauf als Text kopieren
- **Packliste**: abhaken, Grundliste, Vorschläge von Claude passend zu Ziel, Jahreszeit und Aktivitäten
- **Reisekasse**: Ausgaben erfassen, faire Aufteilung und Ausgleich („Alex zahlt Lennert 26,75 €“)
- **Notizen** pro Reise, teilbar mit Mitreisenden (Rolle „Contributor“)

## Technik

Eine einzelne HTML-Datei ohne Build-Schritt (`index.html`). Sie nutzt die Artifact-Laufzeit von claude.ai:

| Fähigkeit | Wofür |
|---|---|
| `db` | Reisen unter `trips/{id}`, darunter `items`, `packing`, `expenses` (Lesen und Schreiben ab Rolle Contributor) |
| `sample` | Claude liest Buchungen aus und schlägt Packlisten vor |
| `mcp` | Gmail (`search_threads`, `get_thread`), Google Calendar (`create_event`) |
| `user` | Schreibrechte erkennen, Kalender-Status pro Person |

Änderungen: Datei bearbeiten und in einer Claude-Code-Sitzung mit derselben Artifact-URL neu veröffentlichen.
