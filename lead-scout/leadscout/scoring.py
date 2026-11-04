"""Bewertung der Online-Präsenz und des Lead-Potenzials, inklusive „Ansatzpunkte“ fürs Erstgespräch.

ANPASSEN: Alle Gewichte, Punkte und Schwellen stehen in diesem oberen Abschnitt.
- Präsenz (0–100): Wie gut ist die Firma online aufgestellt? (hoch = stark)
- Potenzial (0–100): Wie lohnend ist die Firma als Kunde für die Agentur? (hoch = viel zu tun + Firma läuft)
"""
from __future__ import annotations

import statistics
from datetime import datetime

# Gewichtung der Kanäle für die Präsenz (Summe 1.0)
GEWICHTE = {"website": 0.40, "instagram": 0.35, "tiktok": 0.25}
# Score, wenn ein Profil existiert, aber keine Kennzahlen abrufbar sind (z. B. ohne Meta-API)
PROFIL_UNBEKANNT = 35
# Score, wenn die Website existiert, aber nicht automatisch prüfbar ist (Bot-Schutz, robots.txt)
WEBSITE_UNBEKANNT = 50

# Website: maximale Punkte je Bereich (Summe 100)
WEBSITE_PUNKTE = {
    "https": 12, "mobil": 16, "tempo": 15, "aktualitaet": 12, "seo": 17,
    "recht": 10, "kontakt": 8, "social": 6, "basis": 4,
}
# Abzug, wenn die Website keine eigene Domain hat (z. B. salon.wixsite.com)
ABZUG_OHNE_EIGENE_DOMAIN = 10

# Instagram: (Schwelle, Punkte) – die erste erfüllte Schwelle zählt
IG_FOLLOWER = [(10000, 20), (5000, 17), (2000, 14), (1000, 11), (500, 8), (200, 5), (50, 2)]
IG_BEITRAEGE = [(200, 10), (100, 8), (50, 6), (20, 4), (5, 2)]
IG_LETZTER_POST_TAGE = [(7, 25), (14, 21), (30, 16), (60, 10), (90, 6), (180, 2)]   # höchstens so viele Tage her
IG_POSTS_30_TAGE = [(12, 15), (8, 13), (4, 10), (2, 6), (1, 3)]
IG_REELS_ANTEIL = [(0.5, 15), (0.3, 11), (0.15, 7), (0.01, 3)]
IG_ENGAGEMENT_PROZENT = [(3, 15), (2, 12), (1, 8), (0.5, 4), (0.01, 1)]

# TikTok
TT_FOLLOWER = [(10000, 20), (5000, 17), (2000, 14), (1000, 11), (500, 8), (200, 5), (50, 2)]
TT_LETZTES_VIDEO_TAGE = [(7, 30), (14, 25), (30, 19), (60, 12), (90, 7), (180, 3)]
TT_VIDEOS_30_TAGE = [(10, 20), (6, 16), (4, 12), (2, 8), (1, 4)]
TT_AUFRUFE_SCHNITT = [(10000, 20), (3000, 16), (1000, 12), (300, 8), (100, 4), (1, 1)]
TT_LIKES_GESAMT = [(50000, 10), (10000, 8), (1000, 5), (100, 2)]

# „Inaktiv“ ab so vielen Tagen ohne neuen Beitrag
INAKTIV_TAGE = 30

# Potenzial = 85 % × (100 − Präsenz) + 15 × Geschäftsfaktor (Google-Bewertungen) ± Zuschläge
POTENZIAL_ANTEIL_LUECKE = 0.85
POTENZIAL_GESCHAEFT = 15
ZUSCHLAG_WERBUNG = 5        # schaltet bereits Werbung (Meta-Pixel, Google Ads …)
ABZUG_KETTE = 25            # Filiale einer Kette, Marketing meist zentral
ABZUG_WENIG_DATEN = 15      # Website unbekannt (z. B. OpenStreetMap ohne Website-Eintrag)

LABEL_POTENZIAL = [(70, "hoch"), (45, "mittel"), (0, "gering")]
LABEL_PRAESENZ = [(75, "stark"), (50, "solide"), (25, "schwach"), (0, "kaum vorhanden")]


# ---------------------------------------------------------------------------

def fmt_int(n) -> str:
    return f"{int(round(n)):,}".replace(",", ".")


def fmt_dec(x, digits: int = 1) -> str:
    return f"{x:.{digits}f}".replace(".", ",")


def days_text(d) -> str:
    if d is None:
        return ""
    if d <= 0:
        return "heute"
    if d == 1:
        return "gestern"
    if d < 60:
        return f"vor {d} Tagen"
    if d < 730:
        return f"vor {round(d / 30.4)} Monaten"
    return f"vor {round(d / 365)} Jahren"


