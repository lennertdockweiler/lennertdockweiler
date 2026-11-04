# Lead-Scout · Firmen finden & Online-Präsenz bewerten

Branche und Ort eingeben, zum Beispiel „Friseur“ in „Bielefeld“. Lead-Scout sucht passende Firmen, prüft **Website, Instagram und TikTok** und sortiert alles nach **Potenzial für eure Agentur**. Zu jeder Firma gibt es konkrete **Ansatzpunkte fürs Erstgespräch**, etwa „Website nicht für Smartphones optimiert“, „Instagram seit 140 Tagen inaktiv“ oder „Kein TikTok, keine der 20 Firmen dieser Suche ist dort“.

- Läuft lokal auf eurem Rechner, mit einer Oberfläche im Browser oder über die Kommandozeile.
- Braucht nur **Python 3.9+**, keine Zusatzpakete.
- Ergebnis: ein interaktiver **HTML-Bericht** (Filter, Suche, Details, „Notiz kopieren“), eine **CSV für Excel/CRM** und die Rohdaten als JSON.

## Inhalt

1. [Schnellstart](#schnellstart)
2. [Bedienung](#bedienung)
3. [Datenquellen einrichten](#datenquellen-einrichten): Google, Instagram (Meta), TikTok, OpenStreetMap
4. [Was geprüft wird](#was-geprüft-wird)
5. [Bewertung: Präsenz, Potenzial, Ansatzpunkte](#bewertung-präsenz-potenzial-ansatzpunkte)
6. [Fairness, Grenzen und Recht](#fairness-grenzen-und-recht)
7. [Fehlerbehebung](#fehlerbehebung)
8. [Für Entwickler](#für-entwickler)

## Schnellstart

1. **Python installieren** (falls noch nicht vorhanden): [python.org/downloads](https://www.python.org/downloads/). Auf dem Mac danach einmal im Ordner „Programme/Python 3.x“ die Datei **„Install Certificates.command“** doppelklicken.
2. **Lead-Scout starten** – im Terminal im Ordner `lead-scout`:

   ```bash
   python3 leadscout.py
   ```

   Unter Windows heißt der Befehl `py leadscout.py`. Der Browser öffnet sich mit der Eingabemaske (Adresse `http://127.0.0.1:8765`).
3. **Branche und Ort eingeben** und „Suche starten“. Ohne weitere Einrichtung sucht Lead-Scout kostenlos über OpenStreetMap.
4. Für **vollständige Ergebnisse aus Google Maps** einen Google-Schlüssel hinterlegen (10 Minuten, siehe unten). Das ist der wichtigste Schritt.

Einstellungen stehen in der Datei `.env`. Einmalig anlegen:

```bash
cp .env.example .env
```

## Bedienung

### Oberfläche

- **Branche & Ort:** Mehrere Begriffe mit Komma trennen, z. B. „Friseur, Barbershop“ und „Bielefeld, Gütersloh“. Jede Kombination wird einzeln gesucht, doppelte Firmen werden zusammengeführt.
- **Firmen pro Suche:** 20, 40 oder 60 (Google liefert höchstens 60 pro Suchbegriff und Ort). Für große Städte lieber nach Stadtteilen suchen, z. B. „Köln-Ehrenfeld, Köln-Nippes“.
- **Quelle:** Google Maps (empfohlen), OpenStreetMap (kostenlos) oder **eigene Liste** (eine Firma pro Zeile: `Name; Website`, nur `website.de` oder `Name; Ort`).
- **Prüfungen:** TikTok, Instagram-Kennzahlen (wenn Meta eingerichtet) und optional **PageSpeed** (echte mobile Ladezeit von Google, ca. 20 Sekunden pro Website).
- **Verbindungen testen** zeigt, ob Schlüssel und Dienste funktionieren.

### Kommandozeile

```bash
python3 leadscout.py "Friseur" "Bielefeld"
```

```bash
python3 leadscout.py "Friseur, Barbershop" "Bielefeld, Gütersloh" --anzahl 40 --pagespeed
```

```bash
python3 leadscout.py --liste firmen.txt
```

```bash
python3 leadscout.py --pruefen
```

Alle Optionen: `python3 leadscout.py --help`

### Der Bericht

Berichte landen im Ordner `berichte/` (HTML, CSV, JSON) und sind in der Oberfläche unter „Berichte“ verlinkt.

- **Kopfbereich:** Marktüberblick der Suche (wie viele haben eine Website, sind mobil optimiert, auf Instagram, auf TikTok) und „Vorbilder dieser Suche“ – praktisch als Vergleich im Gespräch.
- **Filter:** Potenzial hoch · Ohne Website · Website schwach · Ohne Instagram · Ohne TikTok · Social inaktiv · Rechtliche Mängel, plus Suche und Sortierung.
- **Details pro Firma** (Zeile anklicken): alle Website-Prüfungen mit Punkten, Instagram- und TikTok-Kennzahlen, weitere Kanäle, Kontaktdaten und die vollständige Liste der Ansatzpunkte.
- **Notiz kopieren:** kompakte Zusammenfassung für CRM oder Telefonnotiz.
- **Briefing für Pitch-Demo:** kopiert ein ausgefülltes Kunden-Briefing im Format des [Website-Studios](../website-studio/README.md) (`PROJEKTZWECK: pitch-demo`). So wird aus einem Website-Lead in wenigen Minuten eine Demo-Website fürs Erstgespräch.
- **Auswahl als CSV:** exportiert genau die gefilterte Liste (Excel-tauglich, Semikolon, UTF-8).

## Datenquellen einrichten

### Google-Schlüssel (Firmensuche + PageSpeed)

Lead-Scout nutzt die offizielle **Places API (New)**, also dieselben Daten wie Google Maps: Name, Adresse, Telefon, Website, Bewertung, Anzahl Rezensionen, Öffnungsstatus.

1. [console.cloud.google.com](https://console.cloud.google.com/) öffnen und ein Projekt anlegen, z. B. „Lead-Scout“.
2. **Abrechnung aktivieren** (Rechnungskonto). Google verlangt das auch für das Freikontingent.
3. Unter „APIs & Dienste → Bibliothek“ aktivieren:
   - **Places API (New)**
   - **PageSpeed Insights API** (für die Ladezeit-Messung)
4. Unter „APIs & Dienste → Anmeldedaten“: **API-Schlüssel erstellen**. Empfohlen: den Schlüssel unter „API-Einschränkungen“ auf genau diese zwei APIs beschränken.
5. Schlüssel in die `.env` eintragen: `GOOGLE_API_KEY=…` und mit `python3 leadscout.py --pruefen` testen.

**Kosten:** Eine Suche mit 20 Firmen ist eine Anfrage, 60 Firmen sind drei. Weil Lead-Scout Website, Telefon und Bewertungen abfragt, zählt das zur SKU „Text Search Enterprise“. Google gewährt pro SKU ein monatliches Freikontingent (Stand 2025: 1.000 Anfragen für Enterprise-SKUs). Darüber hinaus kostet eine Anfrage wenige Cent. Aktuelle Preise: [Google-Maps-Preisliste](https://developers.google.com/maps/billing-and-pricing/pricing). Tipp: In der Cloud Console ein **Budget mit Benachrichtigung** anlegen. Die PageSpeed Insights API ist kostenlos (großzügiges Tageskontingent).

### Instagram-Kennzahlen (Meta Graph API, optional)

Ohne Einrichtung erkennt Lead-Scout Instagram-Profile (auf der Website verlinkt, im Google-Eintrag, auf Linktree & Co.) und verlinkt sie im Bericht. **Für Kennzahlen** (Follower, letzter Beitrag, Beiträge pro Monat, Reels-Anteil, Engagement-Rate) nutzt Lead-Scout ausschließlich die offizielle **Business Discovery** der Meta Graph API. Instagram-Seiten werden **nicht** gescrapt.

Voraussetzung: euer eigenes Instagram-Konto ist ein **professionelles Konto** (Business oder Creator) und mit einer **Facebook-Seite** verknüpft. Für eine Social-Media-Agentur ist das meist schon der Fall.

1. Auf [developers.facebook.com](https://developers.facebook.com/) unter „Meine Apps“ eine App erstellen (Typ „Business“ bzw. Anwendungsfall für Instagram mit Facebook-Login). Für die eigene Nutzung reicht in der Regel der Entwicklungsmodus.
2. Im [Graph API Explorer](https://developers.facebook.com/tools/explorer/) die App wählen, „User Token“ erzeugen und diese Berechtigungen anhaken: `instagram_basic`, `pages_show_list`, `pages_read_engagement` (liegt die Seite in einem Business-Portfolio, zusätzlich `business_management`). „Generate Access Token“, einloggen und Seite und Instagram-Konto freigeben.
3. Den Token im [Access Token Debugger](https://developers.facebook.com/tools/debug/accesstoken/) einfügen und unten auf **„Extend Access Token“** klicken. Das ergibt einen Token, der rund 60 Tage gilt.
4. In die `.env` eintragen: `META_ACCESS_TOKEN=…`
5. `python3 leadscout.py --pruefen` ausführen. Lead-Scout zeigt die ID eures Instagram-Kontos an. Diese als `META_IG_USER_ID=…` eintragen und erneut prüfen.

Hinweise:
- Kennzahlen gibt es nur für **Business- und Creator-Konten**. Private oder persönliche Konten erscheinen als „kein Business-Konto“.
- Meta begrenzt die Abfragen (etwa 200 pro Stunde). Bei sehr großen Suchen meldet Lead-Scout das und arbeitet ohne Kennzahlen weiter.
- Ist auf einer Website kein Instagram verlinkt, probiert Lead-Scout über die Meta-API zwei naheliegende Namen aus der Domain (z. B. `friseur-sivo.de` → `friseursivo`). Ein Treffer zählt nur, wenn im gefundenen Profil **dieselbe Website** hinterlegt ist.
- Token alle 60 Tage erneuern (Schritte 2–4). Für einen dauerhaften Token kann im Meta Business Manager ein Systembenutzer angelegt werden.

### TikTok (keine Einrichtung nötig)

- **Existenz** eines Profils prüft Lead-Scout über die offizielle **oEmbed-Schnittstelle** von TikTok.
- **Kennzahlen** (Follower, Likes, letzte Videos, Ø Aufrufe, Videos pro Monat) kommen aus dem öffentlichen **Creator-Embed**, dem Profil-Widget, das TikTok zum Einbetten auf Websites anbietet.
- Abrufe sind gedrosselt (mindestens 2 Sekunden Abstand, ehrlicher User-Agent). Begrenzt TikTok, stoppt Lead-Scout die TikTok-Prüfung für diesen Lauf und vermerkt das im Bericht.
- Das Embed kann TikTok jederzeit ändern. Dann fehlen die Kennzahlen, die Existenzprüfung funktioniert weiter.

### OpenStreetMap (kostenlos)

Ohne Google-Schlüssel sucht Lead-Scout in OpenStreetMap (Overpass, ersatzweise Nominatim). Gut zum Ausprobieren, aber deutlich **unvollständiger**: Es fehlen Bewertungen, und bei vielen Einträgen ist keine Website hinterlegt. Solche Firmen erscheinen deshalb als **„Website unbekannt“ (Merkmal „Wenig Daten“)**, nicht als „ohne Website“, und rutschen im Potenzial nach unten. Die Branche wird über eine Stichwortliste (rund 100 Branchen) auf OSM-Merkmale übertragen. Unbekannte Begriffe werden im Firmennamen gesucht.

## Was geprüft wird

**Website** (Startseite plus Impressum/Kontakt, maximal drei Seiten)

| Bereich | Prüfungen |
|---|---|
| Erreichbarkeit | Domain erreichbar, SSL-Zertifikat gültig, Weiterleitung auf fremde Domain, Baustellen-/Parkseite, defekte Links aus dem Google-Profil, abgeschaltete Google-Websites (business.site) |
| Technik | HTTPS, Mobil-Optimierung (Viewport), Server-Antwortzeit oder PageSpeed (mobil), CMS/Baukasten (WordPress, Wix, Jimdo, IONOS/Strato …), Baukasten-Subdomain statt eigener Domain |
| Aktualität | Copyright-Jahr, veraltete Technik (Frames, Laufschrift, Flash, sehr alte jQuery-Version) |
| SEO-Grundlagen | Seitentitel, Meta-Beschreibung, H1, strukturierte Daten, Vorschaubild für WhatsApp & Social Media, Sprache, `noindex`, robots.txt sperrt Google |
| Recht & DSGVO | Impressum, Datenschutzerklärung, Google Fonts von Google-Servern, Tracking ohne erkennbares Cookie-Banner |
| Kontakt & Conversion | Klick-zum-Anrufen, E-Mail/Kontaktformular, Online-Buchung (Treatwell, Doctolib, OpenTable …), WhatsApp |
| Social & Video | Instagram/TikTok verlinkt, Videos oder Instagram-Feed eingebunden |
| Signale | Werbe-Pixel (Meta, Google Ads, TikTok) = Marketingbudget vorhanden, Online-Shop |

**Instagram** (mit Meta-API): Follower, Beiträge gesamt, letzter Beitrag, Beiträge in 30 Tagen, Reels-Anteil der letzten 12 Beiträge, Engagement-Rate.

**TikTok:** Profil existiert, privat/öffentlich, Follower, Likes, letztes Video, Videos in 30 Tagen, Ø Aufrufe der letzten Videos.

**Google-Profil:** Bewertung, Anzahl Rezensionen, Öffnungsstatus (dauerhaft geschlossene Firmen bekommen Potenzial 0). Mehrere Standorte mit derselben Website gelten als Kette.

## Bewertung: Präsenz, Potenzial, Ansatzpunkte

- **Website-, Instagram- und TikTok-Score** (je 0–100): Punkte aus den Prüfungen oben.
- **Präsenz** (0–100): gewichteter Durchschnitt, Standard 40 % Website, 35 % Instagram, 25 % TikTok.
- **Potenzial** (0–100): 85 % „Lücke“ (100 − Präsenz) plus bis zu 15 Punkte für ein laufendes Geschäft (viele, gute Google-Bewertungen). Zuschlag, wenn bereits Werbung geschaltet wird; Abzug für Ketten und Firmen mit zu wenig Daten. Ab 70 = hoch, ab 45 = mittel.
- **Ansatzpunkte:** konkrete Schwächen, nach Wichtigkeit sortiert, teils mit Marktvergleich („6 von 20 Firmen dieser Suche sind auf Instagram“).
- **Merkmale:** Website-Bedarf, Instagram-Bedarf, TikTok-Bedarf, Video-Bedarf, Rechtliche Mängel, Kette, Wenig Daten.
- **„?“ statt Zahl** bedeutet: Profil existiert, aber ohne Kennzahlen (z. B. ohne Meta-API) oder die Website blockiert automatische Prüfungen. Dann rechnet Lead-Scout mit einem neutralen Wert.

**Anpassen:** Alle Gewichte, Punkte und Schwellen stehen oben in `leadscout/scoring.py` (z. B. „inaktiv ab 30 Tagen“). Nach einer Änderung lassen sich vorhandene Berichte ohne neues Abrufen neu berechnen:

```bash
python3 leadscout.py --neu-bewerten berichte/2026-11-04_1530_friseur-in-bielefeld.json
```

## Fairness, Grenzen und Recht

- **Höflich abrufen:** Lead-Scout beachtet `robots.txt`, ruft pro Website höchstens drei Seiten ab (plus bis zu zwei CSS-Dateien für die Google-Fonts-Prüfung), hält Abstand zwischen Anfragen an denselben Server und meldet sich mit einem ehrlichen User-Agent. Tragt in der `.env` unter `KONTAKT` eure Website ein, dann sehen Betreiber, wer prüft.
- **Instagram nur offiziell:** Kennzahlen kommen ausschließlich über die Meta Graph API.
- **Automatische Werte sind Hinweise:** Vor einem Gespräch kurz gegenprüfen. Ein Profil kann existieren, ohne verlinkt zu sein. Dafür gibt es im Bericht die Links „Manuell bei Google suchen“.
- **Datenschutz:** Berichte enthalten Kontaktdaten von Firmen (bei Einzelunternehmen auch personenbezogene Daten). Nur für die eigene Akquise nutzen, nicht weitergeben und nicht mehr benötigte Berichte löschen. Der Ordner `berichte/` ist von Git ausgenommen.
- **Kontaktaufnahme (UWG):** Werbe-E-Mails brauchen auch bei Firmen eine vorherige ausdrückliche Einwilligung. Werbeanrufe bei Firmen sind nur mit mutmaßlicher Einwilligung zulässig (§ 7 UWG). Sicherer Weg: persönlicher Besuch, Brief oder Kontakt über Empfehlungen, Netzwerke und Events. Das ist keine Rechtsberatung.

## Fehlerbehebung

| Meldung | Lösung |
|---|---|
| „Python kann keine sicheren Verbindungen prüfen“ | Mac: „Install Certificates.command“ im Ordner „Programme/Python 3.x“ ausführen. Alternativ `pip install certifi`. |
| „Der Google-API-Schlüssel ist ungültig“ | Schlüssel in `.env` prüfen (keine Leerzeichen, keine Anführungszeichen nötig). |
| „Places API (New) ist nicht aktiviert“ | In der Cloud Console unter „Bibliothek“ aktivieren. Achtung: „Places API (New)“, nicht die alte „Places API“. |
| „keine Abrechnung aktiviert“ | Rechnungskonto mit dem Projekt verknüpfen. |
| „Meta-Zugangstoken ungültig oder abgelaufen“ | Token neu erzeugen und verlängern (Schritte 2–4 bei Instagram). |
| „OpenStreetMap (Overpass) nicht erreichbar“ | Die Overpass-Server sind manchmal überlastet. Lead-Scout weicht automatisch auf Nominatim aus. Später erneut versuchen oder Google nutzen. |
| Oberfläche öffnet sich nicht | Adresse aus dem Terminal manuell im Browser öffnen. Ist der Port belegt, nimmt Lead-Scout den nächsten freien. |
| „Website blockiert automatische Prüfungen“ | Bot-Schutz der Website. Die Website wird nicht bewertet und ist im Bericht mit „?“ markiert. Bitte manuell ansehen. |

## Für Entwickler

```text
lead-scout/
├── leadscout.py              Startskript (Oberfläche oder Kommandozeile)
├── .env.example              Vorlage für Schlüssel und Einstellungen
├── leadscout/
│   ├── config.py             Einstellungen aus .env / Umgebungsvariablen
│   ├── net.py                HTTP: Zeitlimits, Drosselung, robots.txt, Schutz vor lokalen Adressen
│   ├── google.py             Places API (New), PageSpeed Insights
│   ├── osm.py                OpenStreetMap: Overpass, Nominatim, Branchen-Stichwörter
│   ├── discovery.py          Suche, eigene Liste, Dubletten, Ketten
│   ├── website.py            Website-Analyse
│   ├── social.py             Profil-Erkennung, TikTok, Meta Business Discovery
│   ├── scoring.py            Bewertung (hier anpassen)
│   ├── pipeline.py           Ablauf und Fortschritt
│   ├── report.py             HTML, CSV, JSON
│   ├── server.py, cli.py     Oberfläche und Kommandozeile
│   └── templates/            report.html (Bericht), app.html (Oberfläche)
└── tests/                    Tests (Standardbibliothek, ohne Internet)
```

Tests ausführen:

```bash
python3 -m unittest discover -s tests
```

Die Oberfläche ist nur unter `127.0.0.1` erreichbar und prüft Host- und Origin-Header. Alle Daten aus dem Netz werden im Bericht maskiert dargestellt.
