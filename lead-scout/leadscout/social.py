"""Social-Media-Profile erkennen und bewerten.

- Links auf Instagram, TikTok, Facebook, YouTube … aus Website, Google-/OSM-Eintrag und Link-Seiten (Linktree)
- Instagram-Kennzahlen ausschließlich über die offizielle Meta Graph API (Business Discovery)
- TikTok: offizielle oEmbed-Schnittstelle (Existenz) und öffentliches Creator-Embed (Kennzahlen)
"""
from __future__ import annotations

import json
import re
import statistics
import time
import urllib.parse
from datetime import datetime, timezone

from . import net

# ---------------------------------------------------------------------------
# Plattformen und Domains
# ---------------------------------------------------------------------------

SOCIAL_HOSTS = {
    "instagram.com": "instagram", "instagr.am": "instagram",
    "tiktok.com": "tiktok",
    "facebook.com": "facebook", "fb.com": "facebook", "fb.me": "facebook",
    "youtube.com": "youtube", "youtu.be": "youtube",
    "linkedin.com": "linkedin", "xing.com": "xing",
    "twitter.com": "x", "x.com": "x",
    "pinterest.com": "pinterest", "pinterest.de": "pinterest", "pinterest.at": "pinterest", "pinterest.ch": "pinterest",
    "wa.me": "whatsapp", "whatsapp.com": "whatsapp",
    "threads.net": "threads", "threads.com": "threads",
}
LINKHUB_HOSTS = {
    "linktr.ee": "Linktree", "linkin.bio": "Linkin.bio", "beacons.ai": "Beacons", "bio.link": "bio.link",
    "lnk.bio": "Lnk.Bio", "campsite.bio": "Campsite", "taplink.cc": "Taplink", "tap.bio": "Tap Bio",
    "solo.to": "solo.to", "milkshake.app": "Milkshake", "msha.ke": "Milkshake", "linkbio.co": "Linkbio",
    "allmylinks.com": "AllMyLinks", "linkr.bio": "Linkr", "hoo.be": "hoo.be", "bento.me": "Bento",
    "linkpop.com": "Linkpop", "koji.to": "Koji", "withkoji.com": "Koji", "snipfeed.co": "Snipfeed",
}
PORTAL_HOSTS = {
    "treatwell.de": "Treatwell", "treatwell.at": "Treatwell", "treatwell.ch": "Treatwell", "treatwell.com": "Treatwell",
    "booksy.com": "Booksy", "planity.com": "Planity", "salonized.com": "Salonized", "shore.com": "Shore",
    "fresha.com": "Fresha", "doctolib.de": "Doctolib", "jameda.de": "Jameda", "dr-flex.de": "Dr. Flex",
    "opentable.de": "OpenTable", "opentable.com": "OpenTable", "quandoo.de": "Quandoo", "resmio.com": "resmio",
    "thefork.de": "TheFork", "lieferando.de": "Lieferando", "lieferando.at": "Lieferando", "wolt.com": "Wolt",
    "ubereats.com": "Uber Eats", "yelp.de": "Yelp", "yelp.com": "Yelp", "gelbeseiten.de": "Gelbe Seiten",
    "dasoertliche.de": "Das Örtliche", "11880.com": "11880", "golocal.de": "golocal", "meinestadt.de": "meinestadt.de",
    "werkenntdenbesten.de": "WerkenntdenBESTEN", "myhammer.de": "MyHammer", "eversports.de": "Eversports",
    "eversports.com": "Eversports", "check24.de": "Check24", "tripadvisor.de": "Tripadvisor",
    "tripadvisor.com": "Tripadvisor", "booking.com": "Booking.com", "airbnb.de": "Airbnb", "airbnb.com": "Airbnb",
    "etsy.com": "Etsy", "ebay.de": "eBay", "kleinanzeigen.de": "Kleinanzeigen", "mobile.de": "mobile.de",
    "autoscout24.de": "AutoScout24", "immobilienscout24.de": "ImmoScout24", "speisekarte.de": "Speisekarte.de",
}
BUILDER_HOSTS = {
    "wixsite.com": "Wix", "jimdosite.com": "Jimdo", "jimdofree.com": "Jimdo", "jimdo.com": "Jimdo",
    "webnode.page": "Webnode", "webnode.de": "Webnode", "site123.me": "SITE123", "godaddysites.com": "GoDaddy",
    "mystrikingly.com": "Strikingly", "weebly.com": "Weebly", "wordpress.com": "WordPress.com",
    "blogspot.com": "Blogger", "carrd.co": "Carrd", "squarespace.com": "Squarespace", "webflow.io": "Webflow",
    "framer.website": "Framer", "framer.ai": "Framer", "sites.google.com": "Google Sites", "ueniweb.com": "UENI",
    "zyrosite.com": "Hostinger", "hostingersite.com": "Hostinger", "myshopify.com": "Shopify",
    "netlify.app": "Netlify", "vercel.app": "Vercel", "github.io": "GitHub Pages", "simplesite.com": "SimpleSite",
    "jouwweb.de": "JouwWeb", "beepworld.de": "Beepworld", "npage.de": "npage", "hpage.com": "hPage",
}
TWO_LEVEL_SUFFIXES = {"co.uk", "org.uk", "com.au", "co.at", "or.at", "ac.at", "gv.at", "com.tr", "co.nz", "com.br"}
PLATFORM_LABELS = {
    "instagram": "Instagram", "tiktok": "TikTok", "facebook": "Facebook", "youtube": "YouTube",
    "linkedin": "LinkedIn", "xing": "XING", "x": "X (Twitter)", "pinterest": "Pinterest",
    "whatsapp": "WhatsApp", "threads": "Threads",
}

