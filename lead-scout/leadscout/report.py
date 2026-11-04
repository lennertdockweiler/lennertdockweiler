"""Berichte schreiben: interaktive HTML-Seite, CSV (Excel, deutsch) und JSON (Rohdaten)."""
from __future__ import annotations

import csv
import html
import json
import re
from datetime import datetime
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent / "templates" / "report.html"


def slug(text: str, limit: int = 50) -> str:
    t = text.lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        t = t.replace(a, b)
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    return (t[:limit].rstrip("-")) or "suche"


def _yes(value) -> str:
    return "Ja" if value else "Nein"


def _num(value, digits: int = 0) -> str:
    if value is None or value == "":
        return ""
    if digits:
        return f"{value:.{digits}f}".replace(".", ",")
    return str(int(round(value)))


def _safe(value) -> str:
    """Schutz vor Formel-Injektion in Excel."""
    text = "" if value is None else str(value)
    if text and text[0] in "=+-@\t\r":
        return "'" + text
    return text


def csv_rows(result: dict) -> list:
    rows = []
    for l in result["leads"]:
        s = l["scores"]
        w = l.get("website") or {}
        psi = w.get("pagespeed") or {}
        ig, tt = l.get("instagram") or {}, l.get("tiktok") or {}
        igm, ttm = ig.get("metrics") or {}, tt.get("metrics") or {}
        rows.append({
            "Potenzial": s["potenzial"],
            "Potenzial-Stufe": s["potenzial_label"],
            "Präsenz": s["praesenz"],
            "Firma": l["name"],
            "Kategorie": l.get("category", ""),
            "Adresse": l.get("address", ""),
            "Telefon": l.get("phone") or (w.get("phones") or [""])[0],
            "E-Mail": (w.get("emails") or [l.get("email_hint", "")])[0] if (w.get("emails") or l.get("email_hint")) else "",
            "Website": l.get("website_url") or (f"nur {l['website_platform']}" if l.get("website_platform") else ""),
            "Website-Score": "" if s["website"] is None else s["website"],
            "Website-Status": w.get("status_text", "") if l.get("website_url") else "keine eigene Website",
            "HTTPS": _yes(w.get("https")) if w.get("status") == "ok" else "",
            "Mobil optimiert": _yes(w.get("viewport")) if w.get("status") == "ok" else "",
            "PageSpeed mobil": psi.get("performance", "") if psi else "",
            "CMS/Baukasten": w.get("cms", ""),
            "Copyright": w.get("copyright_year") or "",
            "Impressum": _yes(w.get("impressum")) if w.get("status") == "ok" else "",
            "Instagram": ig.get("url", ""),
            "IG-Follower": igm.get("followers", ""),
            "IG-Beiträge": igm.get("posts", ""),
            "IG letzter Beitrag (Tage)": igm.get("last_post_days", ""),
            "IG Reels-Anteil %": _num((igm.get("reels_share") or 0) * 100) if igm.get("reels_share") is not None else "",
            "IG-Score": s["instagram"],
            "TikTok": tt.get("url", "") if tt.get("exists") is not False else "",
            "TT-Follower": ttm.get("followers", ""),
            "TT letztes Video (Tage)": ttm.get("last_video_days", ""),
            "TT Ø Aufrufe": ttm.get("avg_views", ""),
            "TT-Score": s["tiktok"],
            "Facebook": (l.get("profile") or {}).get("facebook", ""),
            "Google-Bewertung": _num(l.get("rating"), 1) if l.get("rating") else "",
            "Rezensionen": l.get("reviews") if l.get("reviews") is not None else "",
            "Google Maps": l.get("maps_url", ""),
            "Merkmale": ", ".join(l.get("tags") or []),
            "Ansatzpunkte": " | ".join(a["text"] for a in (l.get("ansatzpunkte") or [])[:6]),
            "Gut zu wissen": " | ".join(h["text"] for h in (l.get("hinweise") or [])[:4]),
            "Quelle": l.get("source", ""),
            "Suche": f"{l.get('branche', '')} in {l.get('ort', '')}".strip() if l.get("branche") else "",
        })
    return rows


def write_csv(result: dict, path: Path) -> None:
    rows = csv_rows(result)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        if not rows:
            fh.write("Keine Ergebnisse\n")
            return
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), delimiter=";", quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: _safe(v) for k, v in row.items()})


def render_html(result: dict) -> str:
    template = TEMPLATE.read_text(encoding="utf-8")
    payload = json.dumps(result, ensure_ascii=False).replace("<", "\\u003c")
    title = html.escape(result["suche"]["titel"])
    return template.replace("__TITLE__", title).replace("__DATA__", payload)


def write_all(result: dict, report_dir: Path) -> dict:
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    base = f"{stamp}_{slug(result['suche']['titel'])}"
    n = 2
    while (report_dir / f"{base}.html").exists():
        base = f"{stamp}_{slug(result['suche']['titel'])}_{n}"
        n += 1
    files = {"html": f"{base}.html", "csv": f"{base}.csv", "json": f"{base}.json"}
    result["dateien"] = files
    (report_dir / files["json"]).write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    write_csv(result, report_dir / files["csv"])
    (report_dir / files["html"]).write_text(render_html(result), encoding="utf-8")
    return files


def write_in_place(result: dict, json_path: Path) -> dict:
    """Schreibt JSON, CSV und HTML unter dem bestehenden Dateinamen neu."""
    base = json_path.stem
    files = {"html": f"{base}.html", "csv": f"{base}.csv", "json": f"{base}.json"}
    result["dateien"] = files
    folder = json_path.parent
    (folder / files["json"]).write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    write_csv(result, folder / files["csv"])
    (folder / files["html"]).write_text(render_html(result), encoding="utf-8")
    return files


def list_reports(report_dir: Path, limit: int = 30) -> list:
    """Übersicht vorhandener Berichte (neueste zuerst)."""
    if not report_dir.exists():
        return []
    out = []
    for path in sorted(report_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        base = path.stem
        if not (report_dir / f"{base}.html").exists():
            continue
        markt = data.get("markt") or {}
        out.append({
            "titel": (data.get("suche") or {}).get("titel", base),
            "erstellt": data.get("erstellt", ""),
            "firmen": markt.get("firmen", len(data.get("leads") or [])),
            "potenzial_hoch": markt.get("potenzial_hoch", 0),
            "quelle": (data.get("suche") or {}).get("quelle", ""),
            "html": f"{base}.html",
            "csv": f"{base}.csv" if (report_dir / f"{base}.csv").exists() else "",
        })
    return out