def _up(value, table) -> float:
    """Punkte für „je mehr, desto besser“."""
    if value is None:
        return 0
    for threshold, points in table:
        if value >= threshold:
            return points
    return 0


def _down(value, table) -> float:
    """Punkte für „je weniger, desto besser“ (z. B. Tage seit dem letzten Beitrag)."""
    if value is None:
        return 0
    for limit, points in table:
        if value <= limit:
            return points
    return 0


def _label(value, table) -> str:
    for threshold, name in table:
        if value >= threshold:
            return name
    return table[-1][1]


def _check(checks: list, key: str, label: str, ok, points: float, maximum: float, detail: str = "") -> None:
    checks.append({"key": key, "label": label, "ok": ok, "points": round(points, 1), "max": maximum, "detail": detail})


def _socials_on_site(site: dict, platform: str) -> bool:
    return bool((site.get("socials") or {}).get(platform))


# ---------------------------------------------------------------------------
# Website
# ---------------------------------------------------------------------------

def score_website(lead: dict) -> tuple:
    """Gibt (score|None, checks, pitches, badges) zurück. pitches: (Priorität, Text, Bereich)."""
    site = lead.get("website") or {}
    pitches, badges, checks = [], [], []
    if not lead.get("website_url"):
        kind, label = lead.get("website_kind", ""), lead.get("website_platform", "")
        if kind == "google_site":
            pitches.append((98, "Website-Link im Google-Profil führt ins Leere – Google-Websites (business.site) "
                                "wurden 2024 abgeschaltet", "website"))
        elif label:
            pitches.append((100, f"Keine eigene Website – hinterlegt ist nur {label}", "website"))
        elif lead.get("profil_quelle") == "google":
            pitches.append((100, "Keine Website im Google-Unternehmensprofil hinterlegt", "website"))
        else:
            # OpenStreetMap/Liste: fehlender Eintrag heißt nicht, dass es keine Website gibt
            pitches.append((26, "Keine Website in den Daten hinterlegt (OpenStreetMap) – bitte kurz googeln", "hinweis"))
            return None, checks, pitches, [["Website unbekannt", "info"]]
        badges.append(["Keine Website", "bad"])
        return 0, checks, pitches, badges

    status = site.get("status", "fehler")
    if status == "fehler":
        text = site.get("status_text") or "nicht erreichbar"
        if not text.startswith("SSL-Zertifikat"):
            text = "Website funktioniert nicht – " + text.replace("Nicht erreichbar: ", "").replace("Website liefert ", "")
        pitches.append((95, text, "website"))
        return 0, checks, pitches, [["Website defekt", "bad"]]
    if status == "plattform":
        pitches.append((96, site.get("status_text", "Domain leitet auf eine Plattform weiter"), "website"))
        return 0, checks, pitches, [["Keine eigene Website", "bad"]]
    if status == "fremd":
        pitches.append((96, f"Die hinterlegte Domain {site.get('status_text', '')} – faktisch keine eigene Website",
                        "website"))
        return 0, checks, pitches, [["Fremde Seite", "bad"]]
    if status == "baustelle":
        pitches.append((95, f"Website ist eine Baustellen- oder Parkseite ({site.get('status_text', '')})", "website"))
        return 5, checks, pitches, [["Baustelle", "bad"]]
    if status == "gesperrt":
        pitches.append((15, "Website konnte nicht automatisch geprüft werden (Bot-Schutz/robots.txt) – bitte "
                            "manuell ansehen", "hinweis"))
        return None, checks, pitches, [["Nicht prüfbar", "info"]]

    P = WEBSITE_PUNKTE
    now_year = datetime.now().year

    # HTTPS
    https_ok = bool(site.get("https"))
    detail = "SSL-Zertifikat fehlerhaft" if site.get("ssl_error") else ("" if https_ok else "Seite läuft ohne HTTPS")
    _check(checks, "https", "Sichere Verbindung (HTTPS)", https_ok, P["https"] if https_ok else 0, P["https"], detail)
    if site.get("ssl_error"):
        pitches.append((86, "SSL-Zertifikat fehlerhaft – Browser zeigen eine Sicherheitswarnung", "website"))
        badges.append(["SSL-Fehler", "bad"])
    elif not https_ok:
        pitches.append((80, "Keine verschlüsselte Verbindung (HTTPS) – Browser zeigen „Nicht sicher“", "website"))
        badges.append(["Kein HTTPS", "bad"])

    # Mobil
    mobile = bool(site.get("viewport"))
    _check(checks, "mobil", "Für Smartphones optimiert", mobile, P["mobil"] if mobile else 0, P["mobil"],
           "" if mobile else "kein responsives Viewport-Tag")
    if not mobile:
        pitches.append((88, "Website ist nicht für Smartphones optimiert", "website"))
        badges.append(["Nicht mobil", "bad"])

    # Tempo
    psi = site.get("pagespeed") or {}
    perf = psi.get("performance")
    if perf is not None:
        lcp = f", Hauptinhalt nach {psi['lcp']}" if psi.get("lcp") else ""
        _check(checks, "tempo", "Ladezeit mobil (PageSpeed)", perf >= 50, P["tempo"] * perf / 100, P["tempo"],
               f"PageSpeed {perf}/100{lcp}")
        if perf < 50:
            pitches.append((72, f"Lädt auf dem Smartphone langsam (PageSpeed {perf}/100{lcp})", "website"))
            badges.append(["Langsam", "bad"])
        elif perf < 70:
            pitches.append((44, f"Ladezeit mobil ausbaufähig (PageSpeed {perf}/100{lcp})", "website"))
    else:
        t = site.get("ttfb")
        if t is None:
            pts, ok = P["tempo"] * 0.5, None
        elif t <= 0.8:
            pts, ok = P["tempo"] * 0.8, True
        elif t <= 1.5:
            pts, ok = P["tempo"] * 0.6, True
        elif t <= 3:
            pts, ok = P["tempo"] * 0.35, False
        else:
            pts, ok = P["tempo"] * 0.1, False
        detail = f"{fmt_dec(t, 2)} s bis zur ersten Antwort (ohne PageSpeed-Messung)" if t is not None else ""
        _check(checks, "tempo", "Server-Antwortzeit", ok, pts, P["tempo"], detail)
        if t is not None and t > 2.5:
            pitches.append((55, f"Server antwortet langsam ({fmt_dec(t)} s bis zur ersten Antwort)", "website"))
            badges.append(["Langsam", "warn"])

    # Aktualität
    year = site.get("copyright_year")
    deprecated = site.get("deprecated") or []
    jq = site.get("jquery_version") or ""
    if deprecated:
        _check(checks, "aktualitaet", "Zeitgemäße Technik", False, 0, P["aktualitaet"],
               "veraltete Elemente: " + ", ".join(deprecated))
        pitches.append((75, "Veraltete Technik im Einsatz (" + ", ".join(deprecated) + ")", "website"))
        badges.append(["Veraltet", "bad"])
    else:
        if year is None:
            pts, ok, detail = P["aktualitaet"] * 0.6, None, "kein Copyright-Jahr gefunden"
        elif year >= now_year - 1:
            pts, ok, detail = P["aktualitaet"], True, f"© {year}"
        elif year == now_year - 2:
            pts, ok, detail = P["aktualitaet"] * 0.65, True, f"© {year}"
        elif year >= now_year - 4:
            pts, ok, detail = P["aktualitaet"] * 0.3, False, f"© {year}"
        else:
            pts, ok, detail = 0, False, f"© {year}"
        if jq and jq.split(".")[0] in ("1", "2"):
            pts = max(0, pts - 3)
            detail += f", altes jQuery {jq}"
        _check(checks, "aktualitaet", "Aktualität (Copyright, Technik)", ok, pts, P["aktualitaet"], detail.strip(", "))
        if year is not None and year <= now_year - 3:
            pitches.append((65, f"Website wirkt veraltet (Copyright {year})", "website"))
            badges.append([f"© {year}", "warn"])

    # SEO
    seo, notes = 0.0, []
    tl = len(site.get("title") or "")
    if 10 <= tl <= 70:
        seo += 4
    elif tl:
        seo += 2
        notes.append("Seitentitel zu lang/kurz")
    else:
        notes.append("kein Seitentitel")
        pitches.append((45, "Kein Seitentitel – schlecht für Google", "website"))
    dl = len(site.get("description") or "")
    if 50 <= dl <= 170:
        seo += 4
    elif dl:
        seo += 2
        notes.append("Meta-Beschreibung zu kurz/lang")
    else:
        notes.append("keine Meta-Beschreibung")
        pitches.append((40, "Keine Meta-Beschreibung – Google zeigt zufällige Textausschnitte", "website"))
    h1 = site.get("h1_count") or 0
    if h1 == 1:
        seo += 3
    elif h1 > 1:
        seo += 2
        notes.append(f"{h1} H1-Überschriften")
    elif site.get("js_rendered"):
        seo += 1.5
    else:
        notes.append("keine H1-Überschrift")
        pitches.append((30, "Keine Hauptüberschrift (H1) auf der Startseite", "website"))
    if site.get("structured_data"):
        seo += 3
    else:
        notes.append("keine strukturierten Daten")
        pitches.append((24, "Keine strukturierten Daten für Google (z. B. Öffnungszeiten, Bewertungen)", "website"))
    if site.get("og_image"):
        seo += 2
    else:
        notes.append("kein Vorschaubild (og:image)")
        pitches.append((38, "Kein Vorschaubild beim Teilen über WhatsApp & Social Media", "website"))
    if site.get("lang"):
        seo += 1
    if site.get("noindex"):
        seo = 0
        notes.insert(0, "Startseite auf noindex")
        pitches.append((90, "Startseite ist für Google gesperrt (noindex) – wird nicht gefunden", "website"))
        badges.append(["Für Google gesperrt", "bad"])
    elif site.get("robots_google_blocked"):
        seo = 0
        notes.insert(0, "robots.txt sperrt Google")
        pitches.append((90, "robots.txt sperrt Google aus – Website wird nicht gefunden", "website"))
        badges.append(["Für Google gesperrt", "bad"])
    _check(checks, "seo", "SEO-Grundlagen", seo >= 12, seo, P["seo"], ", ".join(notes))

    # Recht & Datenschutz
    legal, notes = 0, []
    if site.get("impressum"):
        legal += 5
    else:
        notes.append("kein Impressum")
        pitches.append((82, "Kein Impressum gefunden – Pflichtangabe nach DDG, Abmahnrisiko", "website"))
        badges.append(["Kein Impressum", "bad"])
    if site.get("datenschutz"):
        legal += 3
    else:
        notes.append("keine Datenschutzerklärung")
        pitches.append((72, "Keine Datenschutzerklärung gefunden – DSGVO-Pflicht", "website"))
    if not site.get("google_fonts"):
        legal += 1
    else:
        notes.append("Google Fonts extern geladen")
        pitches.append((58, "Google Fonts werden direkt von Google-Servern geladen – DSGVO-Abmahnrisiko", "website"))
        badges.append(["Google Fonts", "warn"])
    tracking = site.get("tracking") or []
    if tracking and not site.get("consent_hint"):
        notes.append("Tracking ohne Cookie-Banner")
        pitches.append((62, f"Tracking ({', '.join(tracking)}) ohne erkennbares Cookie-Banner – DSGVO-Risiko", "website"))
        badges.append(["Tracking ohne Consent", "warn"])
    else:
        legal += 1
    _check(checks, "recht", "Impressum, Datenschutz & DSGVO", legal >= 9, legal, P["recht"], ", ".join(notes))

    # Kontakt & Conversion
    contact, notes = 0, []
    if site.get("tel_link"):
        contact += 3
    else:
        notes.append("Telefon nicht antippbar")
        pitches.append((34, "Telefonnummer nicht direkt antippbar (kein Klick-zum-Anrufen)", "website"))
    if site.get("contact_form") or site.get("emails"):
        contact += 3
    else:
        notes.append("kein Formular/keine E-Mail")
        pitches.append((42, "Kein Kontaktformular und keine E-Mail-Adresse auf der Website", "website"))
    if site.get("booking_tool") or site.get("whatsapp"):
        contact += 2
    else:
        notes.append("keine Online-Buchung/WhatsApp")
        pitches.append((28, "Keine Online-Terminbuchung oder WhatsApp-Kontakt", "website"))
    _check(checks, "kontakt", "Kontaktwege & Buchung", contact >= 6, contact, P["kontakt"], ", ".join(notes))

    # Social & Video auf der Website
    soc, notes = 0, []
    if _socials_on_site(site, "instagram") or _socials_on_site(site, "tiktok"):
        soc += 4
    else:
        notes.append("Instagram/TikTok nicht verlinkt")
    if site.get("video") or site.get("instagram_feed"):
        soc += 2
    else:
        notes.append("keine Videos")
        pitches.append((36, "Keine Videos auf der Website", "website"))
    _check(checks, "social", "Social Media & Video eingebunden", soc >= 4, soc, P["social"], ", ".join(notes))

    # Basis
    base, notes = 0, []
    if site.get("favicon"):
        base += 2
    else:
        notes.append("kein Favicon")
    words = site.get("word_count") or 0
    if site.get("js_rendered"):
        base += 1
    elif words >= 300:
        base += 2
    elif words >= 120:
        base += 1
    else:
        notes.append(f"nur {words} Wörter")
        pitches.append((35, f"Sehr wenig Text auf der Startseite ({words} Wörter) – schwach für Google", "website"))
    _check(checks, "basis", "Favicon & Textumfang", base >= 3, base, P["basis"], ", ".join(notes))

    img_total, img_no_alt = site.get("img_total") or 0, site.get("img_no_alt") or 0
    if img_total >= 5 and img_no_alt / img_total > 0.5:
        pitches.append((20, f"{img_no_alt} von {img_total} Bildern ohne Alternativtext (Barrierefreiheit, SEO)", "website"))

    if site.get("deep_link_404"):
        pitches.append((60, "Der hinterlegte Website-Link führt auf eine Unterseite, die es nicht mehr gibt (Fehler 404)",
                        "website"))
    if site.get("redirect_domain"):
        pitches.append((30, f"Hinterlegte Domain leitet auf {site['redirect_domain']} weiter – kurz prüfen, ob das die "
                            "aktuelle Website ist", "hinweis"))

    score = sum(c["points"] for c in checks)
    if site.get("builder_subdomain"):
        score -= ABZUG_OHNE_EIGENE_DOMAIN
        pitches.append((78, f"Keine eigene Domain – Website läuft unter {site.get('domain', '')}", "website"))
        badges.append(["Keine eigene Domain", "bad"])
    if site.get("cms_kind") == "baukasten":
        pitches.append((48, f"Mit Homepage-Baukasten erstellt ({site.get('cms')}) – oft eingeschränkt bei Design, "
                            "SEO und Ladezeit", "website"))
        badges.append([site.get("cms"), "info"])
    elif site.get("cms"):
        badges.append([site.get("cms"), "info"])
    return max(0, min(100, round(score))), checks, pitches, badges


