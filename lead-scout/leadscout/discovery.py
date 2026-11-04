"""Firmen finden: Google Maps (Places API), OpenStreetMap (kostenlos) oder eine eigene Liste."""
from __future__ import annotations

import re
import urllib.parse
from collections import Counter

from . import google, osm, social
from .config import SetupError

MAX_TOTAL = 300
URL_LIKE = re.compile(r"^(?:https?://)?(?:[a-z0-9-]+\.)+[a-z]{2,}(?:[/:?#]\S*)?$", re.I)


def split_terms(value) -> list:
    """„Friseur, Barbershop“ → ["Friseur", "Barbershop"] (Komma, Semikolon oder Zeilenumbruch)."""
    items = value if isinstance(value, (list, tuple)) else re.split(r"[,;\n]+", value or "")
    out: list = []
    for item in items:
        term = " ".join(str(item).split())
        if term and term.lower() not in [o.lower() for o in out]:
            out.append(term)
    return out


def _maps_link(name: str, address: str) -> str:
    return "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote_plus(f"{name} {address}".strip())


def parse_list(text: str, settings, log) -> list:
    """Eigene Liste: pro Zeile „Firmenname“, „Firmenname; https://website.de“ oder nur „website.de“.

    Zeilen ohne Website werden – falls ein Google-Schlüssel hinterlegt ist – über Google Maps ergänzt.
    """
    leads = []
    for i, raw in enumerate((text or "").splitlines()):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in re.split(r"\s*[;\t|]\s*", line) if p.strip()]
        url = next((p for p in parts if URL_LIKE.match(p) and " " not in p), "")
        rest = [p for p in parts if p != url]
        name = rest[0] if rest else ""
        extra = " ".join(rest[1:])
        lead = {
            "id": f"liste:{i}", "name": name, "address": extra, "phone": "", "website_raw": url, "maps_url": "",
            "rating": None, "reviews": None, "category": "", "business_status": "", "source": "liste",
            "branche": "", "ort": extra, "hints": {}, "name_from_domain": False,
        }
        if not url and name and settings.has_google:
            try:
                found = google.places_search(f"{name} {extra}".strip(), api_key=settings.google_api_key,
                                             land=settings.land, sprache=settings.sprache, limit=1,
                                             user_agent=settings.user_agent)
                if found:
                    lead = google.place_to_lead(found[0], "", extra)
                    lead["id"] = f"liste:{i}:{lead['id']}"
                    lead["source"] = "liste"
                    lead["name_from_domain"] = False
            except google.GoogleError as e:
                log(f"  Google-Suche für „{name}“ fehlgeschlagen: {e}")
        if not lead["name"] and url:
            lead["name"] = social.registrable_domain(url)
            lead["name_from_domain"] = True
        if not lead["maps_url"] and lead["name"]:
            lead["maps_url"] = _maps_link(lead["name"], lead["address"])
        leads.append(lead)
    return leads


def prepare(lead: dict) -> None:
    """Website-Feld einordnen (eigene Website, Social-Profil, Link-Seite, Portal) und Hinweise übernehmen."""
    lead.setdefault("socials", {})
    lead.update(website_url="", website_platform="", website_kind="", linkhub="")
    via = lead["source"] if lead["source"] in ("google", "osm") else "liste"
    for platform, value in (lead.get("hints") or {}).items():
        item = social.handle_from_hint(platform, value)
        if item:
            social.merge_socials(lead["socials"], {item[0]: [{"ident": item[1], "url": item[2], "via": via}]})
    raw = (lead.get("website_raw") or "").strip()
    if not raw:
        return
    url = social.normalize_url(raw)
    plat = social.platform_of(url)
    if plat is None or plat["kind"] == "builder":
        lead["website_url"] = url
        return
    lead["website_platform"] = plat["label"]
    lead["website_kind"] = plat["kind"]
    if plat["kind"] == "social":
        item = social.classify_social(url)
        if item:
            social.merge_socials(lead["socials"], {item[0]: [{"ident": item[1], "url": item[2], "via": via}]})
    elif plat["kind"] == "linkhub":
        lead["linkhub"] = url


def _simple(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


def dedupe(leads: list) -> list:
    seen_ids, seen_keys, out = set(), set(), []
    for lead in leads:
        if lead["id"] in seen_ids:
            continue
        dom = social.registrable_domain(lead.get("website_raw") or "") if lead.get("website_raw") else ""
        key = (_simple(lead["name"]), dom, _simple(lead.get("address", ""))[:12])
        if lead["name"] and key in seen_keys:
            continue
        seen_ids.add(lead["id"])
        seen_keys.add(key)
        out.append(lead)
    return out


def mark_chains(leads: list) -> None:
    """Mehrere Standorte mit derselben Website-Domain → wahrscheinlich Kette/Filialbetrieb."""
    domains = [social.registrable_domain(l["website_url"]) for l in leads if l.get("website_url")]
    counts = Counter(domains)
    for lead in leads:
        dom = social.registrable_domain(lead["website_url"]) if lead.get("website_url") else ""
        lead["chain"] = bool(dom) and counts[dom] >= 2
        lead["chain_count"] = counts[dom] if lead["chain"] else 0


def discover(branchen: list, orte: list, anzahl: int, quelle: str, liste: str, settings, log, cancelled) -> tuple:
    """Gibt (leads, genutzte_quelle, hinweise) zurück."""
    notes: list = []
    source = quelle or "auto"
    if source == "auto":
        source = "google" if settings.has_google else "osm"
    if source == "google" and not settings.has_google:
        raise SetupError("Für die Google-Suche fehlt der GOOGLE_API_KEY (siehe README, Abschnitt „Google-Schlüssel“). "
                         "Alternativ die kostenlose Quelle OpenStreetMap wählen.")
    leads: list = []
    if source == "liste":
        leads = parse_list(liste, settings, log)
        if not leads:
            raise SetupError("Die Liste ist leer – bitte pro Zeile eine Firma oder Website eintragen.")
    else:
        if not branchen or not orte:
            raise SetupError("Bitte Branche und Ort angeben.")
        label = "Google Maps" if source == "google" else "OpenStreetMap"
        for branche in branchen:
            for ort in orte:
                if cancelled():
                    break
                log(f"Suche „{branche}“ in „{ort}“ über {label} …")
                try:
                    if source == "google":
                        places = google.places_search(f"{branche} in {ort}", api_key=settings.google_api_key,
                                                      land=settings.land, sprache=settings.sprache, limit=anzahl,
                                                      user_agent=settings.user_agent)
                        found = [google.place_to_lead(p, branche, ort) for p in places]
                    else:
                        found = osm.search(branche, ort, land=settings.land, limit=anzahl,
                                           user_agent=settings.user_agent, log=log)
                except google.GoogleError as e:
                    raise SetupError(str(e)) from e
                except RuntimeError as e:
                    notes.append(str(e))
                    log(f"  {e}")
                    continue
                log(f"  {len(found)} Firmen gefunden")
                leads.extend(found)
    leads = dedupe(leads)
    if len(leads) > MAX_TOTAL:
        notes.append(f"Es wurden nur die ersten {MAX_TOTAL} von {len(leads)} Firmen analysiert.")
        leads = leads[:MAX_TOTAL]
    for lead in leads:
        prepare(lead)
    mark_chains(leads)
    return leads, source, notes