PLACEHOLDER_HANDLES = {
    "wix", "wixcom", "jimdo", "squarespace", "wordpress", "wordpressdotcom", "elementor", "envato", "themeforest",
    "username", "yourusername", "your-username", "your_username", "yourname", "yourpage", "yourprofile", "user",
    "example", "instagram", "facebook", "tiktok", "meta", "shopify", "webflow", "godaddy", "ionos", "strato",
    "hostinger", "zyro", "weebly", "canva", "google", "youtube", "twitter", "pinterest", "linkedin", "share",
    "home", "profile", "page", "deinprofil", "ihrprofil", "accountname", "your_account", "account", "handle",
    "deinname", "ihrname", "name", "test", "demo", "company", "firma", "musterfirma", "mustermann",
}
IG_RESERVED = {
    "p", "reel", "reels", "tv", "stories", "explore", "accounts", "about", "developer", "developers", "legal",
    "direct", "directory", "web", "emails", "challenge", "privacy", "terms", "session", "oauth", "graphql", "api",
    "static", "s", "ar", "embed", "embed.js", "_u", "_n", "invites", "lite", "download", "press", "topics",
    "locations", "sharer", "share", "intent", "home", "login", "signup", "help", "blog", "creators", "business",
}
FB_RESERVED = {
    "sharer", "sharer.php", "share", "share.php", "dialog", "plugins", "tr", "login", "login.php", "l.php",
    "privacy", "policies", "policy", "policy.php", "help", "legal", "hashtag", "watch", "home.php", "photo.php",
    "photo", "permalink.php", "story.php", "media", "business", "ads", "public", "search", "gaming", "marketplace",
    "settings", "careers", "terms", "cookies", "fundraisers", "about", "docs", "brand", "facebook", "meta",
    "recover", "r.php", "reg", "connect", "events", "reel", "reels", "stories", "notes", "messages", "friends",
    "bookmarks", "notifications", "pages_reaction_units", "ajax", "common", "rsrc.php",
}
X_RESERVED = {"share", "intent", "home", "hashtag", "i", "search", "login", "signup", "tos", "privacy", "explore",
              "settings", "messages", "notifications", "about", "help", "rules", "download", "compose"}
PIN_RESERVED = {"pin", "search", "ideas", "today", "_", "business", "pin-builder", "settings", "about", "help"}
# Erlaubte Subdomains für Profil-Links (help.instagram.com, developers.facebook.com … sind keine Profile)
PROFILE_SUBDOMAINS = {
    "instagram.com": {"", "m"}, "instagr.am": {""}, "tiktok.com": {"", "m", "vm", "vt"},
    "facebook.com": {"", "m", "web", "mbasic", "touch"}, "fb.com": {""}, "fb.me": {""},
    "youtube.com": {"", "m"}, "youtu.be": {""}, "linkedin.com": {""}, "xing.com": {""},
    "twitter.com": {"", "mobile"}, "x.com": {""}, "wa.me": {""}, "whatsapp.com": {"", "api", "chat", "web"},
    "threads.net": {""}, "threads.com": {""}, "pinterest.com": {""}, "pinterest.de": {""}, "pinterest.at": {""},
    "pinterest.ch": {""},
}
LOCALE_SUB_OK = {"facebook.com", "linkedin.com", "pinterest.com"}
LOCALE_SUB = re.compile(r"^[a-z]{2}(?:-[a-z]{2})?$")

