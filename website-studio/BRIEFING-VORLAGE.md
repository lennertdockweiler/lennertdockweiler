# Kunden-Briefing · Vorlage

Kopiere einen der Blöcke, fülle aus, was du weißt, und sende ihn an Claude: zusammen mit dem Master-Prompt oder in einem Projekt bzw. Ordner, in dem der Master-Prompt schon hinterlegt ist.

- **Leere Felder sind erlaubt.** Claude entscheidet dann nach Best Practice und dokumentiert seine Annahmen im Konzept.
- Text hinter `#` ist nur eine Auswahlhilfe. Ersetze ihn durch deine Angabe oder lass ihn stehen.
- **Bequemer geht es mit dem Generator** (`generator.html`): Er schlägt nach Eingabe der Branche Leistungen, Keywords, Zielgruppen, Kundenfragen, Ziele, Stil und Funktionen vor und kennzeichnet unbestätigte Vorschläge im Briefing mit `[Vorschlag]`. Wenn du von Hand ausfüllst, kannst du unsichere Angaben genauso markieren, z. B. `LEISTUNGEN [Vorschlag]: …`.
- **Je mehr echte Informationen, desto besser das Ergebnis:** Leistungen, Belege, Kundenstimmen, Fotos, Logo und die Adresse der alten Website machen den größten Unterschied.
- Anhänge (Logo, Fotos, Texte, Flyer, Preislisten) einfach mitschicken bzw. in den Projektordner legen.

---

## Variante A · Schnellstart

Reicht für eine starke Pitch-Demo. Claude ergänzt den Rest selbst.

```text
=== KUNDEN-BRIEFING ===
PROJEKTZWECK:      # produktion | pitch-demo | relaunch
BRANCHE:
FIRMENNAME:
ORT / EINZUGSGEBIET:
LEISTUNGEN:        # Hauptleistung zuerst
BESONDERHEIT:      # Was macht den Betrieb besonders?
STIL:              # optional, z. B. „Warm & Nahbar“ oder „edel, ruhig, viel Weißraum“
BESTEHENDE WEBSITE:
```

---

## Variante B · Vollständiges Briefing

```text
=== KUNDEN-BRIEFING ===

## Projekt
PROJEKTZWECK:              # produktion | pitch-demo | relaunch
ARBEITSMODUS:              # autopilot | rückfragen
FREIGABE NACH KONZEPT:     # nein | ja
TECHNIK:                   # automatisch | astro | html
HOSTING:                   # unbekannt | webspace-php (z. B. IONOS, Strato, all-inkl) | netlify | vercel | cloudflare
DOMAIN:
SPRACHEN:                  # de | de, en | …
ZEITRAHMEN:

## Unternehmen
BRANCHE:                   # möglichst genau, z. B. „Zahnarztpraxis mit Schwerpunkt Kinder“
FIRMENNAME:
RECHTSFORM:
INHABER / GESCHÄFTSFÜHRUNG:
ADRESSE:
TELEFON:
E-MAIL:
WHATSAPP:
ÖFFNUNGSZEITEN:
SONDERZEITEN:              # Betriebsurlaub, Feiertage, Notdienst
EINZUGSGEBIET:
GEGRÜNDET:
TEAMGRÖSSE:
BESTEHENDE WEBSITE:
GOOGLE-PROFIL / BEWERTUNGEN:   # Link, Schnitt, Anzahl
SOCIAL MEDIA:
RECHTSANGABEN:             # Register, USt-IdNr., Kammer, Aufsichtsbehörde, Berufshaftpflicht …

## Angebot & Positionierung
LEISTUNGEN:                # Hauptleistung zuerst, gern mit kurzer Beschreibung
PREISE:                    # Preise, Preisrahmen oder „keine Preise nennen“
ZIELGRUPPEN:
USP / UNTERSCHIED:         # Warum dieser Betrieb und nicht ein anderer?
WETTBEWERBER:              # Namen oder URLs
HÄUFIGE FRAGEN / EINWÄNDE:
BELEGE:                    # Zahlen, Zertifikate, Auszeichnungen, Garantien, Referenzen – nur echte
KUNDENSTIMMEN:             # echte Zitate mit Freigabe, Name bzw. Initiale, Quelle
GESCHICHTE / PERSÖNLICHES:

## Ziele
HAUPTZIEL:                 # anfragen | anrufe | terminbuchungen | reservierungen | bewerbungen | verkäufe | information
NEBENZIELE:
KEYWORDS / ORTE:
REAKTIONSZEIT:             # z. B. „Antwort innerhalb von 24 Stunden“ – nur wenn verbindlich

## Marke & Design
STIL:                      # Klar & Modern | Warm & Nahbar | Premium & Edel | Kraftvoll & Bodenständig | Seriös & Vertrauensvoll | Frisch & Freundlich | Editorial & Kreativ | Natürlich & Nachhaltig | Dunkel & Atmosphärisch | freie Beschreibung
MARKENPERSÖNLICHKEIT:      # drei Adjektive
FARBEN:                    # Hex-Werte, „aus dem Logo“ oder Beschreibung
SCHRIFTEN:
LOGO:                      # vorhanden (Datei anhängen) | fehlt → Interim-Wortmarke
BILDER:                    # eigene Fotos (anhängen) | lizenzfreie Fotos | gestaltete Platzhalter
VORBILDER:                 # Websites, die gefallen – und warum
NO-GOS:
ANREDE:                    # Sie | du
TONALITÄT:                 # z. B. seriös, herzlich, locker, frech
GENDERN:                   # neutral ohne Sonderzeichen | Doppelpunkt | Sternchen | generisches Maskulinum

## Umfang & Funktionen
SEITEN:                    # leer = Claude schlägt vor
FUNKTIONEN:                # kontaktformular, rückruf, online-termin, reservierung, öffnungszeiten-live, karte (zwei-klick), bewertungen, galerie, vorher-nachher, preisliste, speisekarte, kursplan, karriere, blog, newsletter, mehrsprachig, suche, shop-anbindung, whatsapp, mobile-aktionsleiste, hinweisleiste
TOOLS / INTEGRATIONEN:     # z. B. Doctolib, Treatwell, Calendly, Maklersoftware, Buchungssystem
ANALYTICS:                 # keine | plausible | matomo | ga4 (benötigt Consent-Banner)
SELBSTPFLEGE / CMS:        # nein | ja (was soll der Kunde selbst ändern?)

## Sonstiges
BESONDERHEITEN / WÜNSCHE:
MATERIAL / ANHÄNGE:
```

---

## Beispiel · ausgefülltes Schnellstart-Briefing

Fiktives Unternehmen, nur zur Orientierung.

```text
=== KUNDEN-BRIEFING ===
PROJEKTZWECK: pitch-demo
BRANCHE: Sanitär, Heizung, Klima – Schwerpunkt Badsanierung
FIRMENNAME: Haustechnik Morgenroth GmbH (fiktives Beispiel)
ORT / EINZUGSGEBIET: Bielefeld und 25 km Umkreis (Gütersloh, Herford, Bad Salzuflen)
LEISTUNGEN: Badsanierung (Hauptleistung), Heizungsmodernisierung inkl. Wärmepumpe, Wartung, Notdienst für Bestandskunden
BESONDERHEIT: Komplettbad aus einer Hand mit festem Ansprechpartner, 3D-Badplanung vorab, verbindlicher Zeitplan; sucht dringend Azubis
STIL: Kraftvoll & Bodenständig, aber hochwertig – nicht rustikal
BESTEHENDE WEBSITE: –
```
