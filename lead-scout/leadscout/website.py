"""Website-Analyse: sammelt Fakten zur Startseite (plus Impressum/Kontakt), bewertet wird in scoring.py.

Geprüft werden u. a. Erreichbarkeit, HTTPS, Mobiltauglichkeit, Ladezeit (Server), SEO-Grundlagen,
Impressum/Datenschutz, Cookie-Banner, Tracking, Google Fonts, CMS/Baukasten, Aktualität,
Kontaktwege, Online-Buchung, Videos und Social-Media-Verlinkung.
"""
from __future__ import annotations

import json
import re
import urllib.parse
from datetime import datetime
from html.parser import HTMLParser

from . import net, social

SKIP_TEXT_TAGS = {"script", "style", "noscript", "template", "svg", "iframe", "object"}
DEPRECATED_TAGS = {"font", "center", "marquee", "blink", "frameset", "frame", "applet", "basefont"}
STRONG_DEPRECATED = {"marquee", "blink", "frameset", "frame", "applet"}

CMS_SIGNATURES = [
    # (Name, Art, Muster im HTML (klein geschrieben))
    ("WordPress", "cms", ["/wp-content/", "/wp-includes/"]),
    ("Wix", "baukasten", ["static.wixstatic.com", "wix-bolt", "wixsite.com", "_wixcss"]),
    ("Jimdo", "baukasten", ["jimcdn.com", "jimdosite", "jimdo-"]),
    ("IONOS/Strato-Baukasten", "baukasten", ["cm4all", "mywebsite-now", "mywebsite-editor"]),
    ("Squarespace", "baukasten", ["static1.squarespace.com", "squarespace-cdn", "sqs-block"]),
    ("Webflow", "baukasten", ["data-wf-site", "website-files.com"]),
    ("Shopify", "shop", ["cdn.shopify.com", "shopify.theme"]),
    ("TYPO3", "cms", ["typo3conf", "typo3temp"]),
    ("Joomla", "cms", ["/media/jui/", "/components/com_"]),
    ("Drupal", "cms", ["drupal-settings-json", "/sites/default/files"]),
    ("Contao", "cms", ["/assets/contao/", "/system/modules/"]),
    ("Duda", "baukasten", ["dudaone", "multiscreensite", "irp.cdn-website.com"]),
    ("GoDaddy-Baukasten", "baukasten", ["img1.wsimg.com"]),
    ("Weebly", "baukasten", ["editmysite.com", "weebly-"]),
    ("Webnode", "baukasten", ["webnode."]),
    ("Hostinger-Baukasten", "baukasten", ["zyrosite.com", "userapp.zyrosite"]),
    ("Framer", "baukasten", ["framerusercontent.com", "data-framer-"]),
    ("Google Sites", "baukasten", ["gstatic.com/atari", "sites.google.com/"]),
    ("Shopware", "shop", ["/bundles/storefront/", "shopware"]),
    ("Next.js", "framework", ["/_next/static"]),
    ("Nuxt", "framework", ["/_nuxt/"]),
    ("Gatsby", "framework", ["___gatsby"]),
    ("Astro", "framework", ["astro-island", "/_astro/"]),
]
GENERATOR_NAMES = [
    ("wordpress", "WordPress", "cms"), ("typo3", "TYPO3", "cms"), ("joomla", "Joomla", "cms"),
    ("drupal", "Drupal", "cms"), ("contao", "Contao", "cms"), ("wix", "Wix", "baukasten"),
    ("jimdo", "Jimdo", "baukasten"), ("squarespace", "Squarespace", "baukasten"), ("webflow", "Webflow", "baukasten"),
    ("hubspot", "HubSpot", "cms"), ("shopify", "Shopify", "shop"), ("go daddy", "GoDaddy-Baukasten", "baukasten"),
    ("weebly", "Weebly", "baukasten"), ("webnode", "Webnode", "baukasten"), ("site123", "SITE123", "baukasten"),
    ("framer", "Framer", "baukasten"), ("astro", "Astro", "framework"), ("gatsby", "Gatsby", "framework"),
    ("next.js", "Next.js", "framework"), ("cm4all", "IONOS/Strato-Baukasten", "baukasten"),
]
PAGE_BUILDERS = [
    ("Elementor", ["elementor"]), ("Divi", ["et_pb_", "/divi/"]), ("WPBakery", ["vc_row", "wpbakery"]),
    ("Beaver Builder", ["fl-builder"]), ("Avada", ["fusion-builder", "avada"]), ("Enfold", ["avia-builder", "/enfold/"]),
    ("Bricks", ["brxe-"]), ("Oxygen", ["oxygen-"]), ("Brizy", ["brz-"]),
]
CONSENT_SIGNATURES = [
    ("Cookiebot", ["cookiebot"]), ("Usercentrics", ["usercentrics"]), ("Borlabs Cookie", ["borlabs"]),
    ("Complianz", ["complianz", "cmplz"]), ("CookieYes", ["cookieyes", "cookie-law-info"]),
    ("OneTrust", ["cdn.cookielaw.org", "onetrust", "optanon"]), ("Klaro", ["klaro.js", "klaro.min.js", "klaroconfig"]),
    ("consentmanager", ["consentmanager.net", "consentmanager.de"]), ("Real Cookie Banner", ["real-cookie-banner"]),
    ("CCM19", ["ccm19"]), ("Cookie Notice", ["cookie-notice", "cn-notice"]), ("GDPR Cookie Compliance", ["moove_gdpr"]),
    ("iubenda", ["iubenda"]), ("Termly", ["termly.io"]), ("Didomi", ["didomi"]), ("Sourcepoint", ["sourcepoint"]),
    ("TrustArc", ["trustarc"]), ("Osano", ["osano.com"]), ("CookieFirst", ["cookiefirst"]),
    ("Cookie-Script", ["cookie-script.com"]), ("CookieConsent", ["cookieconsent.min.js", "cookieconsent.js", "cc_cookie"]),
    ("Shopify-Consent", ["customerprivacy"]), ("Wix-Consent", ["consentpolicy", "consent-policy"]),
]
CONSENT_TEXT = ["cookie-einstellungen", "cookies akzeptieren", "alle akzeptieren", "cookie-banner", "cookiebanner",
                "cookie-hinweis", "cookie consent", "datenschutzeinstellungen", "privatsphäre-einstellungen",
                "accept all cookies", "cookie settings", "wir verwenden cookies", "diese website verwendet cookies"]
