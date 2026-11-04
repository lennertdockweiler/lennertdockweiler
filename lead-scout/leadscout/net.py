"""HTTP-Helfer (nur Standardbibliothek).

- Zeit- und Größenlimits, gzip/deflate, Protokoll der Weiterleitungen
- höfliche Drosselung pro Host (THROTTLE)
- robots.txt-Prüfung (ROBOTS)
- keine Abrufe von lokalen/privaten Adressen (Schutz bei Weiterleitungen)
"""
from __future__ import annotations

import ipaddress
import json
import os
import re
import socket
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from dataclasses import dataclass, field
from http.client import HTTPException
from urllib.robotparser import RobotFileParser

DEFAULT_TIMEOUT = 15
MAX_BYTES = 3_000_000
MAX_DECOMPRESSED = 12_000_000
ACCEPT_HTML = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
ACCEPT_JSON = "application/json"
DEFAULT_UA = "Mozilla/5.0 (compatible; LeadScout/1.0)"

_ssl_lock = threading.Lock()
_ssl_ctx: ssl.SSLContext | None = None


def ssl_context() -> ssl.SSLContext:
    """Standard-Zertifikatsspeicher; falls leer (z. B. Python von python.org auf macOS) wird certifi genutzt."""
    global _ssl_ctx
    with _ssl_lock:
        if _ssl_ctx is None:
            ctx = ssl.create_default_context()
            if not (os.environ.get("SSL_CERT_FILE") or os.environ.get("SSL_CERT_DIR")):
                try:
                    if ctx.cert_store_stats().get("x509_ca", 0) == 0:
                        import certifi  # type: ignore

                        ctx = ssl.create_default_context(cafile=certifi.where())
                except Exception:
                    pass
            _ssl_ctx = ctx
        return _ssl_ctx


def is_blocked_host(host: str) -> bool:
    """True für localhost und private/reservierte IP-Adressen."""
    if not host:
        return True
    h = host.strip("[]").lower().rstrip(".")
    if h == "localhost" or h.endswith((".localhost", ".local", ".internal", ".lan", ".home.arpa")):
        return True
    try:
        ip = ipaddress.ip_address(h)
    except ValueError:
        return False
    return bool(ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
                or ip.is_multicast or ip.is_unspecified)


@dataclass
class Response:
    url: str
    final_url: str = ""
    status: int = 0
    headers: dict = field(default_factory=dict)
    body: bytes = b""
    error: str = ""          # "", ssl, dns, timeout, connection, blocked, invalid_url
    error_detail: str = ""
    redirects: list = field(default_factory=list)
    ttfb: float = 0.0
    elapsed: float = 0.0
    truncated: bool = False

    @property
    def ok(self) -> bool:
        return not self.error and 200 <= self.status < 300

    @property
    def content_type(self) -> str:
        return self.headers.get("content-type", "").lower()

    def text(self) -> str:
        m = re.search(r"charset=[\"']?([\w\-:.]+)", self.headers.get("content-type", ""), re.I)
        declared = m.group(1) if m else ""
        if not declared:
            head = self.body[:4096].decode("ascii", "ignore")
            m = re.search(r"<meta[^>]+charset=[\"']?([\w\-:.]+)", head, re.I)
            declared = m.group(1) if m else ""
        if declared:
            try:
                return self.body.decode(declared, "replace")
            except LookupError:
                pass
        try:
            return self.body.decode("utf-8")
        except UnicodeDecodeError:
            return self.body.decode("cp1252", "replace")

    def json(self):
        try:
            return json.loads(self.body.decode("utf-8", "replace"))
        except (ValueError, UnicodeDecodeError):
            return None

    def describe_error(self) -> str:
        """Kurze deutsche Fehlerbeschreibung."""
        if self.error == "ssl":
            return "SSL-Zertifikat fehlerhaft"
        if self.error == "dns":
            return "Domain existiert nicht oder ist nicht erreichbar"
        if self.error == "timeout":
            return "Zeitüberschreitung"
        if self.error == "blocked":
            return "Ziel blockiert (lokale Adresse)"
        if self.error == "invalid_url":
            return "Ungültige Adresse"
        if self.error:
            return "Verbindung fehlgeschlagen"
        if self.status >= 400:
            return f"HTTP-Fehler {self.status}"
        return ""


class _RedirectRecorder(urllib.request.HTTPRedirectHandler):
    max_redirections = 8

    def __init__(self):
        super().__init__()
        self.chain: list = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        host = urllib.parse.urlparse(newurl).hostname or ""
        if is_blocked_host(host):
            raise urllib.error.URLError("blocked redirect")
        self.chain.append([code, newurl])
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _decompress(raw: bytes, encoding: str) -> bytes:
    enc = (encoding or "").lower()
    if not raw or not enc or enc == "identity":
        return raw
    try:
        if "gzip" in enc:
            return zlib.decompressobj(16 + zlib.MAX_WBITS).decompress(raw, MAX_DECOMPRESSED)
        if "deflate" in enc:
            try:
                return zlib.decompressobj().decompress(raw, MAX_DECOMPRESSED)
            except zlib.error:
                return zlib.decompressobj(-zlib.MAX_WBITS).decompress(raw, MAX_DECOMPRESSED)
    except zlib.error:
        return raw
    return raw


