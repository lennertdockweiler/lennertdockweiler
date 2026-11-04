"""Einstellungen laden: zuerst Umgebungsvariablen, dann die Datei .env im Ordner lead-scout."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from . import __version__

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"
REPORT_DIR = BASE_DIR / "berichte"


class SetupError(Exception):
    """Fehlende oder falsche Einrichtung (Schlüssel, Zertifikate …) mit verständlicher Meldung."""


def load_env_file(path: Path) -> dict:
    """Liest KEY=VALUE-Zeilen. Kommentare (#) und Anführungszeichen werden berücksichtigt."""
    values: dict = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        if key.startswith("export "):
            key = key[len("export "):].strip()
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        else:
            val = val.split(" #", 1)[0].strip()
        values[key] = val
    return values


@dataclass
class Settings:
    google_api_key: str = ""
    meta_access_token: str = ""
    meta_ig_user_id: str = ""
    meta_graph_version: str = "v23.0"
    land: str = "DE"
    sprache: str = "de"
    kontakt: str = ""
    report_dir: Path = field(default_factory=lambda: REPORT_DIR)

    @property
    def user_agent(self) -> str:
        extra = f"; +{self.kontakt}" if self.kontakt else ""
        return f"Mozilla/5.0 (compatible; LeadScout/{__version__}{extra})"

    @property
    def has_google(self) -> bool:
        return bool(self.google_api_key)

    @property
    def has_meta(self) -> bool:
        return bool(self.meta_access_token and self.meta_ig_user_id)

    def public_status(self) -> dict:
        """Status ohne geheime Werte, z. B. für die Oberfläche."""
        return {
            "google": self.has_google,
            "meta": self.has_meta,
            "meta_token_ohne_id": bool(self.meta_access_token and not self.meta_ig_user_id),
            "land": self.land,
            "kontakt": bool(self.kontakt),
            "env_datei": ENV_FILE.exists(),
        }


def load_settings() -> Settings:
    file_values = load_env_file(ENV_FILE)

    def get(name: str, default: str = "") -> str:
        value = os.environ.get(name)
        if value is None or value == "":
            value = file_values.get(name, "")
        return (value or default).strip()

    land = get("LAND", "DE").upper()[:2] or "DE"
    report_dir = get("BERICHTE_ORDNER")
    return Settings(
        google_api_key=get("GOOGLE_API_KEY"),
        meta_access_token=get("META_ACCESS_TOKEN"),
        meta_ig_user_id=get("META_IG_USER_ID"),
        meta_graph_version=get("META_GRAPH_VERSION", "v23.0"),
        land=land,
        sprache=get("SPRACHE", "de").lower() or "de",
        kontakt=get("KONTAKT"),
        report_dir=Path(report_dir).expanduser() if report_dir else REPORT_DIR,
    )