# ---------------------------------------------------------------------------
# Instagram & TikTok
# ---------------------------------------------------------------------------

def score_instagram(lead: dict) -> tuple:
    ig = lead.get("instagram") or {}
    pitches, badges, checks = [], [], []
    if ig.get("status") == "feed":
        return PROFIL_UNBEKANNT, checks, pitches, [["Feed auf Website", "info"]]
    if not ig.get("handle"):
        return 0, checks, pitches, [["Kein Instagram", "bad"]]
    m = ig.get("metrics")
    if not m:
        if ig.get("status") == "kein_business":
            pitches.append((44, f"Instagram-Link @{ig['handle']} führt zu keinem Business-Profil (privat, umbenannt "
                                "oder persönliches Konto)", "instagram"))
            return 25, checks, pitches, [["Kein Business-Konto", "warn"]]
        return PROFIL_UNBEKANNT, checks, pitches, [["Kennzahlen offen", "info"]]

    f, posts, last, p30 = m.get("followers") or 0, m.get("posts") or 0, m.get("last_post_days"), m.get("posts_30d") or 0
    reels, eng = m.get("reels_share"), m.get("engagement")
    _check(checks, "ig_follower", "Follower", f >= 500, _up(f, IG_FOLLOWER), 20, fmt_int(f))
    _check(checks, "ig_posts", "Beiträge gesamt", posts >= 50, _up(posts, IG_BEITRAEGE), 10, fmt_int(posts))
    _check(checks, "ig_aktiv", "Letzter Beitrag", last is not None and last <= INAKTIV_TAGE,
           _down(last, IG_LETZTER_POST_TAGE), 25, days_text(last) or "keine Beiträge")
    _check(checks, "ig_freq", "Beiträge in 30 Tagen", p30 >= 4, _up(p30, IG_POSTS_30_TAGE), 15, str(p30))
    _check(checks, "ig_reels", "Reels-/Video-Anteil", None if reels is None else reels >= 0.3,
           _up(reels, IG_REELS_ANTEIL), 15,
           f"{m.get('videos_recent', 0)} von {m.get('sample', 0)} letzten Beiträgen" if reels is not None else "")
    _check(checks, "ig_eng", "Engagement-Rate", None if eng is None else eng >= 1,
           _up(eng, IG_ENGAGEMENT_PROZENT) if eng is not None else 7, 15,
           f"{fmt_dec(eng, 2)} %" if eng is not None else "Likes ausgeblendet")
    score = round(sum(c["points"] for c in checks))

    if last is None:
        pitches.append((80, "Instagram-Profil ohne Beiträge", "instagram"))
        badges.append(["Leer", "bad"])
    elif last > 90:
        pitches.append((82, f"Instagram seit {last} Tagen ohne neuen Beitrag (zuletzt {m.get('last_post_date', '')})",
                        "instagram"))
        badges.append(["Inaktiv", "bad"])
    elif last > INAKTIV_TAGE:
        pitches.append((74, f"Instagram seit {last} Tagen ohne neuen Beitrag", "instagram"))
        badges.append(["Inaktiv", "warn"])
    elif p30 < 4:
        pitches.append((50, f"Nur {p30} Instagram-Beiträge in den letzten 30 Tagen", "instagram"))
    if reels is not None and m.get("sample", 0) >= 4 and reels < 0.25:
        pitches.append((68, f"Kaum Reels: nur {m.get('videos_recent', 0)} von {m.get('sample', 0)} letzten "
                            "Beiträgen sind Videos", "instagram"))
        badges.append(["Kaum Reels", "warn"])
    if eng is not None and eng < 1:
        pitches.append((46, f"Geringe Interaktion auf Instagram ({fmt_dec(eng, 2)} % Engagement-Rate)", "instagram"))
    if f < 300:
        pitches.append((52, f"Kleine Instagram-Reichweite ({fmt_int(f)} Follower)", "instagram"))
    if score >= 70:
        pitches.append((40, f"Starkes Instagram ({fmt_int(f)} Follower, aktiv)", "staerke"))
    return score, checks, pitches, badges