def _classify(reason) -> tuple:
    if isinstance(reason, ssl.SSLCertVerificationError):
        return "ssl", getattr(reason, "verify_message", "") or str(reason)
    if isinstance(reason, ssl.SSLError):
        return "ssl", str(reason)
    if isinstance(reason, socket.gaierror):
        return "dns", str(reason)
    if isinstance(reason, (socket.timeout, TimeoutError)):
        return "timeout", str(reason)
    text = str(reason)
    if "blocked redirect" in text:
        return "blocked", text
    if "CERTIFICATE_VERIFY_FAILED" in text or "SSL" in text:
        return "ssl", text
    if "timed out" in text:
        return "timeout", text
    if "Name or service not known" in text or "nodename nor servname" in text or "getaddrinfo" in text:
        return "dns", text
    return "connection", text


def fetch(url: str, *, method: str = "GET", data=None, headers: dict | None = None,
          timeout: float = DEFAULT_TIMEOUT, max_bytes: int = MAX_BYTES,
          user_agent: str = "", accept: str = ACCEPT_HTML) -> Response:
    """Ruft eine URL ab und gibt immer ein Response-Objekt zurück (wirft keine Netzwerkfehler)."""
    resp = Response(url=url, final_url=url)
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        resp.error, resp.error_detail = "invalid_url", "Nur http(s)-Adressen werden abgerufen"
        return resp
    if is_blocked_host(parsed.hostname):
        resp.error, resp.error_detail = "blocked", "Lokale Adresse"
        return resp

    hdrs = {
        "User-Agent": user_agent or DEFAULT_UA,
        "Accept": accept,
        "Accept-Language": "de-DE,de;q=0.9,en;q=0.7",
        "Accept-Encoding": "gzip, deflate",
    }
    if headers:
        hdrs.update(headers)
    body = data
    if isinstance(data, (dict, list)):
        body = json.dumps(data).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")
    elif isinstance(data, str):
        body = data.encode("utf-8")

    recorder = _RedirectRecorder()
    opener = urllib.request.build_opener(recorder, urllib.request.HTTPSHandler(context=ssl_context()))
    req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    start = time.monotonic()
    raw = b""
    try:
        with opener.open(req, timeout=timeout) as r:
            resp.ttfb = time.monotonic() - start
            resp.status = r.getcode() or 0
            resp.final_url = r.geturl() or url
            resp.headers = {k.lower(): v for k, v in r.headers.items()}
            raw = r.read(max_bytes + 1)
    except urllib.error.HTTPError as e:
        resp.ttfb = time.monotonic() - start
        resp.status = e.code
        resp.final_url = e.geturl() or url
        resp.headers = {k.lower(): v for k, v in (e.headers.items() if e.headers else [])}
        try:
            raw = e.read(max_bytes + 1)
        except Exception:
            raw = b""
    except urllib.error.URLError as e:
        resp.error, resp.error_detail = _classify(e.reason)
    except (socket.timeout, TimeoutError) as e:
        resp.error, resp.error_detail = "timeout", str(e)
    except ssl.SSLError as e:
        resp.error, resp.error_detail = "ssl", str(e)
    except (HTTPException, ConnectionError, OSError) as e:
        resp.error, resp.error_detail = _classify(e)
    except ValueError as e:
        resp.error, resp.error_detail = "invalid_url", str(e)

    resp.redirects = recorder.chain
    if len(raw) > max_bytes:
        raw = raw[:max_bytes]
        resp.truncated = True
    resp.body = _decompress(raw, resp.headers.get("content-encoding", ""))
    resp.elapsed = time.monotonic() - start
    return resp


class HostThrottle:
    """Sorgt für Mindestabstände zwischen Anfragen an denselben Host bzw. Dienst."""

    def __init__(self):
        self._lock = threading.Lock()
        self._next: dict = {}

    def wait(self, key: str, interval: float) -> None:
        with self._lock:
            now = time.monotonic()
            slot = max(now, self._next.get(key, 0.0))
            self._next[key] = slot + interval
        delay = slot - now
        if delay > 0:
            time.sleep(delay)


THROTTLE = HostThrottle()


def host_of(url: str) -> str:
    host = (urllib.parse.urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


class RobotsCache:
    """robots.txt pro Origin abrufen und auswerten (RFC 9309: 4xx = keine Einschränkung)."""

    def __init__(self):
        self._lock = threading.Lock()
        self._cache: dict = {}

    def _get(self, url: str, user_agent: str):
        p = urllib.parse.urlparse(url)
        origin = f"{p.scheme}://{p.netloc}"
        with self._lock:
            if origin in self._cache:
                return self._cache[origin]
        THROTTLE.wait(host_of(url), 0.5)
        r = fetch(origin + "/robots.txt", user_agent=user_agent, timeout=10, max_bytes=500_000,
                  accept="text/plain,*/*;q=0.5")
        parser = None
        if r.ok and r.body:
            text = r.text()
            if not text.lstrip().startswith("<"):
                parser = RobotFileParser()
                parser.parse(text.splitlines())
        with self._lock:
            self._cache[origin] = parser
        return parser

    def check(self, url: str, user_agent: str) -> dict:
        parser = self._get(url, user_agent)
        if parser is None:
            return {"allowed": True, "google_blocked": False, "exists": False}
        return {
            "allowed": parser.can_fetch("LeadScout", url),
            "google_blocked": not parser.can_fetch("Googlebot", url),
            "exists": True,
        }


ROBOTS = RobotsCache()