TRACKING_SIGNATURES = [
    ("Google Analytics", ["google-analytics.com/analytics.js", "google-analytics.com/ga.js", "gtag/js?id=g-",
                          "gtag/js?id=ua-"]),
    ("Google Tag Manager", ["googletagmanager.com/gtm.js", "googletagmanager.com/ns.html"]),
    ("Meta-Pixel", ["fbevents.js", "fbq('init'", 'fbq("init"']),
    ("Google Ads", ["googleadservices.com", "gtag/js?id=aw-", "google_conversion_id"]),
    ("TikTok-Pixel", ["analytics.tiktok.com"]),
    ("LinkedIn Insight", ["snap.licdn.com"]),
    ("Pinterest-Tag", ["s.pinimg.com/ct/core.js"]),
    ("Hotjar", ["static.hotjar.com"]),
    ("Microsoft Clarity", ["clarity.ms/tag"]),
    ("Matomo", ["matomo.js", "piwik.js"]),
]
ADS_TOOLS = {"Meta-Pixel", "Google Ads", "TikTok-Pixel", "LinkedIn Insight", "Pinterest-Tag"}
BOOKING_SIGNATURES = [
    ("Doctolib", ["doctolib"]), ("Jameda", ["jameda"]), ("Dr. Flex", ["dr-flex"]), ("samedi", ["samedi.de"]),
    ("Treatwell", ["treatwell"]), ("Shore", ["connect.shore.com", "shore.com/"]), ("Salonized", ["salonized"]),
    ("Planity", ["planity"]), ("Booksy", ["booksy"]), ("Fresha", ["fresha.com"]), ("Calendly", ["calendly.com"]),
    ("Timify", ["timify"]), ("eTermin", ["etermin.net"]), ("Terminland", ["terminland"]), ("SimplyBook", ["simplybook"]),
    ("Acuity", ["acuityscheduling"]), ("OpenTable", ["opentable"]), ("Quandoo", ["quandoo"]), ("resmio", ["resmio"]),
    ("TheFork", ["thefork", "lafourchette"]), ("DISH", ["reservation.dish.co"]), ("Gastronovi", ["gastronovi"]),
    ("aleno", ["aleno.me"]), ("Eversports", ["eversports"]), ("Magicline", ["magicline"]),
    ("bookingkit", ["bookingkit"]), ("Regiondo", ["regiondo"]),
]
BOOKING_TEXT = ["online-termin", "online termin", "termin online", "online buchen", "jetzt buchen", "termin buchen",
                "termin vereinbaren online", "tisch reservieren", "online reservieren", "jetzt reservieren"]