IG_HANDLE = re.compile(r"^[A-Za-z0-9._]{1,30}$")
TT_HANDLE = re.compile(r"^[A-Za-z0-9._]{2,24}$")
GENERIC_HANDLE = re.compile(r"^[A-Za-z0-9._\-]{2,80}$")

URL_IN_HTML = re.compile(
    r"(?:https?:)?//(?:[a-z0-9-]+\.)*(?:instagram\.com|instagr\.am|tiktok\.com|facebook\.com|fb\.com|fb\.me|"
    r"youtube\.com|youtu\.be|linkedin\.com|xing\.com|pinterest\.(?:com|de|at|ch)|twitter\.com|x\.com|wa\.me|"
    r"whatsapp\.com|threads\.net)(?:/[^\s\"'<>()\\,]*)?",
    re.I,
)
URL_IN_TEXT = re.compile(r"(?<![\w./])(?:www\.)?(instagram\.com|tiktok\.com)/(@?[A-Za-z0-9._]{2,30})", re.I)
IG_MENTION = re.compile(r"instagram[^@\n]{0,40}?(?<![\w.])@([A-Za-z0-9._]{2,30})", re.I)
TT_MENTION = re.compile(r"tik\s?tok[^@\n]{0,40}?(?<![\w.])@([A-Za-z0-9._]{2,24})", re.I)


def host_matches(host: str, domain: str) -> bool:
    return host == domain or host.endswith("." + domain)


def registrable_domain(url_or_host: str) -> str:
    host = url_or_host
    if "/" in url_or_host or ":" in url_or_host:
        host = urllib.parse.urlparse(url_or_host if "//" in url_or_host else "https://" + url_or_host).hostname or ""
    host = host.lower().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    labels = host.split(".")
    if len(labels) >= 3 and ".".join(labels[-2:]) in TWO_LEVEL_SUFFIXES:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:]) if len(labels) >= 2 else host


def normalize_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    if url.startswith("//"):
        url = "https:" + url
    if not re.match(r"^[a-z][a-z0-9+.-]*://", url, re.I):
        url = "https://" + url
    return url


