"""Offizielle Google-APIs: Places API (New) für die Firmensuche, PageSpeed Insights für die Ladezeit."""
from __future__ import annotations

import time
import urllib.parse

from . import net

PLACES_URL = "https://places.googleapis.com/v1/places:searchText"
PLACES_FIELDS = ",".join([
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.websiteUri",
    "places.nationalPhoneNumber",
    "places.internationalPhoneNumber",
    "places.rating",
    "places.userRatingCount",
    "places.businessStatus",
    "places.googleMapsUri",
    "places.primaryTypeDisplayName",
    "places.location",
    "nextPageToken",
])
PSI_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"


class GoogleError(Exception):
    pass


def explain_error(r: net.Response, api: str = "Places API (New)") -> str:
    """Übersetzt Google-Fehlerantworten in verständliche Hinweise."""
    if r.error:
        return f"Google nicht erreichbar ({r.describe_error()}: {r.error_detail})"
    data = r.json() or {}
    err = data.get("error", {}) if isinstance(data, dict) else {}
    message = err.get("message", "") or r.text()[:300]
    reasons = " ".join(str(d.get("reason", "")) for d in err.get("details", []) if isinstance(d, dict))
    blob = f"{message} {reasons} {err.get('status', '')}"
    if "API_KEY_INVALID" in blob or "API key not valid" in blob:
        return "Der Google-API-Schlüssel ist ungültig. Bitte GOOGLE_API_KEY in der .env prüfen."
    if "BILLING" in blob.upper() or "billing" in blob:
        return ("Für das Google-Cloud-Projekt ist keine Abrechnung aktiviert. Die Places API braucht ein "
                "Rechnungskonto (es gibt ein monatliches Freikontingent).")
    if "SERVICE_DISABLED" in blob or "has not been used in project" in blob or "is disabled" in blob:
        return f"Die „{api}“ ist im Google-Cloud-Projekt nicht aktiviert. Bitte in der API-Bibliothek aktivieren."
    if "API_KEY_SERVICE_BLOCKED" in blob or "are blocked" in blob:
        return f"Der API-Schlüssel ist auf andere APIs beschränkt. Bitte „{api}“ in den Schlüssel-Einschränkungen erlauben."
    if r.status == 429 or "RESOURCE_EXHAUSTED" in blob:
        return "Google-Kontingent erschöpft. Später erneut versuchen oder Kontingent in der Cloud Console prüfen."
    if r.status == 403:
        return f"Zugriff verweigert ({message[:200]})"
    return f"Google-Fehler {r.status}: {message[:200]}"


def places_search(query: str, *, api_key: str, land: str = "DE", sprache: str = "de",
                  limit: int = 20, user_agent: str = "") -> list:
    """Textsuche wie in Google Maps, z. B. „Friseur in Bielefeld“. Liefert höchstens 60 Treffer."""
    limit = max(1, min(int(limit), 60))
    results: list = []
    token = None
    while len(results) < limit:
        body = {"textQuery": query, "languageCode": sprache, "regionCode": land, "pageSize": 20}
        if token:
            body["pageToken"] = token
        r = net.fetch(PLACES_URL, method="POST", data=body, accept=net.ACCEPT_JSON, timeout=30,
                      user_agent=user_agent,
                      headers={"X-Goog-Api-Key": api_key, "X-Goog-FieldMask": PLACES_FIELDS})
        if not r.ok:
            raise GoogleError(explain_error(r))
        data = r.json() or {}
        places = data.get("places") or []
        results.extend(places)
        token = data.get("nextPageToken")
        if not token or not places:
            break
        time.sleep(1.0)
    return results[:limit]


def place_to_lead(p: dict, branche: str, ort: str) -> dict:
    loc = p.get("location") or {}
    return {
        "id": "g:" + str(p.get("id", "")),
        "name": (p.get("displayName") or {}).get("text", "").strip(),
        "address": p.get("formattedAddress", ""),
        "phone": p.get("nationalPhoneNumber") or p.get("internationalPhoneNumber") or "",
        "website_raw": p.get("websiteUri", ""),
        "maps_url": p.get("googleMapsUri", ""),
        "rating": p.get("rating"),
        "reviews": p.get("userRatingCount"),
        "category": (p.get("primaryTypeDisplayName") or {}).get("text", ""),
        "business_status": p.get("businessStatus", ""),
        "lat": loc.get("latitude"),
        "lng": loc.get("longitude"),
        "source": "google",
        "profil_quelle": "google",
        "branche": branche,
        "ort": ort,
        "hints": {},
    }