def score_tiktok(lead: dict) -> tuple:
    tt = lead.get("tiktok") or {}
    pitches, badges, checks = [], [], []
    if not tt.get("handle"):
        return 0, checks, pitches, [["Kein TikTok", "bad"]]
    if tt.get("exists") is False:
        pitches.append((56, f"TikTok-Link @{tt['handle']} führt ins Leere (Profil existiert nicht)", "tiktok"))
        return 0, checks, pitches, [["Link tot", "bad"]]
    m = tt.get("metrics")
    if not m:
        return PROFIL_UNBEKANNT, checks, pitches, [["Kennzahlen offen", "info"]]
    if m.get("private"):
        pitches.append((50, "TikTok-Profil ist privat – für Kunden unsichtbar", "tiktok"))
        return 10, checks, pitches, [["Privat", "bad"]]

    f, last, v30 = m.get("followers") or 0, m.get("last_video_days"), m.get("videos_30d") or 0
    views, likes = m.get("avg_views"), m.get("likes") or 0
    _check(checks, "tt_follower", "Follower", f >= 500, _up(f, TT_FOLLOWER), 20, fmt_int(f))
    _check(checks, "tt_aktiv", "Letztes Video", last is not None and last <= INAKTIV_TAGE,
           _down(last, TT_LETZTES_VIDEO_TAGE), 30, days_text(last) or "keine Videos")
    _check(checks, "tt_freq", "Videos in 30 Tagen", v30 >= 4, _up(v30, TT_VIDEOS_30_TAGE), 20, str(v30))
    _check(checks, "tt_views", "Ø Aufrufe (letzte Videos)", None if views is None else views >= 1000,
           _up(views, TT_AUFRUFE_SCHNITT), 20, fmt_int(views) if views is not None else "")
    _check(checks, "tt_likes", "Likes gesamt", likes >= 1000, _up(likes, TT_LIKES_GESAMT), 10, fmt_int(likes))
    score = round(sum(c["points"] for c in checks))

    if not m.get("videos_visible"):
        pitches.append((66, "TikTok-Profil ohne Videos", "tiktok"))
        badges.append(["Leer", "bad"])
    elif last is not None and last > 90:
        pitches.append((78, f"TikTok seit {last} Tagen ohne neues Video (zuletzt {m.get('last_video_date', '')})", "tiktok"))
        badges.append(["Inaktiv", "bad"])
    elif last is not None and last > INAKTIV_TAGE:
        pitches.append((70, f"TikTok seit {last} Tagen ohne neues Video", "tiktok"))
        badges.append(["Inaktiv", "warn"])
    elif v30 < 4:
        pitches.append((48, f"Nur {v30} TikTok-Videos in den letzten 30 Tagen", "tiktok"))
    if views is not None and views < 300 and m.get("videos_visible"):
        pitches.append((46, f"Geringe TikTok-Reichweite (Ø {fmt_int(views)} Aufrufe pro Video)", "tiktok"))
    if score >= 70:
        pitches.append((40, f"Starkes TikTok ({fmt_int(f)} Follower, aktiv)", "staerke"))
    return score, checks, pitches, badges