def platform_of(url: str):
    """Ordnet eine Website-Adresse ein: eigene Website, Social-Profil, Link-Seite, Portal, Google, Baukasten."""
    url = normalize_url(url)
    if not url:
        return None
    p = urllib.parse.urlparse(url)
    host = (p.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    for domain, platform in SOCIAL_HOSTS.items():
        if host_matches(host, domain):
            return {"kind": "social", "platform": platform, "label": PLATFORM_LABELS.get(platform, platform)}
    for domain, label in LINKHUB_HOSTS.items():
        if host_matches(host, domain):
            return {"kind": "linkhub", "label": label}
    if host_matches(host, "business.site"):
        return {"kind": "google_site", "label": "Google-Website (2024 eingestellt)"}
    if host in ("g.page", "maps.app.goo.gl", "goo.gl") or (host_matches(host, "google.com") and p.path.startswith("/maps")) \
            or host_matches(host, "maps.google.com") or host_matches(host, "maps.google.de"):
        return {"kind": "google", "label": "Google-Unternehmensprofil"}
    for domain, label in PORTAL_HOSTS.items():
        if host_matches(host, domain):
            return {"kind": "portal", "label": label}
    for domain, label in BUILDER_HOSTS.items():
        if host_matches(host, domain):
            return {"kind": "builder", "label": label}
    return None


def _first_segments(path: str) -> list:
    return [s for s in path.split("/") if s]


def classify_social(url: str):
    """Gibt (plattform, kennung, url) für einen Profil-Link zurück, sonst None.

    Teilen-Buttons, Beiträge ohne Profilbezug und Platzhalter aus Website-Vorlagen werden ignoriert.
    """
    if not url:
        return None
    url = url.strip().replace("\\/", "/")
    if url.startswith("//"):
        url = "https:" + url
    if not re.match(r"^https?://", url, re.I):
        if re.match(r"^(www\.)?[a-z0-9.-]+\.[a-z]{2,}/", url, re.I):
            url = "https://" + url
        else:
            return None
    try:
        p = urllib.parse.urlparse(url)
    except ValueError:
        return None
    host = (p.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    base = next((d for d in PROFILE_SUBDOMAINS if host_matches(host, d)), "")
    if not base:
        return None
    sub = host[: -len(base) - 1] if host != base else ""
    if sub not in PROFILE_SUBDOMAINS[base] and not (base in LOCALE_SUB_OK and LOCALE_SUB.match(sub)):
        return None
    segs = _first_segments(urllib.parse.unquote(p.path))
    first = segs[0] if segs else ""
    query = urllib.parse.parse_qs(p.query)

    if host_matches(host, "instagram.com") or host_matches(host, "instagr.am"):
        if not first or first.lower() in IG_RESERVED or not IG_HANDLE.match(first):
            return None
        if first.isdigit() or first.startswith(".") or first.endswith(".") or ".." in first:
            return None  # keine gültigen Instagram-Namen (z. B. help.instagram.com/155833707900388)
        handle = first.lower()
        if handle in PLACEHOLDER_HANDLES:
            return None
        return ("instagram", handle, f"https://www.instagram.com/{handle}/")

    if host_matches(host, "tiktok.com"):
        if host.startswith(("vm.", "vt.")) and first:
            return ("tiktok_short", first, f"https://{host}/{first}/")
        if first.startswith("@"):
            handle = first[1:].lower()
            if TT_HANDLE.match(handle) and handle not in PLACEHOLDER_HANDLES:
                return ("tiktok", handle, f"https://www.tiktok.com/@{handle}")
        return None

    if host_matches(host, "facebook.com") or host in ("fb.com", "fb.me"):
        if not first or first.lower() in FB_RESERVED or re.match(r"^v\d+(\.\d+)?$", first):
            return None
        if first == "profile.php":
            pid = (query.get("id") or [""])[0]
            return ("facebook", f"profile.php?id={pid}", f"https://www.facebook.com/profile.php?id={pid}") if pid.isdigit() else None
        if first == "pg" and len(segs) >= 2:
            return ("facebook", segs[1], f"https://www.facebook.com/{segs[1]}")
        if first in ("pages", "p", "groups", "people") and len(segs) >= 2:
            ident = "/".join(segs[:3] if first == "pages" else segs[:2])
            return ("facebook", ident, f"https://www.facebook.com/{ident}")
        if not GENERIC_HANDLE.match(first) or first.lower() in PLACEHOLDER_HANDLES:
            return None
        return ("facebook", first, f"https://www.facebook.com/{first}")

    if host_matches(host, "youtube.com") or host == "youtu.be":
        if host == "youtu.be":
            return ("youtube_video", first, url) if first else None
        if first.startswith("@") and len(first) > 2:
            return ("youtube", first, f"https://www.youtube.com/{first}")
        if first in ("channel", "c", "user") and len(segs) >= 2:
            return ("youtube", f"{first}/{segs[1]}", f"https://www.youtube.com/{first}/{segs[1]}")
        if first in ("watch", "embed", "shorts", "playlist", "live"):
            return ("youtube_video", first, url)
        return None

    if host_matches(host, "linkedin.com"):
        if first in ("company", "in", "school", "showcase") and len(segs) >= 2:
            ident = f"{first}/{segs[1]}"
            return ("linkedin", ident, f"https://www.linkedin.com/{ident}")
        return None

    if host_matches(host, "xing.com"):
        if first in ("pages", "companies", "profile", "company") and len(segs) >= 2:
            ident = f"{first}/{segs[1]}"
            return ("xing", ident, f"https://www.xing.com/{ident}")
        return None

    if host_matches(host, "twitter.com") or host == "x.com":
        if len(first) >= 3 and first.lower() not in X_RESERVED and GENERIC_HANDLE.match(first) \
                and first.lower() not in PLACEHOLDER_HANDLES and not first.endswith(".php"):
            return ("x", first.lower(), f"https://x.com/{first}")
        return None

    if host.startswith("pinterest.") or host_matches(host, "pinterest.com") or host_matches(host, "pinterest.de"):
        if len(first) >= 3 and first.lower() not in PIN_RESERVED and GENERIC_HANDLE.match(first) \
                and first.lower() not in PLACEHOLDER_HANDLES:
            return ("pinterest", first.lower(), f"https://www.pinterest.de/{first}/")
        return None

    if host == "wa.me":
        return ("whatsapp", first or "link", url)
    if host_matches(host, "whatsapp.com"):
        if host.startswith(("api.", "web.")) and (query.get("phone") or first == "send"):
            return ("whatsapp", (query.get("phone") or ["link"])[0], url)
        if host.startswith("chat."):
            return ("whatsapp", "gruppe", url)
        if first == "channel":
            return ("whatsapp", "kanal", url)
        return None

    if host_matches(host, "threads.net") or host_matches(host, "threads.com"):
        if first.startswith("@") and len(first) > 2:
            return ("threads", first[1:].lower(), f"https://www.threads.net/{first}")
    return None


def extract_socials(hrefs, raw_html: str = "", visible_text: str = "") -> dict:
    """Sammelt Profil-Links. Ergebnis: {plattform: [{ident, url, via}]} in Fundreihenfolge."""
    found: dict = {}

    def add(item, via):
        if not item:
            return
        platform, ident, url = item
        bucket = found.setdefault(platform, {})
        if ident not in bucket:
            bucket[ident] = {"ident": ident, "url": url, "via": via}

    for href in hrefs:
        add(classify_social(href), "link")
    if raw_html:
        for m in URL_IN_HTML.finditer(raw_html.replace("\\/", "/")):
            add(classify_social(m.group(0)), "quelltext")
    if visible_text:
        for m in URL_IN_TEXT.finditer(visible_text):
            add(classify_social(f"https://{m.group(1)}/{m.group(2)}"), "text")
        for m in IG_MENTION.finditer(visible_text):
            add(classify_social(f"https://www.instagram.com/{m.group(1).rstrip('.')}/"), "text")
        for m in TT_MENTION.finditer(visible_text):
            add(classify_social(f"https://www.tiktok.com/@{m.group(1).rstrip('.')}"), "text")
    return {platform: list(items.values()) for platform, items in found.items()}


def merge_socials(target: dict, extra: dict, via: str = "") -> None:
    for platform, items in (extra or {}).items():
        bucket = target.setdefault(platform, [])
        known = {i["ident"] for i in bucket}
        for item in items:
            if item["ident"] not in known:
                entry = dict(item)
                if via:
                    entry["via"] = via
                bucket.append(entry)
                known.add(item["ident"])


def _simple(text: str) -> str:
    t = (text or "").lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        t = t.replace(a, b)
    return re.sub(r"[^a-z0-9]", "", t)


GENERIC_NAME_WORDS = {"gmbh", "ug", "kg", "ohg", "gbr", "mbh", "und", "the", "salon", "studio", "praxis", "fuer",
                      "friseur", "inh", "inhaber", "haus", "team", "restaurant", "cafe", "dr", "med"}


def pick_best(items: list, name: str = "", domain: str = "") -> dict | None:
    """Wählt das wahrscheinlichste eigene Profil (Ähnlichkeit zu Firmenname/Domain, dann Fundort)."""
    if not items:
        return None
    label = _simple(domain.split(".")[0]) if domain else ""
    words = [_simple(w) for w in re.split(r"[\s\-&+.,/]+", name or "")]
    words = [w for w in words if len(w) >= 4 and w not in GENERIC_NAME_WORDS]
    via_rank = {"google": 4, "osm": 4, "link": 3, "linkhub": 3, "quelltext": 2, "text": 1}

    def score(item):
        h = _simple(item["ident"])
        s = 0
        if label and len(label) >= 3 and (label in h or h in label):
            s += 4
        s += sum(1 for w in words if w in h)
        return (s, via_rank.get(item.get("via", ""), 0))

    return max(items, key=score)


def handle_from_hint(platform: str, value: str):
    """OSM-/Google-Angaben wie „@salon_xy“ oder volle URLs in einen Profil-Link umwandeln."""
    value = (value or "").strip()
    if not value:
        return None
    if "/" in value:
        return classify_social(normalize_url(value))
    value = value.lstrip("@")
    if platform == "instagram":
        return classify_social(f"https://www.instagram.com/{value}/")
    if platform == "tiktok":
        return classify_social(f"https://www.tiktok.com/@{value}")
    if platform == "facebook":
        return classify_social(f"https://www.facebook.com/{value}")
    if platform == "youtube":
        return classify_social(f"https://www.youtube.com/@{value}")
    return None


def resolve_short_link(url: str, user_agent: str) -> str:
    """Folgt einem Kurzlink (z. B. vm.tiktok.com) und gibt die Zieladresse zurück."""
    net.THROTTLE.wait("tiktok", 2.0)
    r = net.fetch(url, user_agent=user_agent, timeout=15, max_bytes=60_000)
    return r.final_url if r.status and r.status < 400 else ""


def scan_linkhub(url: str, user_agent: str) -> dict:
    """Liest eine Link-Seite (z. B. Linktree): Profile und ggf. eine eigene Website."""
    net.THROTTLE.wait(net.host_of(url), 1.0)
    r = net.fetch(url, user_agent=user_agent, timeout=15, max_bytes=1_500_000)
    out = {"ok": r.ok, "socials": {}, "website": ""}
    if not r.ok:
        return out
    html = r.text()
    hrefs = re.findall(r"href=[\"']([^\"']+)[\"']", html, re.I)
    out["socials"] = extract_socials(hrefs, html)
    hub_domain = registrable_domain(url)
    for href in hrefs:
        if not href.startswith("http"):
            continue
        dom = registrable_domain(href)
        if dom == hub_domain or classify_social(href) or platform_of(href):
            continue
        if any(x in href for x in ("linktr.ee", "privacy", "cookie", "terms", "report", "apple.com", "google.com")):
            continue
        out["website"] = href
        break
    return out


def search_links(name: str, ort: str) -> dict:
    """Links für die manuelle Prüfung (Google-Suche nach Profilen)."""
    base = "https://www.google.com/search?q="
    q_name = f"\"{name}\" {ort}".strip()
    return {
        "website": base + urllib.parse.quote_plus(q_name),
        "instagram": base + urllib.parse.quote_plus(f"site:instagram.com {q_name}"),
        "tiktok": base + urllib.parse.quote_plus(f"site:tiktok.com {q_name}"),
        "facebook": base + urllib.parse.quote_plus(f"site:facebook.com {q_name}"),
    }


# ---------------------------------------------------------------------------
# Hilfen für Zeitangaben
# ---------------------------------------------------------------------------

def _now_ts(now=None) -> float:
    return now if now is not None else time.time()


def _iso_date(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


def video_id_timestamp(video_id: str, now=None):
    """TikTok-Video-IDs enthalten in den oberen 32 Bit den Unix-Zeitstempel der Veröffentlichung."""
    try:
        ts = int(video_id) >> 32
    except (TypeError, ValueError):
        return None
    if 1472688000 <= ts <= _now_ts(now) + 86400:  # zwischen 09/2016 und morgen
        return ts
    return None


# ---------------------------------------------------------------------------
# TikTok
# ---------------------------------------------------------------------------

def parse_tiktok_embed(html: str, now=None):
    """Kennzahlen aus dem öffentlichen Creator-Embed (https://www.tiktok.com/embed/@name)."""
    m = re.search(r'<script[^>]+id="__FRONTITY_CONNECT_STATE__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        return None
    try:
        state = json.loads(m.group(1))
    except ValueError:
        return None
    data = ((state.get("source") or {}).get("data") or {})
    entry = None
    for key, value in data.items():
        if key.startswith("/embed/@") and isinstance(value, dict):
            entry = value
            break
    if not entry:
        return None
    if entry.get("isError") or not entry.get("userInfo"):
        return {"exists": False}
    user = entry["userInfo"]
    videos = []
    for v in entry.get("videoList") or []:
        ts = video_id_timestamp(str(v.get("id", "")), now)
        videos.append({"ts": ts, "plays": int(v.get("playCount") or 0)})
    dates = sorted((v["ts"] for v in videos if v["ts"]), reverse=True)
    now_ts = _now_ts(now)
    plays = [v["plays"] for v in videos]
    return {
        "exists": True,
        "followers": int(user.get("followerCount") or 0),
        "likes": int(user.get("heartCount") or 0),
        "following": int(user.get("followingCount") or 0),
        "private": bool(user.get("privateAccount")),
        "verified": bool(user.get("verified")),
        "nickname": user.get("nickname", ""),
        "bio": user.get("signature", ""),
        "videos_visible": len(videos),
        "last_video_days": int((now_ts - dates[0]) // 86400) if dates else None,
        "last_video_date": _iso_date(dates[0]) if dates else "",
        "videos_30d": sum(1 for t in dates if now_ts - t <= 30 * 86400),
        "videos_90d": sum(1 for t in dates if now_ts - t <= 90 * 86400),
        "avg_views": int(statistics.mean(plays)) if plays else None,
        "median_views": int(statistics.median(plays)) if plays else None,
    }


class TikTokClient:
    """Höflicher TikTok-Abruf: ehrlicher User-Agent, mindestens 2 s Abstand, Abbruch bei Sperre."""

    def __init__(self, user_agent: str, notes: list, metrics: bool = True):
        self.ua = user_agent
        self.notes = notes
        self.metrics = metrics
        self.blocked = False

    def _get(self, url: str, accept: str) -> net.Response:
        r = net.Response(url=url)
        for attempt in range(2):
            net.THROTTLE.wait("tiktok", 2.0)
            r = net.fetch(url, user_agent=self.ua, accept=accept, timeout=20, max_bytes=2_500_000)
            if r.status != 429:
                return r
            if attempt == 0:
                time.sleep(20)
        self.blocked = True
        self.notes.append("TikTok hat weitere Abrufe vorübergehend begrenzt – restliche Profile nicht geprüft.")
        return r

    def check(self, handle: str) -> dict:
        url = f"https://www.tiktok.com/@{handle}"
        res = {"handle": handle, "url": url, "status": "unbekannt", "exists": None, "name": "", "metrics": None, "error": ""}
        if self.blocked:
            res["status"], res["error"] = "nicht_geprueft", "TikTok-Abruflimit erreicht"
            return res
        r = self._get("https://www.tiktok.com/oembed?url=" + urllib.parse.quote(url, safe=""), net.ACCEPT_JSON)
        if r.status == 200:
            data = r.json() or {}
            res.update(exists=True, status="ok", name=data.get("author_name", ""))
        elif r.status in (400, 404):
            res.update(exists=False, status="nicht_gefunden")
            return res
        else:
            res.update(status="fehler", error=r.describe_error() or f"HTTP {r.status}")
            return res
        if self.metrics and not self.blocked:
            r = self._get(f"https://www.tiktok.com/embed/@{urllib.parse.quote(handle)}", net.ACCEPT_HTML)
            if r.ok:
                parsed = parse_tiktok_embed(r.text())
                if parsed and parsed.get("exists"):
                    parsed.pop("exists", None)
                    res["metrics"] = parsed
        return res


# ---------------------------------------------------------------------------
# Instagram über Meta Graph API (Business Discovery)
# ---------------------------------------------------------------------------

def _parse_ig_ts(value: str):
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S%z").timestamp()
    except (TypeError, ValueError):
        return None


def parse_ig_business(bd: dict, now=None) -> dict:
    media = ((bd.get("media") or {}).get("data")) or []
    items = []
    for m in media:
        ts = _parse_ig_ts(m.get("timestamp", ""))
        items.append({
            "ts": ts,
            "video": m.get("media_product_type") == "REELS" or m.get("media_type") == "VIDEO",
            "likes": m.get("like_count"),
            "comments": m.get("comments_count"),
        })
    items.sort(key=lambda x: x["ts"] or 0, reverse=True)
    now_ts = _now_ts(now)
    dates = [i["ts"] for i in items if i["ts"]]
    recent = items[:12]
    followers = int(bd.get("followers_count") or 0)
    interactions = [(i["likes"] or 0) + (i["comments"] or 0) for i in recent
                    if i["likes"] is not None or i["comments"] is not None]
    engagement = None
    if followers and interactions:
        engagement = round(statistics.mean(interactions) / followers * 100, 2)
    return {
        "followers": followers,
        "following": int(bd.get("follows_count") or 0),
        "posts": int(bd.get("media_count") or 0),
        "name": bd.get("name", ""),
        "bio": bd.get("biography", ""),
        "website": bd.get("website", ""),
        "last_post_days": int((now_ts - dates[0]) // 86400) if dates else None,
        "last_post_date": _iso_date(dates[0]) if dates else "",
        "posts_30d": sum(1 for t in dates if now_ts - t <= 30 * 86400),
        "posts_90d": sum(1 for t in dates if now_ts - t <= 90 * 86400),
        "reels_share": round(sum(1 for i in recent if i["video"]) / len(recent), 2) if recent else None,
        "videos_recent": sum(1 for i in recent if i["video"]),
        "sample": len(recent),
        "engagement": engagement,
    }


class MetaClient:
    """Instagram-Kennzahlen anderer Business-/Creator-Konten über die eigene Meta-App."""

    FIELDS = ("business_discovery.username({u}){{username,name,biography,website,followers_count,follows_count,"
              "media_count,media.limit(25){{timestamp,media_type,media_product_type,like_count,comments_count}}}}")

    def __init__(self, token: str, ig_user_id: str, version: str, user_agent: str, notes: list):
        self.token = token
        self.ig_id = ig_user_id
        self.version = version or "v23.0"
        self.ua = user_agent
        self.notes = notes
        self.disabled = ""

    def _get(self, path: str, params: dict):
        net.THROTTLE.wait("graph.facebook.com", 0.5)
        query = urllib.parse.urlencode({**params, "access_token": self.token})
        r = net.fetch(f"https://graph.facebook.com/{self.version}/{path}?{query}", accept=net.ACCEPT_JSON,
                      timeout=30, user_agent=self.ua)
        data = r.json()
        if r.ok and isinstance(data, dict):
            return data, None
        err = (data or {}).get("error", {}) if isinstance(data, dict) else {}
        return None, {
            "code": err.get("code"),
            "subcode": err.get("error_subcode"),
            "message": err.get("error_user_msg") or err.get("message") or r.describe_error() or f"HTTP {r.status}",
        }

    def _disable(self, reason: str) -> None:
        if not self.disabled:
            self.disabled = reason
            self.notes.append(f"Instagram-Kennzahlen abgebrochen: {reason}")

    def lookup(self, username: str) -> dict:
        if self.disabled:
            return {"status": "nicht_geprueft", "error": self.disabled}
        data, err = self._get(self.ig_id, {"fields": self.FIELDS.format(u=username)})
        if err:
            code = err.get("code")
            if code in (190, 102):
                self._disable("Meta-Zugangstoken ungültig oder abgelaufen (META_ACCESS_TOKEN erneuern)")
            elif code in (4, 17, 32, 613, 80002):
                self._disable("Meta-API-Limit erreicht – in etwa einer Stunde erneut versuchen")
            elif code in (10, 200, 3):
                self._disable("Dem Meta-Token fehlen Berechtigungen (instagram_basic, pages_show_list, "
                              "pages_read_engagement)")
            elif code in (110, 100):
                return {"status": "kein_business", "error": "Kein Business-/Creator-Konto oder Name existiert nicht"}
            return {"status": "fehler", "error": err.get("message", "")}
        bd = (data or {}).get("business_discovery")
        if not bd:
            return {"status": "kein_business", "error": "Keine Daten"}
        return {"status": "ok", "metrics": parse_ig_business(bd)}

    def check(self) -> dict:
        """Verbindungstest; findet bei Bedarf die eigene Instagram-Konto-ID."""
        me, err = self._get("me", {"fields": "id,name"})
        if err:
            return {"ok": False, "message": f"Token ungültig: {err['message']}"}
        accounts, _ = self._get("me/accounts", {"fields": "name,instagram_business_account{id,username}", "limit": 50})
        found = []
        for page in (accounts or {}).get("data", []):
            ig = page.get("instagram_business_account")
            if ig:
                found.append({"seite": page.get("name", ""), "id": ig.get("id", ""), "username": ig.get("username", "")})
        if not self.ig_id:
            if found:
                hint = ", ".join(f"@{f['username']} → {f['id']}" for f in found)
                return {"ok": False, "accounts": found,
                        "message": f"Token gültig. Trage die ID deines Instagram-Kontos als META_IG_USER_ID ein: {hint}"}
            return {"ok": False, "accounts": [],
                    "message": "Token gültig, aber kein Instagram-Business-Konto mit einer Facebook-Seite verknüpft."}
        info, err = self._get(self.ig_id, {"fields": "username,followers_count"})
        if err:
            return {"ok": False, "accounts": found, "message": f"META_IG_USER_ID passt nicht: {err['message']}"}
        test = self.lookup(info.get("username", "instagram"))
        if test.get("status") == "ok":
            return {"ok": True, "accounts": found,
                    "message": f"Instagram-Kennzahlen aktiv (eigenes Konto @{info.get('username', '')})."}
        return {"ok": False, "accounts": found, "message": f"Business Discovery funktioniert nicht: {test.get('error', '')}"}


def instagram_candidates(domain: str) -> list:
    """Mögliche Instagram-Namen aus der Domain (max. 2), z. B. friseur-sivo.de → friseursivo, friseur_sivo."""
    label = domain.split(".")[0].lower() if domain else ""
    if len(label) < 3:
        return []
    out = [label.replace("-", ""), label.replace("-", "_")]
    return [c for i, c in enumerate(out) if c not in out[:i] and IG_HANDLE.match(c)][:2]
