import os
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from leadscout import net, website  # noqa: E402

HOME = """<!doctype html><html lang="de"><head>
<title>Salon Sonnenschein – Friseur in Bielefeld</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="Ihr Friseur in Bielefeld: Schnitt, Farbe und Pflege. Jetzt Termin vereinbaren und wohlfühlen.">
<meta name="generator" content="WordPress 6.6">
<link rel="icon" href="/favicon.ico">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter">
<script src="/wp-includes/js/jquery/jquery.min.js?ver=1.12.4"></script>
<script async src="https://www.googletagmanager.com/gtag/js?id=G-ABC123"></script>
<script type="application/ld+json">{"@context":"https://schema.org","@type":"HairSalon","name":"Salon Sonnenschein"}</script>
</head><body>
<h1>Willkommen im Salon Sonnenschein</h1>
<p>Wir schneiden, färben und pflegen. Telefon: <a href="tel:+495211234567">0521 1234567</a></p>
<a href="https://www.instagram.com/salon.sonnenschein/">Instagram</a>
<a href="https://www.facebook.com/sharer/sharer.php?u=x">Teilen</a>
<a href="/impressum">Impressum</a> <a href="/datenschutz">Datenschutz</a>
<iframe src="https://www.youtube-nocookie.com/embed/abc"></iframe>
<footer>© 2019 Salon Sonnenschein</footer>
</body></html>"""

IMPRESSUM = """<html><body><h1>Impressum</h1><p>Salon Sonnenschein, Inhaberin Anna Beispiel</p>
<p>E-Mail: info [at] salon-sonnenschein [punkt] de</p>
<a href="https://www.tiktok.com/@salon.sonnenschein">TikTok</a>
<p>Datenschutz: https://help.instagram.com/155833707900388</p></body></html>"""

PAGES = {
    "/": (200, "text/html; charset=utf-8", HOME),
    "/impressum": (200, "text/html; charset=utf-8", IMPRESSUM),
    "/robots.txt": (200, "text/plain", "User-agent: *\nDisallow: /intern/\n"),
}


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        status, ctype, body = PAGES.get(self.path, (404, "text/plain", "nicht da"))
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


class ParserTest(unittest.TestCase):
    def test_parse_html(self):
        page = website.parse_html(HOME)
        self.assertEqual(page.title, "Salon Sonnenschein – Friseur in Bielefeld")
        self.assertEqual(page.lang, "de")
        self.assertIn("width=device-width", page.meta["viewport"])
        self.assertEqual(page.h1, ["Willkommen im Salon Sonnenschein"])
        self.assertEqual(website._jsonld_types(page.jsonld), ["HairSalon"])
        self.assertIn("© 2019 Salon Sonnenschein", page.visible_text)
        self.assertNotIn("schema.org", page.visible_text)

    def test_deprecated_counting(self):
        page = website.parse_html("<center>a</center><font>b</font><marquee>c</marquee>")
        self.assertEqual(page.deprecated, {"center": 1, "font": 1, "marquee": 1})

    def test_emails(self):
        anchors = [("mailto:Info@Salon.de?subject=Hallo", "")]
        emails = website.collect_emails(anchors, "oder kontakt (at) salon-xy (punkt) de sowie logo@2x.png")
        self.assertEqual(emails, ["info@salon.de", "kontakt@salon-xy.de"])

    def test_cms(self):
        self.assertEqual(website.detect_cms("<link href='/wp-content/x.css'>", [], {}), ("WordPress", "cms"))
        self.assertEqual(website.detect_cms("", ["Wix.com Website Builder"], {}), ("Wix", "baukasten"))
        self.assertEqual(website.detect_cms("", [], {"x-wix-request-id": "1"}), ("Wix", "baukasten"))

    def test_name_found(self):
        self.assertFalse(website.name_found("El Salon Chiko", "Psychotherapie Hinrichs"))
        self.assertTrue(website.name_found("Haar für Haar", "Kerstin Baur – Haar für Haar"))
        self.assertTrue(website.name_found("Salon", "irgendwas"))  # nicht beurteilbar


class AnalyzeLocalSiteTest(unittest.TestCase):
    """End-to-End-Analyse gegen einen lokalen Testserver (ohne Internet)."""

    @classmethod
    def setUpClass(cls):
        os.environ["no_proxy"] = os.environ["NO_PROXY"] = "127.0.0.1,localhost"
        cls._orig_blocked = net.is_blocked_host
        net.is_blocked_host = lambda host: False  # lokale Adressen nur im Test erlauben
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.httpd.server_address[1]}/"

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        net.is_blocked_host = cls._orig_blocked

    def test_analyze(self):
        res = website.analyze(self.url, user_agent="LeadScout-Test", name="Salon Sonnenschein")
        self.assertEqual(res["status"], "ok", res["status_text"])
        self.assertFalse(res["https"])
        self.assertTrue(res["viewport"])
        self.assertEqual(res["cms"], "WordPress")
        self.assertEqual(res["jquery_version"], "1.12.4")
        self.assertEqual(res["copyright_year"], 2019)
        self.assertTrue(res["impressum"])
        self.assertTrue(res["datenschutz"])
        self.assertTrue(res["google_fonts"])
        self.assertIn("Google Analytics", res["tracking"])
        self.assertFalse(res["consent_hint"])
        self.assertTrue(res["tel_link"])
        self.assertTrue(res["video"])
        self.assertEqual(res["structured_data"], ["HairSalon"])
        self.assertEqual([i["ident"] for i in res["socials"]["instagram"]], ["salon.sonnenschein"])
        self.assertEqual([i["ident"] for i in res["socials"]["tiktok"]], ["salon.sonnenschein"])
        self.assertNotIn("facebook", res["socials"])
        self.assertIn("info@salon-sonnenschein.de", res["emails"])
        self.assertEqual(len(res["pages_checked"]), 2)

    def test_missing_site(self):
        res = website.analyze(self.url + "gibt-es-nicht/", user_agent="LeadScout-Test")
        # Unterseite 404 → Startseite wird geprüft und der tote Link gemerkt
        self.assertEqual(res["status"], "ok")
        self.assertTrue(res["deep_link_404"])


if __name__ == "__main__":
    unittest.main()
