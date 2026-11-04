"""Ablauf einer Suche: Firmen finden → Websites → Social-Profile → Kennzahlen → PageSpeed → Bewertung → Bericht."""
from __future__ import annotations

import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime

from . import __version__, discovery, google, net, report, scoring, social, website
from .config import SetupError, Settings

OTHER_PLATFORMS = ["facebook", "youtube", "linkedin", "xing", "x", "pinterest", "whatsapp", "threads", "youtube_video"]


@dataclass
class Options:
    branchen: list = field(default_factory=list)
    orte: list = field(default_factory=list)
    anzahl: int = 20
    quelle: str = "auto"
    liste: str = ""
    pagespeed: bool = False
    tiktok: bool = True
    instagram: bool = True
    ig_suche: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "Options":
        def flag(name, default):
            value = data.get(name, default)
            return value if isinstance(value, bool) else str(value).lower() in ("1", "true", "ja", "on", "yes")

        try:
            anzahl = int(data.get("anzahl", 20))
        except (TypeError, ValueError):
            anzahl = 20
        quelle = str(data.get("quelle", "auto")).lower()
        if quelle not in ("auto", "google", "osm", "liste"):
            quelle = "auto"
        return cls(
            branchen=discovery.split_terms(data.get("branchen") or data.get("branche") or ""),
            orte=discovery.split_terms(data.get("orte") or data.get("ort") or ""),
            anzahl=max(1, min(anzahl, 60)),
            quelle=quelle,
            liste=str(data.get("liste") or "")[:200_000],
            pagespeed=flag("pagespeed", False),
            tiktok=flag("tiktok", True),
            instagram=flag("instagram", True),
            ig_suche=flag("ig_suche", True),
        )

    def title(self) -> str:
        if self.quelle == "liste":
            return "Eigene Liste"
        return f"{', '.join(self.branchen)} in {', '.join(self.orte)}"


class Progress:
    """Thread-sicherer Fortschritt, gelesen von Kommandozeile und Oberfläche."""

    def __init__(self, on_log=None):
        self._lock = threading.Lock()
        self.phase = ""
        self.done = 0
        self.total = 0
        self.logs: list = []
        self.on_log = on_log
        self.cancel_event = threading.Event()
        self.started = time.time()

    def set_phase(self, name: str, total: int = 0) -> None:
        with self._lock:
            self.phase, self.done, self.total = name, 0, total
        self.log(name + (f" ({total})" if total else ""))

    def step(self, n: int = 1) -> None:
        with self._lock:
            self.done = min(self.total, self.done + n) if self.total else self.done + n

    def log(self, message: str) -> None:
        line = f"{datetime.now():%H:%M:%S}  {message}"
        with self._lock:
            self.logs.append(line)
            if len(self.logs) > 500:
                self.logs = self.logs[-400:]
        if self.on_log:
            self.on_log(message)

    def cancelled(self) -> bool:
        return self.cancel_event.is_set()

    def snapshot(self) -> dict:
        with self._lock:
            return {"phase": self.phase, "done": self.done, "total": self.total, "logs": self.logs[-60:],
                    "sekunden": round(time.time() - self.started)}


def self_test(settings: Settings) -> None:
    """Prüft Internet und Zertifikate, bevor viele Websites fälschlich als fehlerhaft gelten."""
    r = net.fetch("https://www.google.com/generate_204", user_agent=settings.user_agent, timeout=15)
    if r.error == "ssl":
        raise SetupError(
            "Python kann keine sicheren Verbindungen prüfen (Zertifikate fehlen). Auf dem Mac: im Ordner "
            "„Programme/Python 3.x“ die Datei „Install Certificates.command“ doppelklicken. Alternativ: "
            "pip install certifi")
    if r.error:
        raise SetupError(f"Keine Internetverbindung ({r.describe_error()}).")