# ---------------------------------------------------------------------------
# Gesamtbewertung
# ---------------------------------------------------------------------------

def _business_factor(lead: dict) -> float:
    reviews = lead.get("reviews")
    if reviews is None:
        return 0.5
    factor = 1.0 if reviews >= 100 else 0.8 if reviews >= 30 else 0.6 if reviews >= 10 else 0.4 if reviews >= 1 else 0.2
    if (lead.get("rating") or 0) >= 4.5:
        factor = min(1.0, factor + 0.1)
    return factor


def market_stats(leads: list) -> dict:
    total = len(leads)
    own = [l for l in leads if l.get("website_url")]
    ok_sites = [l for l in own if (l.get("website") or {}).get("status") == "ok"]
    ig = [l for l in leads if (l.get("instagram") or {}).get("handle") or (l.get("instagram") or {}).get("status") == "feed"]
    tt = [l for l in leads if (l.get("tiktok") or {}).get("handle") and (l.get("tiktok") or {}).get("exists") is not False]
    ig_metrics = [l["instagram"]["metrics"] for l in leads if (l.get("instagram") or {}).get("metrics")]
    tt_metrics = [l["tiktok"]["metrics"] for l in leads if (l.get("tiktok") or {}).get("metrics")]
    site_scores = [l["scores"]["website"] for l in own if l["scores"].get("website") is not None]

    def median(values):
        return round(statistics.median(values)) if len(values) >= 3 else None

    return {
        "firmen": total,
        "mit_website": len(own),
        "ohne_website": sum(1 for l in leads if not l.get("website_url") and l["scores"].get("website") == 0),
        "website_unbekannt": sum(1 for l in leads if not l.get("website_url") and l["scores"].get("website") is None),
        "website_ok": len(ok_sites),
        "mobil": sum(1 for l in ok_sites if l["website"].get("viewport")),
        "https": sum(1 for l in ok_sites if l["website"].get("https")),
        "mit_instagram": len(ig),
        "mit_tiktok": len(tt),
        "ig_mit_kennzahlen": len(ig_metrics),
        "tt_mit_kennzahlen": len(tt_metrics),
        "ig_aktiv": sum(1 for m in ig_metrics if m.get("last_post_days") is not None and m["last_post_days"] <= INAKTIV_TAGE),
        "tt_aktiv": sum(1 for m in tt_metrics if m.get("last_video_days") is not None and m["last_video_days"] <= INAKTIV_TAGE),
        "ig_median_follower": median([m.get("followers") or 0 for m in ig_metrics]),
        "tt_median_follower": median([m.get("followers") or 0 for m in tt_metrics]),
        "website_schnitt": round(statistics.mean(site_scores)) if site_scores else None,
    }