FORM_SERVICES = ["wpcf7", "wpforms", "gform_", "gravityforms", "ninja-forms", "formidable", "formspree", "jotform",
                 "typeform", "123formbuilder", "hsforms", "hs-form", "elementor-form", "wixforms", "form-builder"]
VIDEO_SIGNATURES = ["youtube.com/embed", "youtube-nocookie.com", "player.vimeo.com", "tiktok.com/embed",
                    "wistia", "vidyard", "jwplayer", "videopress", ".mp4", "youtube.com/watch", "youtu.be/"]
IG_FEED_SIGNATURES = ["elfsight", "behold.so", "juicer.io", "sb_instagram", "sbi_", "curator.io", "taggbox",
                      "walls.io", "snapwidget", "lightwidget", "flockler", "spotlight-instagram", "instagram-feed",
                      "instafeed", "embedsocial", "tagembed", "instagram.com/embed.js"]
PARKING_HOSTS = ["sedoparking.com", "parkingcrew.net", "bodis.com", "dan.com", "afternic.com", "hugedomains.com",
                 "undeveloped.com", "above.com", "domainmarket.com", "sav.com", "parklogic.com", "sedo.com"]
PARKED_TEXT = ["domain ist zu verkaufen", "diese domain kaufen", "domain kaufen", "this domain is for sale",
               "buy this domain", "domain may be for sale", "domain steht zum verkauf", "domain is parked",
               "diese domain wurde soeben registriert", "diese domain ist bereits registriert", "default web site page",
               "welcome to nginx", "apache2 ubuntu default page", "it works!", "domain wurde erfolgreich",
               "hier entsteht eine neue", "hier entsteht in kürze", "website im aufbau", "seite im aufbau",
               "homepage im aufbau", "under construction", "coming soon", "wartungsmodus", "maintenance mode",
               "wir sind bald für sie da", "in kürze finden sie hier"]
CHALLENGE_TEXT = ["just a moment", "challenge-platform", "attention required", "cf-browser-verification",
                  "ddos protection", "sucuri website firewall", "access denied", "bot protection", "captcha"]
BAD_EMAIL_PARTS = ("example.", "beispiel.", "domain.", "email.", "sentry", "wixpress", "@2x", ".png", ".jpg",
                   ".jpeg", ".gif", ".svg", ".webp", "u00", "yourdomain", "ihredomain", "musterfirma", "mustermann")

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,24}")
EMAIL_OBFUSCATED_RE = re.compile(
    r"([A-Za-z0-9._%+\-]+)\s*[\[(\{]\s*(?:at|ät|@)\s*[\])\}]\s*([A-Za-z0-9.\-]+?)\s*"
    r"(?:[\[(\{]\s*(?:dot|punkt|\.)\s*[\])\}]|\.)\s*([A-Za-z]{2,24})\b", re.I)
COPYRIGHT_RE = re.compile(r"(?:©|\(c\)|copyright)\s*(?:by\s*)?(?:(?:19|20)\d{2}\s*(?:[-–—/]|bis)\s*)?((?:19|20)\d{2})",
                          re.I)
JQUERY_RE = re.compile(r"jquery[-.]?(\d+\.\d+(?:\.\d+)?)(?:\.min|\.slim)*\.js|jquery(?:\.min)?\.js\?ver=(\d+\.\d+(?:\.\d+)?)",
                       re.I)
GTAG_CONFIG_RE = re.compile(r"gtag\(\s*['\"]config['\"]\s*,\s*['\"](g|ua|aw)-", re.I)