def check_connections(settings: Settings) -> list:
    """Verbindungstest für Oberfläche und Kommandozeile: [[Bereich, ok (True/False/None), Meldung], …]."""
    results = []
    try:
        self_test(settings)
        results.append(["Internet & Zertifikate", True, "OK"])
    except SetupError as e:
        return [["Internet & Zertifikate", False, str(e)]]
    if settings.has_google:
        g = google.check_key(settings.google_api_key, settings.user_agent)
        results.append(["Google Places API (Firmensuche)", g["places"]["ok"], g["places"]["message"]])
        results.append(["PageSpeed Insights API (Ladezeit)", g["pagespeed"]["ok"], g["pagespeed"]["message"]])
    else:
        results.append(["Google-Schlüssel", None, "Nicht hinterlegt – die Suche läuft über OpenStreetMap "
                                                  "(kostenlos, aber weniger vollständig)."])
    if settings.meta_access_token:
        m = social.MetaClient(settings.meta_access_token, settings.meta_ig_user_id, settings.meta_graph_version,
                              settings.user_agent, []).check()
        results.append(["Meta Graph API (Instagram-Kennzahlen)", m["ok"], m["message"]])
    else:
        results.append(["Meta Graph API (Instagram-Kennzahlen)", None,
                        "Nicht eingerichtet – Instagram-Profile werden erkannt und verlinkt, aber ohne Kennzahlen."])
    r = net.fetch("https://www.tiktok.com/oembed?url=https%3A%2F%2Fwww.tiktok.com%2F%40tiktok",
                  user_agent=settings.user_agent, accept=net.ACCEPT_JSON, timeout=20)
    results.append(["TikTok (oEmbed)", r.status == 200,
                    "erreichbar" if r.status == 200 else f"nicht erreichbar ({r.describe_error() or r.status})"])
    return results


def _short(lead: dict) -> str:
    return lead["name"][:48] or lead.get("website_url", "")


def _name_from_title(title: str) -> str:
    parts = [p.strip() for p in re.split(r"\s+[|–—\-·:]\s+", title or "") if p.strip()]
    return (parts[0] if parts else "")[:70]


def _collect_profiles(lead: dict) -> None:
    socials: dict = {}
    social.merge_socials(socials, lead.get("socials") or {})
    site = lead.get("website") or {}
    social.merge_socials(socials, site.get("socials") or {})
    domain = site.get("domain") or (social.registrable_domain(lead["website_url"]) if lead.get("website_url") else "")
    for platform in ("instagram", "tiktok"):
        items = socials.get(platform, [])
        best = social.pick_best(items, lead.get("name", ""), domain)
        if best:
            lead[platform] = {"handle": best["ident"], "url": best["url"], "via": best.get("via", ""),
                              "status": "verlinkt", "metrics": None, "error": "",
                              "andere": [i["ident"] for i in items if i["ident"] != best["ident"]][:4]}
            if platform == "tiktok":
                lead[platform]["exists"] = None
        else:
            feed = platform == "instagram" and site.get("status") == "ok" and site.get("instagram_feed")
            lead[platform] = {"handle": "", "url": "", "via": "website" if feed else "",
                              "status": "feed" if feed else "nicht_gefunden", "metrics": None, "error": "", "andere": []}
    lead["profile"] = {p: socials[p][0]["url"] for p in OTHER_PLATFORMS if socials.get(p)}
    lead["socials"] = socials