def _fmt_seconds(ms) -> str:
    if ms is None:
        return ""
    return f"{ms / 1000:.1f} s".replace(".", ",")


def parse_pagespeed(data: dict) -> dict:
    lh = data.get("lighthouseResult") or {}
    cats = lh.get("categories") or {}
    audits = lh.get("audits") or {}

    def cat(name):
        score = (cats.get(name) or {}).get("score")
        return round(score * 100) if isinstance(score, (int, float)) else None

    def num(name):
        value = (audits.get(name) or {}).get("numericValue")
        return value if isinstance(value, (int, float)) else None

    lcp = num("largest-contentful-paint")
    fcp = num("first-contentful-paint")
    field_data = (data.get("loadingExperience") or {}).get("overall_category")
    return {
        "performance": cat("performance"),
        "seo": cat("seo"),
        "accessibility": cat("accessibility"),
        "best_practices": cat("best-practices"),
        "lcp_ms": round(lcp) if lcp is not None else None,
        "lcp": _fmt_seconds(lcp),
        "fcp_ms": round(fcp) if fcp is not None else None,
        "fcp": _fmt_seconds(fcp),
        "tbt_ms": round(num("total-blocking-time")) if num("total-blocking-time") is not None else None,
        "cls": round(num("cumulative-layout-shift"), 3) if num("cumulative-layout-shift") is not None else None,
        "felddaten": field_data if field_data in ("FAST", "AVERAGE", "SLOW") else None,
        "error": "",
    }


def pagespeed(url: str, *, api_key: str = "", sprache: str = "de", user_agent: str = "") -> dict:
    """Mobile Lighthouse-Messung über die PageSpeed-Insights-API (dauert 10–40 Sekunden)."""
    params = [("url", url), ("strategy", "mobile"), ("category", "performance"), ("category", "seo"),
              ("category", "accessibility"), ("category", "best-practices"), ("locale", sprache)]
    if api_key:
        params.append(("key", api_key))
    r = net.fetch(PSI_URL + "?" + urllib.parse.urlencode(params), accept=net.ACCEPT_JSON, timeout=150,
                  max_bytes=25_000_000, user_agent=user_agent)
    if not r.ok:
        data = r.json() or {}
        message = ((data.get("error") or {}).get("message") or "") if isinstance(data, dict) else ""
        if r.status == 400 and "lighthouse" in message.lower():
            return {"error": "PageSpeed konnte die Seite nicht laden"}
        return {"error": explain_error(r, "PageSpeed Insights API")}
    return parse_pagespeed(r.json() or {})


def check_key(api_key: str, user_agent: str = "") -> dict:
    """Prüft den Schlüssel für Places API (New) und PageSpeed Insights API (ohne kostenpflichtige Felder)."""
    out = {"places": {"ok": False, "message": ""}, "pagespeed": {"ok": False, "message": ""}}
    if not api_key:
        msg = "Kein GOOGLE_API_KEY hinterlegt."
        out["places"]["message"] = out["pagespeed"]["message"] = msg
        return out
    r = net.fetch(PLACES_URL, method="POST", accept=net.ACCEPT_JSON, timeout=30, user_agent=user_agent,
                  data={"textQuery": "Rathaus Berlin", "pageSize": 1},
                  headers={"X-Goog-Api-Key": api_key, "X-Goog-FieldMask": "places.id"})
    if r.ok:
        out["places"] = {"ok": True, "message": "Places API (New) funktioniert."}
    else:
        out["places"]["message"] = explain_error(r)
    # Absichtlich ungültige URL: Antwort 400 heißt, Schlüssel und API sind in Ordnung.
    r = net.fetch(PSI_URL + "?" + urllib.parse.urlencode({"url": "keine-url", "key": api_key}),
                  accept=net.ACCEPT_JSON, timeout=30, user_agent=user_agent)
    blob = r.text()
    if r.status == 400 and "API_KEY_INVALID" not in blob and "API key not valid" not in blob:
        out["pagespeed"] = {"ok": True, "message": "PageSpeed Insights API funktioniert."}
    elif r.ok:
        out["pagespeed"] = {"ok": True, "message": "PageSpeed Insights API funktioniert."}
    else:
        out["pagespeed"]["message"] = explain_error(r, "PageSpeed Insights API")
    return out