class PageParser(HTMLParser):
    """Robuster, toleranter HTML-Parser (Standardbibliothek)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lang = ""
        self.title_parts: list = []
        self.meta: dict = {}
        self.generators: list = []
        self.link_rels: list = []
        self.script_srcs: list = []
        self.inline_scripts: list = []
        self.jsonld: list = []
        self.anchors: list = []
        self.iframes: list = []
        self.h1: list = []
        self.img_total = 0
        self.img_no_alt = 0
        self.video_tags = 0
        self.forms: list = []
        self.deprecated: dict = {}
        self.flash = False
        self.text_parts: list = []
        self._text_len = 0
        self._skip = 0
        self._in_title = False
        self._anchor = None
        self._h1 = None
        self._script = None
        self._form = None

    def _close_anchor(self):
        if self._anchor is not None:
            href, texts = self._anchor
            self.anchors.append((href.strip(), " ".join(" ".join(texts).split())))
            self._anchor = None

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs if k}
        if tag == "html" and a.get("lang"):
            self.lang = a["lang"].strip()
        elif tag == "title":
            self._in_title = True
        elif tag == "meta":
            key = (a.get("name") or a.get("property") or a.get("http-equiv") or "").lower().strip()
            if key == "generator":
                self.generators.append(a.get("content", ""))
            elif key:
                self.meta.setdefault(key, a.get("content", ""))
        elif tag == "link":
            if a.get("rel"):
                self.link_rels.append((a["rel"].lower(), a.get("href", "")))
        elif tag == "script":
            self._script = {"type": a.get("type", "").lower(), "src": a.get("src", ""), "buf": []}
            if a.get("src"):
                self.script_srcs.append(a["src"])
        elif tag == "a":
            self._close_anchor()
            self._anchor = [a.get("href", ""), []]
        elif tag == "h1":
            self._h1 = []
        elif tag == "img":
            self.img_total += 1
            if "alt" not in a:
                self.img_no_alt += 1
        elif tag == "iframe":
            self.iframes.append(a.get("src", "") or a.get("data-src", ""))
        elif tag == "video":
            self.video_tags += 1
        elif tag == "form":
            self._form = {"inputs": [], "textarea": False}
            self.forms.append(self._form)
        elif tag == "input" and self._form is not None:
            self._form["inputs"].append(a.get("type", "text").lower())
        elif tag == "textarea" and self._form is not None:
            self._form["textarea"] = True
        elif tag in ("object", "embed"):
            blob = (a.get("data", "") + a.get("src", "") + a.get("type", "")).lower()
            if ".swf" in blob or "shockwave" in blob:
                self.flash = True
        if tag in DEPRECATED_TAGS:
            self.deprecated[tag] = self.deprecated.get(tag, 0) + 1
        if tag in SKIP_TEXT_TAGS:
            self._skip += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "a":
            self._close_anchor()
        elif tag == "h1" and self._h1 is not None:
            self.h1.append(" ".join(" ".join(self._h1).split()))
            self._h1 = None
        elif tag == "script" and self._script is not None:
            text = "".join(self._script["buf"])
            if "ld+json" in self._script["type"]:
                self.jsonld.append(text)
            elif not self._script["src"] and sum(len(s) for s in self.inline_scripts) < 600_000:
                self.inline_scripts.append(text)
            self._script = None
        elif tag == "form":
            self._form = None
        if tag in SKIP_TEXT_TAGS and self._skip > 0:
            self._skip -= 1

    def handle_data(self, data):
        if self._script is not None:
            self._script["buf"].append(data)
            return
        if self._in_title:
            self.title_parts.append(data)
            return
        if self._skip:
            return
        if self._anchor is not None:
            self._anchor[1].append(data)
        if self._h1 is not None:
            self._h1.append(data)
        if self._text_len < 400_000:
            self.text_parts.append(data)
            self._text_len += len(data)

    @property
    def title(self) -> str:
        return " ".join("".join(self.title_parts).split())

    @property
    def visible_text(self) -> str:
        return " ".join(" ".join(self.text_parts).split())


def parse_html(html: str) -> PageParser:
    parser = PageParser()
    try:
        parser.feed(html)
        parser.close()
    except Exception:  # HTMLParser ist tolerant, aber sicher ist sicher
        pass
    parser._close_anchor()
    return parser


def _jsonld_types(blocks: list) -> list:
    types: list = []

    def walk(node):
        if isinstance(node, dict):
            t = node.get("@type")
            for item in (t if isinstance(t, list) else [t]):
                if isinstance(item, str) and item not in types:
                    types.append(item)
            for value in node.values():
                if isinstance(value, (dict, list)):
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    for block in blocks:
        try:
            walk(json.loads(block.strip()))
        except ValueError:
            continue
    return types


def _first_match(blob: str, signatures) -> str:
    for name, patterns in signatures:
        if any(p in blob for p in patterns):
            return name
    return ""


def _all_matches(blob: str, signatures) -> list:
    return [name for name, patterns in signatures if any(p in blob for p in patterns)]


def _clean_email(raw: str) -> str:
    email = urllib.parse.unquote(raw).split("?")[0].strip().strip(".,;:").lower()
    if not EMAIL_RE.fullmatch(email) or any(part in email for part in BAD_EMAIL_PARTS):
        return ""
    return email


def collect_emails(anchors: list, text: str) -> list:
    found: list = []
    for href, _ in anchors:
        if href.lower().startswith("mailto:"):
            email = _clean_email(href[7:])
            if email and email not in found:
                found.append(email)
    for m in EMAIL_RE.finditer(text):
        email = _clean_email(m.group(0))
        if email and email not in found:
            found.append(email)
    for m in EMAIL_OBFUSCATED_RE.finditer(text):
        email = _clean_email(f"{m.group(1)}@{m.group(2)}.{m.group(3)}")
        if email and email not in found:
            found.append(email)
    return found[:5]


def collect_phones(anchors: list) -> list:
    phones: list = []
    for href, _ in anchors:
        if href.lower().startswith("tel:"):
            number = urllib.parse.unquote(href[4:]).strip()
            if len(re.sub(r"\D", "", number)) >= 6 and number not in phones:
                phones.append(number)
    return phones[:3]


def _find_link(links: list, keywords) -> str:
    for url, text in links:
        low_url = url.lower()
        low_text = text.lower()
        if any(k in low_url or k in low_text for k in keywords):
            return url
    return ""


def detect_cms(blob: str, generators: list, headers: dict) -> tuple:
    gen = " ".join(generators).lower()
    for key, name, kind in GENERATOR_NAMES:
        if key in gen:
            return name, kind
    header_blob = " ".join(f"{k}: {v}" for k, v in headers.items()).lower()
    if "x-wix-request-id" in header_blob:
        return "Wix", "baukasten"
    if "x-shopify" in header_blob or "x-shopid" in header_blob:
        return "Shopify", "shop"
    for name, kind, patterns in CMS_SIGNATURES:
        if any(p in blob for p in patterns):
            return name, kind
    return "", ""


def _empty(url: str) -> dict:
    return {
        "input_url": url, "status": "fehler", "status_text": "", "final_url": "", "domain": "",
        "http_status": 0, "https": False, "ssl_error": False, "ttfb": None, "load_time": None, "html_kb": None,
        "redirects": 0, "title": "", "description": "", "viewport": False, "lang": "", "h1_count": 0, "h1": "",
        "og_image": False, "favicon": False, "canonical": False, "structured_data": [], "noindex": False,
        "robots_google_blocked": False, "cms": "", "cms_kind": "", "page_builder": "", "builder_subdomain": "",
        "shop": False, "copyright_year": None, "jquery_version": "", "deprecated": [], "impressum": False,
        "datenschutz": False, "consent_tool": "", "consent_hint": False, "tracking": [], "ads_tools": [],
        "google_fonts": False, "phones": [], "emails": [], "tel_link": False, "contact_form": False,
        "whatsapp": False, "booking_tool": "", "video": False, "instagram_feed": False, "word_count": 0,
        "img_total": 0, "img_no_alt": 0, "js_rendered": False, "socials": {}, "pages_checked": [],
        "platform": "", "pagespeed": None, "redirect_domain": "", "deep_link_404": False,
    }


def _get(url: str, user_agent: str, timeout: float = 15) -> net.Response:
    net.THROTTLE.wait(net.host_of(url), 0.6)
    return net.fetch(url, user_agent=user_agent, timeout=timeout)


def _toggle_www(url: str) -> str:
    p = urllib.parse.urlparse(url)
    host = p.netloc
    host = host[4:] if host.startswith("www.") else "www." + host
    return urllib.parse.urlunparse(p._replace(netloc=host))


def _fetch_homepage(url: str, user_agent: str, res: dict) -> net.Response:
    r = _get(url, user_agent)
    if r.error == "timeout":
        r = _get(url, user_agent, timeout=30)
    if r.error in ("dns", "connection"):
        alt = _get(_toggle_www(url), user_agent)
        if not alt.error:
            return alt
    if r.error in ("ssl", "connection") and url.startswith("https://"):
        res["ssl_error"] = r.error == "ssl"
        alt = _get("http://" + url[len("https://"):], user_agent)
        if not alt.error:
            return alt
    p = urllib.parse.urlparse(url)
    if r.status == 404 and p.path not in ("", "/"):
        # Hinterlegt war eine Unterseite, die es nicht mehr gibt → Startseite der Domain prüfen
        root = _get(f"{p.scheme}://{p.netloc}/", user_agent)
        if root.ok:
            res["deep_link_404"] = True
            return root
    return r


GENERIC_NAME_TOKENS = {"gmbh", "mbh", "inh", "inhaber", "inhaberin", "salon", "studio", "praxis", "friseur", "team",
                       "haus", "restaurant", "cafe", "und", "fuer", "the", "der", "die", "das", "beauty", "hair"}


def _norm(text: str) -> str:
    t = (text or "").lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss"), ("é", "e")):
        t = t.replace(a, b)
    return re.sub(r"[^a-z0-9]", "", t)


def name_found(name: str, haystack: str) -> bool:
    """Taucht ein markanter Teil des Firmennamens auf der Seite auf? (True, wenn nicht beurteilbar)"""
    tokens = [_norm(w) for w in re.split(r"[\s\-&+.,/'’()|]+", name or "")]
    tokens = [t for t in tokens if len(t) >= 4 and t not in GENERIC_NAME_TOKENS]
    if not tokens:
        return True
    hay = _norm(haystack)
    return any(t in hay for t in tokens)


def analyze(url: str, *, user_agent: str, name: str = "", check_robots: bool = True) -> dict:
    """Analysiert eine Website. status: ok | fehler | baustelle | gesperrt | plattform | fremd."""
    url = social.normalize_url(url)
    res = _empty(url)
    if check_robots:
        rb = net.ROBOTS.check(url, user_agent)
        res["robots_google_blocked"] = rb["google_blocked"]
        if not rb["allowed"]:
            res.update(status="gesperrt", status_text="robots.txt erlaubt keine automatische Prüfung")
            return res

    r = _fetch_homepage(url, user_agent, res)
    res["pages_checked"].append(r.final_url or url)
    if res["ssl_error"] and (r.error or r.status >= 400):
        res.update(status="fehler", http_status=r.status,
                   status_text="SSL-Zertifikat ungültig – Browser zeigen eine Sicherheitswarnung statt der Website")
        return res
    if r.error:
        res.update(status="fehler", status_text=f"Nicht erreichbar: {r.describe_error()}")
        return res

    final = r.final_url or url
    final_host = net.host_of(final)
    res.update(final_url=final, domain=social.registrable_domain(final), http_status=r.status,
               redirects=len(r.redirects), ttfb=round(r.ttfb, 2), load_time=round(r.elapsed, 2),
               html_kb=round(len(r.body) / 1024))
    if any(social.host_matches(final_host, h) for h in PARKING_HOSTS):
        res.update(status="baustelle", status_text="Domain ist geparkt (Verkaufs-/Parkseite)")
        return res
    plat = social.platform_of(final)
    if plat and plat["kind"] in ("social", "portal", "linkhub", "google", "google_site"):
        res.update(status="plattform", platform=plat["label"],
                   status_text=f"Domain leitet auf {plat['label']} weiter – keine eigene Website")
        return res

    html = r.text()
    low = html.lower()
    if r.status in (401, 403, 406, 429) or (r.status == 503 and (any(t in low[:20000] for t in CHALLENGE_TEXT)
                                                                 or "cf-mitigated" in r.headers)):
        res.update(status="gesperrt", status_text=f"Website blockiert automatische Prüfungen (HTTP {r.status}) – "
                                                  "bitte manuell ansehen")
        return res
    if r.status >= 400:
        res.update(status="fehler", status_text=f"Website liefert Fehler {r.status}")
        return res
    if r.content_type and "html" not in r.content_type:
        res.update(status="fehler", status_text="Startseite ist keine HTML-Seite")
        return res

    page = parse_html(html)
    text = page.visible_text
    text_low = text.lower()
    words = len(re.findall(r"\w+", text))
    res["https"] = final.startswith("https://") and not res["ssl_error"]
    res["word_count"] = words
    res["js_rendered"] = words < 40 and len(page.script_srcs) > 0

    if words < 350 and any(t in text_low or t in page.title.lower() for t in PARKED_TEXT):
        res.update(status="baustelle", status_text="Baustellen-, Wartungs- oder Standardseite des Hosters",
                   title=page.title)
        return res
    start_domain = social.registrable_domain(url)
    if res["domain"] != start_domain:
        res["redirect_domain"] = res["domain"]
        if name and not name_found(name, " ".join([page.title, text[:30000], final])):
            res.update(status="fremd", title=page.title,
                       status_text=f"{start_domain} leitet auf eine fremde Seite weiter ({res['domain']})")
            return res

    # --- SEO-Grundlagen ---
    viewport = page.meta.get("viewport", "").lower()
    robots_meta = (page.meta.get("robots", "") + " " + page.meta.get("googlebot", "")).lower()
    rels = page.link_rels
    res.update(
        title=page.title[:200],
        description=" ".join(page.meta.get("description", "").split())[:400],
        viewport="width=device-width" in viewport.replace(" ", ""),
        lang=page.lang,
        h1_count=len([h for h in page.h1 if h]),
        h1=next((h for h in page.h1 if h), "")[:200],
        og_image=bool(page.meta.get("og:image") or page.meta.get("twitter:image")),
        favicon=any("icon" in rel for rel, _ in rels),
        canonical=any(rel == "canonical" for rel, _ in rels),
        structured_data=_jsonld_types(page.jsonld)[:8],
        noindex="noindex" in robots_meta,
        img_total=page.img_total,
        img_no_alt=page.img_no_alt,
    )

    # --- Technik & Aktualität ---
    blob = low + " " + " ".join(page.script_srcs).lower() + " " + " ".join(page.iframes).lower()
    cms, kind = detect_cms(blob, page.generators, r.headers)
    plat_final = social.platform_of(final)
    if plat_final and plat_final["kind"] == "builder":
        res["builder_subdomain"] = plat_final["label"]
        if not cms:
            cms, kind = plat_final["label"], "baukasten"
    res["cms"], res["cms_kind"] = cms, kind
    if cms == "WordPress":
        res["page_builder"] = _first_match(blob, PAGE_BUILDERS)
    res["shop"] = kind == "shop" or "woocommerce" in blob
    this_year = datetime.now().year
    years = [int(m.group(1)) for m in COPYRIGHT_RE.finditer(text)]
    years = [y for y in years if 1995 <= y <= this_year]
    res["copyright_year"] = max(years) if years else None
    for src in page.script_srcs:
        m = JQUERY_RE.search(src)
        if m and "migrate" not in src.lower():
            res["jquery_version"] = m.group(1) or m.group(2) or ""
            break
    # Starke Signale (Frames, Laufschrift, Flash) zählen sofort, <font>/<center> erst ab mehreren Vorkommen
    strong = sorted(t for t in page.deprecated if t in STRONG_DEPRECATED)
    weak_count = sum(n for t, n in page.deprecated.items() if t not in STRONG_DEPRECATED)
    deprecated = strong + (sorted(t for t in page.deprecated if t not in STRONG_DEPRECATED) if weak_count >= 5 else [])
    if page.flash:
        deprecated.append("flash")
    res["deprecated"] = deprecated

    # --- Rechtliches & Datenschutz ---
    links = []
    for href, label in page.anchors:
        if not href or href.startswith(("javascript:", "#", "mailto:", "tel:")):
            continue
        links.append((urllib.parse.urljoin(final, href), label))
    impressum_url = _find_link(links, ("impressum", "imprint", "anbieterkennzeichnung", "legal-notice", "legal notice"))
    datenschutz_url = _find_link(links, ("datenschutz", "privacy", "dsgvo", "data-protection"))
    kontakt_url = _find_link(links, ("kontakt", "contact"))
    res["impressum"] = bool(impressum_url) or "impressum" in text_low
    res["datenschutz"] = bool(datenschutz_url) or "datenschutz" in text_low
    res["consent_tool"] = _first_match(blob, CONSENT_SIGNATURES)
    res["consent_hint"] = bool(res["consent_tool"]) or any(t in text_low for t in CONSENT_TEXT)
    tracking = _all_matches(blob, TRACKING_SIGNATURES)
    for m in GTAG_CONFIG_RE.finditer(blob):
        name = "Google Ads" if m.group(1).lower() == "aw" else "Google Analytics"
        if name not in tracking:
            tracking.append(name)
    res["tracking"] = tracking
    res["ads_tools"] = [t for t in tracking if t in ADS_TOOLS]
    res["google_fonts"] = "fonts.googleapis.com" in blob or "fonts.gstatic.com" in blob

    # --- Kontakt, Buchung, Video, Social ---
    hrefs = [h for h, _ in page.anchors]
    socials = social.extract_socials(hrefs + page.iframes, html, text)
    emails = collect_emails(page.anchors, text)
    phones = collect_phones(page.anchors)
    forms_ok = any(f["textarea"] or ("email" in f["inputs"] and len(f["inputs"]) >= 3) for f in page.forms)
    forms_ok = forms_ok or any(s in blob for s in FORM_SERVICES)
    booking = _first_match(blob, BOOKING_SIGNATURES)
    if not booking and any(t in text_low for t in BOOKING_TEXT):
        booking = "Online-Termin"
    video = page.video_tags > 0 or any(s in blob for s in VIDEO_SIGNATURES)
    ig_feed = any(s in blob for s in IG_FEED_SIGNATURES)

    # --- Unterseiten (Impressum, Kontakt) für Social-Links, E-Mail und Formular ---
    site_domain = res["domain"]
    subpages = []
    if impressum_url and social.registrable_domain(impressum_url) == site_domain:
        subpages.append(impressum_url)
    needs_more = not socials.get("instagram") or not socials.get("tiktok") or not emails or not forms_ok
    if kontakt_url and needs_more and social.registrable_domain(kontakt_url) == site_domain \
            and kontakt_url.split("#")[0] not in [s.split("#")[0] for s in subpages]:
        subpages.append(kontakt_url)
    for sub in subpages[:2]:
        if sub.split("#")[0].rstrip("/") == final.split("#")[0].rstrip("/"):
            continue
        if check_robots and not net.ROBOTS.check(sub, user_agent)["allowed"]:
            continue
        sr = _get(sub, user_agent)
        if not sr.ok or (sr.content_type and "html" not in sr.content_type):
            continue
        res["pages_checked"].append(sr.final_url)
        sub_html = sr.text()
        sub_page = parse_html(sub_html)
        sub_text = sub_page.visible_text
        # Unterseiten nur über echte Links auswerten: Datenschutztexte nennen viele Plattform-URLs
        social.merge_socials(socials, social.extract_socials([h for h, _ in sub_page.anchors], "", sub_text))
        for email in collect_emails(sub_page.anchors, sub_text):
            if email not in emails:
                emails.append(email)
        for phone in collect_phones(sub_page.anchors):
            if phone not in phones:
                phones.append(phone)
        sub_blob = sub_html.lower()
        if not forms_ok:
            forms_ok = any(f["textarea"] for f in sub_page.forms) or any(s in sub_blob for s in FORM_SERVICES)
        if not booking:
            booking = _first_match(sub_blob, BOOKING_SIGNATURES)

    # --- Google Fonts auch in eingebundenen CSS-Dateien suchen ---
    if not res["google_fonts"]:
        css_links = [urllib.parse.urljoin(final, href) for rel, href in rels if "stylesheet" in rel and href]
        same_site = [c for c in css_links if social.registrable_domain(c) == site_domain][:2]
        for css in same_site:
            cr = _get(css, user_agent, timeout=10)
            if cr.ok and (b"fonts.googleapis.com" in cr.body or b"fonts.gstatic.com" in cr.body):
                res["google_fonts"] = True
                break

    res.update(
        socials=socials,
        emails=emails[:5],
        phones=phones[:3],
        tel_link=bool(phones),
        contact_form=forms_ok,
        whatsapp=bool(socials.get("whatsapp")) or "wa.me/" in blob,
        booking_tool=booking,
        video=video,
        instagram_feed=ig_feed,
        status="ok",
        status_text="Website erreichbar",
    )
    return res
