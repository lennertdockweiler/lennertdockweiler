import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from leadscout import scoring  # noqa: E402


def site(**over):
    base = {
        "status": "ok", "status_text": "Website erreichbar", "final_url": "https://salon.de/", "domain": "salon.de",
        "https": True, "ssl_error": False, "ttfb": 0.4, "title": "Salon XY – Friseur in Bielefeld",
        "description": "Ihr Friseur in Bielefeld für Schnitt, Farbe und Pflege – jetzt online Termin buchen.",
        "viewport": True, "lang": "de", "h1_count": 1, "og_image": True, "favicon": True, "structured_data": ["HairSalon"],
        "noindex": False, "robots_google_blocked": False, "cms": "WordPress", "cms_kind": "cms",
        "copyright_year": 2026, "jquery_version": "", "deprecated": [], "impressum": True, "datenschutz": True,
        "consent_tool": "Borlabs Cookie", "consent_hint": True, "tracking": [], "ads_tools": [], "google_fonts": False,
        "phones": ["+49521"], "emails": ["info@salon.de"], "tel_link": True, "contact_form": True, "whatsapp": False,
        "booking_tool": "Treatwell", "video": True, "instagram_feed": False, "word_count": 500, "img_total": 4,
        "img_no_alt": 0, "js_rendered": False, "socials": {"instagram": [{"ident": "salonxy"}]}, "pagespeed": None,
        "builder_subdomain": "", "redirect_domain": "", "deep_link_404": False,
    }
    base.update(over)
    return base


def lead(**over):
    base = {"id": "g:1", "name": "Salon XY", "source": "google", "profil_quelle": "google", "website_url": "https://salon.de",
            "website": site(), "rating": 4.7, "reviews": 120, "business_status": "OPERATIONAL", "chain": False,
            "instagram": {"handle": "", "status": "nicht_gefunden"}, "tiktok": {"handle": "", "status": "nicht_gefunden"}}
    base.update(over)
    return base


class WebsiteScoreTest(unittest.TestCase):
    def test_good_site_scores_high(self):
        score, checks, pitches, _ = scoring.score_website(lead())
        self.assertGreaterEqual(score, 85)
        self.assertLessEqual(sum(c["max"] for c in checks), 100)

    def test_no_website_from_google(self):
        score, _, pitches, badges = scoring.score_website(lead(website_url="", website={}))
        self.assertEqual(score, 0)
        self.assertIn("Google-Unternehmensprofil", pitches[0][1])

    def test_unknown_website_from_osm(self):
        score, _, pitches, _ = scoring.score_website(lead(website_url="", website={}, profil_quelle="", source="osm"))
        self.assertIsNone(score)
        self.assertEqual(pitches[0][2], "hinweis")

    def test_weaknesses_create_pitches(self):
        bad = site(viewport=False, https=False, impressum=False, google_fonts=True, copyright_year=2017,
                   tracking=["Meta-Pixel"], consent_hint=False, consent_tool="")
        score, _, pitches, badges = scoring.score_website(lead(website=bad))
        texts = " ".join(p[1] for p in pitches)
        self.assertLess(score, 55)
        for part in ("Smartphones", "HTTPS", "Impressum", "Google Fonts", "Copyright 2017", "Cookie-Banner"):
            self.assertIn(part, texts)

    def test_blocked_site_is_not_rated(self):
        score, *_ = scoring.score_website(lead(website=site(status="gesperrt")))
        self.assertIsNone(score)


class SocialScoreTest(unittest.TestCase):
    def test_inactive_instagram_without_reels(self):
        ig = {"handle": "salonxy", "status": "ok", "metrics": {
            "followers": 250, "posts": 40, "last_post_days": 140, "last_post_date": "2026-06-17", "posts_30d": 0,
            "reels_share": 0.0, "videos_recent": 0, "sample": 12, "engagement": 0.6}}
        score, _, pitches, badges = scoring.score_instagram(lead(instagram=ig))
        texts = " ".join(p[1] for p in pitches)
        self.assertLess(score, 25)
        self.assertIn("140 Tagen", texts)
        self.assertIn("Kaum Reels", texts)

    def test_active_tiktok(self):
        tt = {"handle": "salonxy", "exists": True, "metrics": {
            "followers": 8000, "likes": 90000, "private": False, "videos_visible": 10, "last_video_days": 2,
            "last_video_date": "2026-11-02", "videos_30d": 8, "avg_views": 4000}}
        score, *_ = scoring.score_tiktok(lead(tiktok=tt))
        self.assertGreaterEqual(score, 80)

    def test_profile_without_metrics_is_neutral(self):
        score, *_ = scoring.score_instagram(lead(instagram={"handle": "salonxy", "status": "verlinkt", "metrics": None}))
        self.assertEqual(score, scoring.PROFIL_UNBEKANNT)


class EvaluateTest(unittest.TestCase):
    def test_potential_and_market(self):
        strong = lead(id="g:1", name="Stark", instagram={"handle": "stark", "status": "ok", "metrics": {
            "followers": 9000, "posts": 400, "last_post_days": 1, "posts_30d": 12, "reels_share": 0.6,
            "videos_recent": 7, "sample": 12, "engagement": 3.2}},
            tiktok={"handle": "stark", "exists": True, "metrics": {"followers": 9000, "likes": 60000, "private": False,
                    "videos_visible": 10, "last_video_days": 1, "videos_30d": 10, "avg_views": 12000}})
        weak = lead(id="g:2", name="Schwach", website_url="", website={})
        chain = lead(id="g:3", name="Kette", website_url="", website={}, chain=True, chain_count=3)
        closed = lead(id="g:4", name="Zu", business_status="CLOSED_PERMANENTLY")
        leads = [strong, weak, chain, closed]
        market = scoring.evaluate(leads)
        self.assertGreater(weak["scores"]["potenzial"], strong["scores"]["potenzial"])
        self.assertGreater(weak["scores"]["potenzial"], chain["scores"]["potenzial"])
        self.assertEqual(closed["scores"]["potenzial"], 0)
        self.assertEqual(weak["scores"]["potenzial_label"], "hoch")
        self.assertIn("Website-Bedarf", weak["tags"])
        self.assertIn("Kette", chain["tags"])
        self.assertEqual(market["firmen"], 4)
        self.assertEqual(market["mit_tiktok"], 1)
        self.assertEqual(market["ohne_website"], 2)
        self.assertTrue(all(a["bereich"] in ("website", "instagram", "tiktok") for a in weak["ansatzpunkte"]))


if __name__ == "__main__":
    unittest.main()