def _market_suffix(count: int, total: int, platform: str) -> str:
    if total < 5:
        return ""
    if count == 0:
        return f" – noch keine der {total} Firmen dieser Suche ist dort: Chance, als Erste sichtbar zu sein"
    return f" – {count} von {total} Firmen dieser Suche sind bereits auf {platform}"


def evaluate(leads: list) -> dict:
    """Bewertet alle Leads (in place) und gibt den Marktüberblick zurück."""
    for lead in leads:
        ws, w_checks, w_pitch, w_badges = score_website(lead)
        igs, ig_checks, ig_pitch, ig_badges = score_instagram(lead)
        tts, tt_checks, tt_pitch, tt_badges = score_tiktok(lead)
        lead["scores"] = {"website": ws, "instagram": igs, "tiktok": tts}
        lead["checks"] = {"website": w_checks, "instagram": ig_checks, "tiktok": tt_checks}
        lead["badges"] = {"website": w_badges, "instagram": ig_badges, "tiktok": tt_badges}
        lead["_pitch"] = w_pitch + ig_pitch + tt_pitch

    market = market_stats(leads)
    total = market["firmen"]
    for lead in leads:
        pitch = lead.pop("_pitch")
        site = lead.get("website") or {}
        site_ok = bool(lead.get("website_url")) and site.get("status") == "ok"
        ig, tt = lead.get("instagram") or {}, lead.get("tiktok") or {}
        if ig.get("status") == "feed":
            pitch.append((20, "Instagram-Feed ist auf der Website eingebunden – Profilname bitte manuell prüfen", "hinweis"))
        elif not ig.get("handle"):
            if site_ok:
                pitch.append((70, "Kein Instagram-Profil auf der Website verlinkt"
                              + _market_suffix(market["mit_instagram"], total, "Instagram"), "instagram"))
            else:
                pitch.append((50, "Kein Instagram-Profil gefunden (keine Website zum Abgleich) – kurz manuell prüfen",
                              "instagram"))
        elif site_ok and not _socials_on_site(site, "instagram"):
            pitch.append((44, f"Instagram-Profil @{ig['handle']} ist nicht auf der Website verlinkt", "instagram"))
        m = ig.get("metrics")
        med = market.get("ig_median_follower")
        if m and med and med >= 100 and (m.get("followers") or 0) < 0.5 * med:
            pitch.append((47, f"Instagram-Reichweite unter Marktschnitt ({fmt_int(m['followers'])} Follower, "
                              f"Median dieser Suche: {fmt_int(med)})", "instagram"))
        if not tt.get("handle"):
            where = "auf der Website verlinkt" if site_ok else "gefunden (keine Website zum Abgleich)"
            pitch.append((64 if site_ok else 46, f"Kein TikTok-Profil {where}"
                          + _market_suffix(market["mit_tiktok"], total, "TikTok"), "tiktok"))
        elif tt.get("exists") and site_ok and not _socials_on_site(site, "tiktok"):
            pitch.append((40, f"TikTok-Profil @{tt['handle']} ist nicht auf der Website verlinkt", "tiktok"))

        # Geschäftliche Signale
        status = lead.get("business_status", "")
        if status == "CLOSED_PERMANENTLY":
            pitch.append((100, "Laut Google dauerhaft geschlossen", "hinweis"))
        elif status == "CLOSED_TEMPORARILY":
            pitch.append((95, "Laut Google vorübergehend geschlossen", "hinweis"))
        if lead.get("chain"):
            pitch.append((90, f"Vermutlich Kette/Filiale ({lead.get('chain_count')} Standorte mit derselben Website) – "
                              "Marketing oft zentral", "hinweis"))
        rating, reviews = lead.get("rating"), lead.get("reviews") or 0
        if rating and rating >= 4.5 and reviews >= 20:
            pitch.append((60, f"Top-Bewertungen bei Google ({fmt_dec(rating)} ★, {fmt_int(reviews)} Rezensionen) – "
                              "starkes Material für Content", "staerke"))
        elif reviews >= 100:
            pitch.append((55, f"Viele Google-Rezensionen ({fmt_int(reviews)}) – etabliertes Geschäft", "staerke"))
        if rating and rating < 3.8 and reviews >= 10:
            pitch.append((50, f"Mäßige Google-Bewertung ({fmt_dec(rating)} ★) – Reputation ist ein Thema", "hinweis"))
        ads = site.get("ads_tools") or []
        if ads:
            pitch.append((58, f"Investiert bereits in Werbung ({', '.join(ads)}) – Marketingbudget vorhanden", "staerke"))
        if site.get("shop"):
            pitch.append((30, "Hat einen Online-Shop", "staerke"))
        if site.get("booking_tool") and site.get("booking_tool") != "Online-Termin":
            pitch.append((25, f"Online-Buchung über {site['booking_tool']}", "staerke"))

        # Präsenz & Potenzial
        s = lead["scores"]
        w_val = WEBSITE_UNBEKANNT if s["website"] is None else s["website"]
        praesenz = round(GEWICHTE["website"] * w_val + GEWICHTE["instagram"] * s["instagram"]
                         + GEWICHTE["tiktok"] * s["tiktok"])
        potenzial = POTENZIAL_ANTEIL_LUECKE * (100 - praesenz) + POTENZIAL_GESCHAEFT * _business_factor(lead)
        if ads:
            potenzial += ZUSCHLAG_WERBUNG
        if lead.get("chain"):
            potenzial -= ABZUG_KETTE
        if s["website"] is None and not lead.get("website_url"):
            potenzial -= ABZUG_WENIG_DATEN
        if status in ("CLOSED_PERMANENTLY", "CLOSED_TEMPORARILY"):
            potenzial = 0
        potenzial = max(0, min(100, round(potenzial)))
        s.update(praesenz=praesenz, potenzial=potenzial,
                 praesenz_label=_label(praesenz, LABEL_PRAESENZ), potenzial_label=_label(potenzial, LABEL_POTENZIAL))

        pitch.sort(key=lambda p: -p[0])
        lead["ansatzpunkte"] = [{"prio": p[0], "text": p[1], "bereich": p[2]} for p in pitch
                                if p[2] in ("website", "instagram", "tiktok")]
        lead["hinweise"] = [{"prio": p[0], "text": p[1], "bereich": p[2]} for p in pitch
                            if p[2] in ("staerke", "hinweis")]

        tags = []
        if s["website"] is not None and s["website"] < 50:
            tags.append("Website-Bedarf")
        # Nur sichere Schwächen markieren: kein Profil, oder Kennzahlen vorhanden und schwach
        if (not ig.get("handle") and ig.get("status") != "feed") or ig.get("status") == "kein_business" \
                or (ig.get("metrics") and s["instagram"] < 40):
            tags.append("Instagram-Bedarf")
        if not tt.get("handle") or tt.get("exists") is False or (tt.get("metrics") and s["tiktok"] < 40):
            tags.append("TikTok-Bedarf")
        ig_m = ig.get("metrics") or {}
        if (ig_m.get("reels_share") is not None and ig_m["reels_share"] < 0.25) or (ig.get("handle") and not tt.get("handle")):
            tags.append("Video-Bedarf")
        if site_ok and (not site.get("impressum") or not site.get("datenschutz") or site.get("google_fonts")
                        or ((site.get("tracking") or []) and not site.get("consent_hint"))):
            tags.append("Rechtliche Mängel")
        if lead.get("chain"):
            tags.append("Kette")
        if s["website"] is None and not lead.get("website_url"):
            tags.append("Wenig Daten")
        if status in ("CLOSED_PERMANENTLY", "CLOSED_TEMPORARILY"):
            tags.append("Geschlossen")
        lead["tags"] = tags

    market["potenzial_hoch"] = sum(1 for l in leads if l["scores"]["potenzial"] >= 70)
    market["potenzial_mittel"] = sum(1 for l in leads if 45 <= l["scores"]["potenzial"] < 70)
    praes = [l["scores"]["praesenz"] for l in leads]
    market["praesenz_schnitt"] = round(statistics.mean(praes)) if praes else None
    return market
