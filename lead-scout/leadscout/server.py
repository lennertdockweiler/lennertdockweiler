"""Lokale Oberfläche im Browser. Läuft nur auf diesem Rechner (127.0.0.1), ohne Zusatzpakete."""
from __future__ import annotations

import json
import threading
import traceback
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from . import __version__, pipeline, report
from .config import SetupError, load_settings

APP_HTML = Path(__file__).resolve().parent / "templates" / "app.html"
FILE_TYPES = {".html": "text/html; charset=utf-8", ".csv": "text/csv; charset=utf-8", ".json": "application/json; charset=utf-8"}


class JobManager:
    """Eine Suche zur Zeit; Fortschritt wird von der Oberfläche abgefragt."""

    def __init__(self):
        self._lock = threading.Lock()
        self.job = None

    def start(self, options: pipeline.Options) -> str:
        with self._lock:
            if self.job and self.job["status"] == "laeuft":
                raise RuntimeError("Es läuft bereits eine Suche.")
            job = {"id": uuid.uuid4().hex[:8], "status": "laeuft", "titel": options.title(),
                   "progress": pipeline.Progress(), "result": None, "fehler": ""}
            self.job = job
        threading.Thread(target=self._run, args=(job, options), daemon=True).start()
        return job["id"]

    def _run(self, job: dict, options: pipeline.Options) -> None:
        try:
            result = pipeline.run(options, load_settings(), job["progress"])
            job["result"] = {k: result[k] for k in ("dateien", "markt", "hinweise", "abgebrochen")}
            job["status"] = "fertig"
        except SetupError as e:
            job["fehler"] = str(e)
            job["status"] = "fehler"
        except Exception as e:  # unerwartet: Meldung zeigen, Details ins Protokoll
            job["fehler"] = f"Unerwarteter Fehler: {e}"
            job["progress"].log(traceback.format_exc(limit=3))
            job["status"] = "fehler"

    def cancel(self) -> None:
        with self._lock:
            if self.job and self.job["status"] == "laeuft":
                self.job["progress"].cancel_event.set()
                self.job["progress"].log("Abbruch angefordert – laufende Abrufe werden beendet …")

    def snapshot(self):
        job = self.job
        if not job:
            return None
        return {"id": job["id"], "status": job["status"], "titel": job["titel"], "fehler": job["fehler"],
                "ergebnis": job["result"], **job["progress"].snapshot()}


class Handler(BaseHTTPRequestHandler):
    server_version = "LeadScout"

    def log_message(self, fmt, *args):  # ruhige Konsole
        pass

    # --- Hilfen ---
    def _send(self, status: int, body: bytes, ctype: str, extra: dict | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, data) -> None:
        self._send(status, json.dumps(data, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def _host_ok(self) -> bool:
        return (self.headers.get("Host") or "").lower() in self.server.allowed_hosts

    def _origin_ok(self) -> bool:
        origin = self.headers.get("Origin")
        if origin and urlparse(origin).netloc.lower() not in self.server.allowed_hosts:
            return False
        site = self.headers.get("Sec-Fetch-Site")
        return site in (None, "same-origin", "none")

    # --- GET ---
    def do_GET(self):
        if not self._host_ok():
            return self._send(403, b"Forbidden", "text/plain")
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            return self._send(200, APP_HTML.read_bytes(), "text/html; charset=utf-8")
        if path == "/api/status":
            settings = load_settings()
            return self._json(200, {"version": __version__, "einstellungen": settings.public_status(),
                                    "job": self.server.jobs.snapshot(),
                                    "berichte": report.list_reports(settings.report_dir)})
        if path == "/api/job":
            return self._json(200, self.server.jobs.snapshot())
        if path.startswith("/berichte/"):
            return self._serve_report(unquote(path[len("/berichte/"):]))
        return self._send(404, b"Nicht gefunden", "text/plain; charset=utf-8")

    def _serve_report(self, name: str):
        report_dir = load_settings().report_dir.resolve()
        if not name or "/" in name or "\\" in name or name.startswith(".") or Path(name).suffix not in FILE_TYPES:
            return self._send(404, b"Nicht gefunden", "text/plain; charset=utf-8")
        target = (report_dir / name).resolve()
        if target.parent != report_dir or not target.is_file():
            return self._send(404, b"Nicht gefunden", "text/plain; charset=utf-8")
        extra = {"Content-Disposition": f'attachment; filename="{target.name}"'} if target.suffix == ".csv" else None
        return self._send(200, target.read_bytes(), FILE_TYPES[target.suffix], extra)

    # --- POST ---
    def do_POST(self):
        if not self._host_ok() or not self._origin_ok():
            return self._send(403, b"Forbidden", "text/plain")
        if "application/json" not in (self.headers.get("Content-Type") or ""):
            return self._json(415, {"fehler": "JSON erwartet"})
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length > 1_000_000:
            return self._json(413, {"fehler": "Anfrage zu groß"})
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            return self._json(400, {"fehler": "Ungültiges JSON"})
        path = urlparse(self.path).path
        if path == "/api/start":
            options = pipeline.Options.from_dict(body if isinstance(body, dict) else {})
            if options.quelle != "liste" and (not options.branchen or not options.orte):
                return self._json(400, {"fehler": "Bitte Branche und Ort angeben."})
            try:
                return self._json(200, {"job": self.server.jobs.start(options)})
            except RuntimeError as e:
                return self._json(409, {"fehler": str(e)})
        if path == "/api/cancel":
            self.server.jobs.cancel()
            return self._json(200, {"ok": True})
        if path == "/api/pruefen":
            return self._json(200, {"ergebnisse": pipeline.check_connections(load_settings())})
        return self._json(404, {"fehler": "Unbekannt"})


def serve(port: int = 8765, open_browser: bool = True) -> None:
    httpd = None
    for candidate in range(port, port + 10):
        try:
            httpd = ThreadingHTTPServer(("127.0.0.1", candidate), Handler)
            port = candidate
            break
        except OSError:
            continue
    if httpd is None:
        raise SetupError(f"Kein freier Port zwischen {port} und {port + 9} gefunden.")
    httpd.daemon_threads = True
    httpd.allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
    httpd.jobs = JobManager()
    url = f"http://127.0.0.1:{port}/"
    print(f"Lead-Scout läuft unter {url}  (Beenden mit Strg+C)")
    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nLead-Scout beendet.")
    finally:
        httpd.server_close()