def run(options: Options, settings: Settings, progress: Progress) -> dict:
    started = time.time()
    notes: list = []
    self_test(settings)

    # 1. Firmen finden
    progress.set_phase("Firmen suchen")
    leads, source, discovery_notes = discovery.discover(options.branchen, options.orte, options.anzahl, options.quelle,
                                                        options.liste, settings, progress.log, progress.cancelled)
    notes += discovery_notes
    if not leads:
        raise SetupError("Keine Firmen gefunden. Andere Schreibweise, einen größeren Ort oder eine andere Quelle probieren.")
    progress.log(f"{len(leads)} Firmen insgesamt")

    # 2. Link-Seiten (Linktree & Co.) auslesen
    hubs = [l for l in leads if l.get("linkhub")]
    if hubs and not progress.cancelled():
        progress.set_phase("Link-Seiten auslesen", len(hubs))
        for lead in hubs:
            hub = social.scan_linkhub(lead["linkhub"], settings.user_agent)
            social.merge_socials(lead["socials"], hub["socials"], via="linkhub")
            if hub["website"] and not lead.get("website_url"):
                lead["website_url"] = social.normalize_url(hub["website"])
            progress.step()

    # 3. Websites prüfen (parallel, pro Host gedrosselt)
    with_site = [l for l in leads if l.get("website_url")]
    progress.set_phase("Websites prüfen", len(with_site))
    if with_site and not progress.cancelled():
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = {pool.submit(website.analyze, l["website_url"], user_agent=settings.user_agent,
                                   name="" if l.get("name_from_domain") else l.get("name", "")): l
                       for l in with_site}
            for fut in as_completed(futures):
                lead = futures[fut]
                if fut.cancelled():
                    continue
                try:
                    lead["website"] = fut.result()
                except Exception as e:  # einzelne Fehler dürfen den Lauf nicht stoppen
                    lead["website"] = website._empty(lead["website_url"])
                    lead["website"]["status_text"] = f"Analyse fehlgeschlagen: {e}"
                progress.step()
                progress.log(f"  {_short(lead)}: {lead['website']['status_text']}")
                if progress.cancelled():
                    for other in futures:
                        other.cancel()
    for lead in with_site:
        if not lead.get("website"):
            lead["website"] = website._empty(lead["website_url"])
            lead["website"].update(status="gesperrt", status_text="nicht geprüft (abgebrochen)")
        if lead.get("name_from_domain") and lead["website"].get("title"):
            lead["name"] = _name_from_title(lead["website"]["title"]) or lead["name"]

    # 4. TikTok-Kurzlinks auflösen, Profile zusammenführen
    if options.tiktok and not progress.cancelled():
        for lead in leads:
            site_socials = (lead.get("website") or {}).get("socials") or {}
            shorts = (lead.get("socials") or {}).get("tiktok_short", []) + site_socials.get("tiktok_short", [])
            has_tt = (lead.get("socials") or {}).get("tiktok") or site_socials.get("tiktok")
            if shorts and not has_tt:
                target = social.resolve_short_link(shorts[0]["url"], settings.user_agent)
                item = social.classify_social(target) if target else None
                if item and item[0] == "tiktok":
                    social.merge_socials(lead["socials"], {"tiktok": [{"ident": item[1], "url": item[2],
                                                                       "via": shorts[0].get("via", "link")}]})
    for lead in leads:
        _collect_profiles(lead)

    # 5. Instagram-Kennzahlen über die offizielle Meta-API
    if options.instagram and settings.has_meta and not progress.cancelled():
        meta = social.MetaClient(settings.meta_access_token, settings.meta_ig_user_id, settings.meta_graph_version,
                                 settings.user_agent, notes)
        targets = [l for l in leads if l["instagram"]["handle"]]
        guess = [l for l in leads if not l["instagram"]["handle"] and (l.get("website") or {}).get("domain")] \
            if options.ig_suche else []
        progress.set_phase("Instagram-Kennzahlen (Meta-API)", len(targets) + len(guess))
        for lead in targets:
            if progress.cancelled() or meta.disabled:
                break
            res = meta.lookup(lead["instagram"]["handle"])
            lead["instagram"].update(status=res["status"], metrics=res.get("metrics"), error=res.get("error", ""))
            progress.step()
        for lead in guess:
            if progress.cancelled() or meta.disabled:
                break
            domain = lead["website"]["domain"]
            for cand in social.instagram_candidates(domain):
                res = meta.lookup(cand)
                site_of_account = ((res.get("metrics") or {}).get("website") or "")
                if res["status"] == "ok" and site_of_account and social.registrable_domain(site_of_account) == domain:
                    lead["instagram"] = {"handle": cand, "url": f"https://www.instagram.com/{cand}/", "via": "meta-suche",
                                         "status": "ok", "metrics": res["metrics"], "error": "", "andere": []}
                    progress.log(f"  {_short(lead)}: Instagram @{cand} über Meta-Suche gefunden")
                    break
            progress.step()
    elif options.instagram and not settings.has_meta:
        notes.append("Instagram-Kennzahlen (Follower, letzter Beitrag, Reels-Anteil) sind nicht aktiv: dafür die "
                     "Meta-API einrichten (README, Abschnitt „Instagram-Kennzahlen“). Gefundene Profile sind verlinkt.")

    # 6. TikTok prüfen (offizielles oEmbed + öffentliches Creator-Embed)
    if options.tiktok and not progress.cancelled():
        client = social.TikTokClient(settings.user_agent, notes)
        targets = [l for l in leads if l["tiktok"]["handle"]]
        progress.set_phase("TikTok-Profile prüfen", len(targets))
        for lead in targets:
            if progress.cancelled():
                break
            res = client.check(lead["tiktok"]["handle"])
            lead["tiktok"].update(exists=res["exists"], status=res["status"], metrics=res["metrics"],
                                  error=res["error"], name=res.get("name", ""))
            progress.step()

    # 7. PageSpeed (optional)
    if options.pagespeed and not progress.cancelled():
        targets = [l for l in leads if (l.get("website") or {}).get("status") == "ok"]
        if not settings.has_google:
            notes.append("PageSpeed ohne GOOGLE_API_KEY ist stark begrenzt – bei Fehlern Schlüssel hinterlegen.")
        progress.set_phase("PageSpeed messen (mobil, ca. 20 s pro Website)", len(targets))
        stop = threading.Event()

        def measure(lead):
            if stop.is_set() or progress.cancelled():
                return lead, None
            return lead, google.pagespeed(lead["website"]["final_url"], api_key=settings.google_api_key,
                                          sprache=settings.sprache, user_agent=settings.user_agent)

        with ThreadPoolExecutor(max_workers=4 if settings.has_google else 1) as pool:
            for fut in as_completed([pool.submit(measure, l) for l in targets]):
                lead, res = fut.result()
                progress.step()
                if res is None:
                    continue
                lead["website"]["pagespeed"] = res
                if res.get("error"):
                    progress.log(f"  {_short(lead)}: {res['error']}")
                    if "Kontingent" in res["error"] or "Schlüssel" in res["error"] or "aktiviert" in res["error"]:
                        if not stop.is_set():
                            notes.append(f"PageSpeed abgebrochen: {res['error']}")
                        stop.set()
                else:
                    progress.log(f"  {_short(lead)}: PageSpeed {res.get('performance')}/100")

    # 8. Bewertung und Bericht
    progress.set_phase("Bewerten und Bericht erstellen")
    market = scoring.evaluate(leads)
    leads.sort(key=lambda l: (-l["scores"]["potenzial"], l["name"].lower()))
    if progress.cancelled():
        notes.insert(0, "Abgebrochen – der Bericht ist unvollständig.")
    for lead in leads:
        lead["suchlinks"] = social.search_links(lead["name"], lead.get("ort") or "")
    result = {
        "version": __version__,
        "erstellt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "suche": {"titel": options.title(), "branchen": options.branchen, "orte": options.orte,
                  "anzahl": options.anzahl, "quelle": source},
        "optionen": {"pagespeed": options.pagespeed, "tiktok": options.tiktok,
                     "instagram_meta": bool(options.instagram and settings.has_meta)},
        "markt": market,
        "hinweise": notes,
        "abgebrochen": progress.cancelled(),
        "dauer_s": round(time.time() - started),
        "leads": leads,
    }
    result["dateien"] = report.write_all(result, settings.report_dir)
    progress.log(f"Fertig: {len(leads)} Firmen bewertet, {market.get('potenzial_hoch', 0)} mit hohem Potenzial.")
    return result


def rescore(json_path) -> dict:
    """Bewertet einen gespeicherten Bericht neu (z. B. nach Änderungen in scoring.py) – ohne neues Abrufen."""
    import json
    from pathlib import Path as _Path

    path = _Path(json_path)
    result = json.loads(path.read_text(encoding="utf-8"))
    leads = result.get("leads") or []
    for lead in leads:
        for key in ("scores", "checks", "badges", "ansatzpunkte", "hinweise", "tags"):
            lead.pop(key, None)
    result["markt"] = scoring.evaluate(leads)
    leads.sort(key=lambda l: (-l["scores"]["potenzial"], l["name"].lower()))
    for lead in leads:
        lead["suchlinks"] = social.search_links(lead["name"], lead.get("ort") or "")
    result["dateien"] = report.write_in_place(result, path)
    return result

