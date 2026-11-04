import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from leadscout import social  # noqa: E402

NOW = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc).timestamp()


class ClassifySocialTest(unittest.TestCase):
    def test_profiles(self):
        self.assertEqual(social.classify_social("https://www.instagram.com/salon_xy/")[:2], ("instagram", "salon_xy"))
        self.assertEqual(social.classify_social("https://instagram.com/Salon.XY?igsh=abc")[:2], ("instagram", "salon.xy"))
        self.assertEqual(social.classify_social("https://www.tiktok.com/@salon.xy?lang=de")[:2], ("tiktok", "salon.xy"))
        self.assertEqual(social.classify_social("https://de-de.facebook.com/SalonXY/")[:2], ("facebook", "SalonXY"))
        self.assertEqual(social.classify_social("https://www.facebook.com/profile.php?id=1000")[:2],
                         ("facebook", "profile.php?id=1000"))
        self.assertEqual(social.classify_social("https://de.linkedin.com/company/salon-xy")[:2],
                         ("linkedin", "company/salon-xy"))
        self.assertEqual(social.classify_social("https://wa.me/491701234567")[0], "whatsapp")
        self.assertEqual(social.classify_social("https://vm.tiktok.com/ZMabc/")[0], "tiktok_short")

    def test_ignores_share_buttons_posts_and_help_pages(self):
        for url in [
            "https://www.facebook.com/sharer/sharer.php?u=https://salon.de",
            "https://www.instagram.com/p/Cabc123/",
            "https://help.instagram.com/155833707900388",
            "https://www.facebook.com/docs",
            "https://developers.facebook.com/salon",
            "https://l.facebook.com/l.php?u=x",
            "https://x.com/intent/tweet?text=hallo",
            "https://x.com/de",
            "https://www.instagram.com/",
            "https://www.tiktok.com/embed.js",
        ]:
            self.assertIsNone(social.classify_social(url), url)

    def test_ignores_template_placeholders(self):
        self.assertIsNone(social.classify_social("https://www.instagram.com/wix"))
        self.assertIsNone(social.classify_social("https://www.facebook.com/wix"))
        self.assertIsNone(social.classify_social("https://www.instagram.com/yourusername/"))
        self.assertIsNone(social.classify_social("https://www.instagram.com/123456789/"))


class ExtractSocialsTest(unittest.TestCase):
    def test_links_json_and_text(self):
        html = '{"sameAs":["https:\\/\\/www.instagram.com\\/salon_json\\/"]}'
        text = "Folgt uns auf Instagram: @salon_text oder schreibt an info@salon.de"
        found = social.extract_socials(["https://www.tiktok.com/@salon_tt"], html, text)
        self.assertEqual([i["ident"] for i in found["instagram"]], ["salon_json", "salon_text"])
        self.assertEqual(found["instagram"][0]["via"], "quelltext")
        self.assertEqual(found["tiktok"][0]["ident"], "salon_tt")

    def test_email_is_not_a_mention(self):
        found = social.extract_socials([], "", "Instagram und E-Mail: kontakt@salon-xy.de")
        self.assertNotIn("instagram", found)

    def test_pick_best_prefers_matching_handle(self):
        items = [{"ident": "webagentur_mueller", "url": "", "via": "link"},
                 {"ident": "friseur.sivo", "url": "", "via": "link"}]
        best = social.pick_best(items, "Friseur Sivo", "friseur-sivo.de")
        self.assertEqual(best["ident"], "friseur.sivo")


class PlatformTest(unittest.TestCase):
    def test_platform_of(self):
        self.assertEqual(social.platform_of("https://linktr.ee/salon")["kind"], "linkhub")
        self.assertEqual(social.platform_of("https://salon.business.site")["kind"], "google_site")
        self.assertEqual(social.platform_of("https://www.treatwell.de/ort/salon/")["kind"], "portal")
        self.assertEqual(social.platform_of("https://salon.wixsite.com/home")["kind"], "builder")
        self.assertEqual(social.platform_of("https://www.facebook.com/salon")["label"], "Facebook")
        self.assertIsNone(social.platform_of("https://www.salon-xy.de"))

    def test_registrable_domain(self):
        self.assertEqual(social.registrable_domain("https://www.shop.salon.co.at/x"), "salon.co.at")
        self.assertEqual(social.registrable_domain("https://www.salon-xy.de/kontakt"), "salon-xy.de")

    def test_instagram_candidates(self):
        self.assertEqual(social.instagram_candidates("friseur-sivo.de"), ["friseursivo", "friseur_sivo"])
        self.assertEqual(social.instagram_candidates("sivo.de"), ["sivo"])


class TikTokParseTest(unittest.TestCase):
    def test_embed(self):
        ts_recent, ts_old = int(NOW - 3 * 86400), int(NOW - 40 * 86400)
        state = {"source": {"data": {"/embed/@salonxy": {
            "isError": False,
            "userInfo": {"followerCount": 1200, "heartCount": 5400, "followingCount": 10, "privateAccount": False,
                         "verified": False, "nickname": "Salon XY", "signature": "Bio"},
            "videoList": [{"id": str((ts_old << 32) + 7), "playCount": 200},
                          {"id": str((ts_recent << 32) + 3), "playCount": 800}],
        }}}}
        html = f'<script id="__FRONTITY_CONNECT_STATE__" type="application/json">{json.dumps(state)}</script>'
        m = social.parse_tiktok_embed(html, now=NOW)
        self.assertTrue(m["exists"])
        self.assertEqual(m["followers"], 1200)
        self.assertEqual(m["last_video_days"], 3)
        self.assertEqual(m["videos_30d"], 1)
        self.assertEqual(m["videos_90d"], 2)
        self.assertEqual(m["avg_views"], 500)

    def test_embed_missing_user(self):
        state = {"source": {"data": {"/embed/@gibtsnicht": {"isError": True}}}}
        html = f'<script id="__FRONTITY_CONNECT_STATE__">{json.dumps(state)}</script>'
        self.assertEqual(social.parse_tiktok_embed(html, now=NOW), {"exists": False})

    def test_video_id_timestamp(self):
        self.assertEqual(social.video_id_timestamp(str((1760000000 << 32) + 99), now=NOW), 1760000000)
        self.assertIsNone(social.video_id_timestamp("123", now=NOW))


class InstagramParseTest(unittest.TestCase):
    def test_business_discovery(self):
        bd = {"followers_count": 1000, "follows_count": 100, "media_count": 120, "name": "Salon",
              "website": "https://salon.de", "media": {"data": [
                  {"timestamp": "2026-10-20T10:00:00+0000", "media_type": "IMAGE", "media_product_type": "FEED",
                   "like_count": 30, "comments_count": 2},
                  {"timestamp": "2026-11-01T10:00:00+0000", "media_type": "VIDEO", "media_product_type": "REELS",
                   "like_count": 50, "comments_count": 5},
              ]}}
        m = social.parse_ig_business(bd, now=NOW)
        self.assertEqual(m["followers"], 1000)
        self.assertEqual(m["last_post_days"], 3)
        self.assertEqual(m["last_post_date"], "2026-11-01")
        self.assertEqual(m["posts_30d"], 2)
        self.assertEqual(m["reels_share"], 0.5)
        self.assertAlmostEqual(m["engagement"], 4.35)


if __name__ == "__main__":
    unittest.main()
