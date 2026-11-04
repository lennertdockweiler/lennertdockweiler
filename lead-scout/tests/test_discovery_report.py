import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from leadscout import discovery, google, osm, pipeline, report, scoring  # noqa: E402
from leadscout.config import Settings  # noqa: E402

PLACE = {
    "id": "ChIJ123",
    "displayName": {"text": "Salon Sonnenschein", "languageCode": "de"},
    "formattedAddress": "Hauptstraße 1, 33602 Bielefeld, Deutschland",
    "websiteUri": "https://www.instagram.com/salon.sonnenschein/",
    "nationalPhoneNumber": "0521 1234567",
    "rating": 4.8,
    "userRatingCount": 212,
    "businessStatus": "OPERATIONAL",
    "googleMapsUri": "https://maps.google.com/?cid=1",
    "primaryTypeDisplayName": {"text": "Friseursalon"},
    "location": {"latitude": 52.02, "longitude": 8.53},
}


class DiscoveryTest(unittest.TestCase):
    def test_split_terms(self):
        self.assertEqual(discovery.split_terms("Friseur, Barbershop; friseur\nKosmetik"), ["Friseur", "Barbershop", "Kosmetik"])

    def test_place_with_instagram_as_website(self):
        lead = google.place_to_lead(PLACE, "Friseur", "Bielefeld")
        discovery.prepare(lead)
        self.assertEqual(lead["website_url"], "")
        self.assertEqual(lead["website_platform"], "Instagram")
        self.assertEqual(lead["socials"]["instagram"][0]["ident"], "salon.sonnenschein")
        self.assertEqual(lead["socials"]["instagram"][0]["via"], "google")

    def test_list_parsing_without_google(self):
        text = "# Kommentar\nSalon A; https://salon-a.de\nsalon-b.de\nCafé C; Bielefeld\n"
        leads = discovery.parse_list(text, Settings(), log=lambda m: None)
        self.assertEqual([l["name"] for l in leads], ["Salon A", "salon-b.de", "Café C"])
        self.assertEqual(leads[1]["website_raw"], "salon-b.de")
        self.assertTrue(leads[1]["name_from_domain"])
        self.assertEqual(leads[2]["ort"], "Bielefeld")

    def test_chains(self):
        leads = [{"id": str(i), "name": f"Filiale {i}", "website_raw": "https://kette.de/standort", "source": "google",
                  "hints": {}} for i in range(3)] + [{"id": "x", "name": "Solo", "website_raw": "https://solo.de",
                                                       "source": "google", "hints": {}}]
        for l in leads:
            discovery.prepare(l)
        discovery.mark_chains(leads)
        self.assertEqual([l["chain"] for l in leads], [True, True, True, False])

    def test_osm_mapping(self):
        self.assertEqual(osm.filters_for("Friseure")[0], ['["shop"="hairdresser"]'])
        self.assertEqual(osm.filters_for("Hundefriseur")[0], ['["shop"="pet_grooming"]'])
        self.assertEqual(osm.filters_for("Zahnärzte")[0][0], '["amenity"="dentist"]')
        self.assertFalse(osm.filters_for("Sparkasse")[2])  # unbekannt → Namenssuche
        q = osm.build_query(['["shop"="hairdresser"]'], "Friseur", {"type": "area", "id": 3600062646}, 20)
        self.assertIn('area(id:3600062646)->.a;', q)
        self.assertIn('nwr["shop"="hairdresser"](area.a);', q)

    def test_options_from_dict(self):
        o = pipeline.Options.from_dict({"branche": "Friseur, Barber", "ort": "Bielefeld", "anzahl": "500",
                                        "quelle": "kaputt", "pagespeed": "true"})
        self.assertEqual((o.branchen, o.orte, o.anzahl, o.quelle, o.pagespeed),
                         (["Friseur", "Barber"], ["Bielefeld"], 60, "auto", True))


class ReportTest(unittest.TestCase):
    def test_write_all(self):
        lead = google.place_to_lead(PLACE, "Friseur", "Bielefeld")
        lead["name"] = "=HYPERLINK(\"x\") </script> Salon"
        discovery.prepare(lead)
        lead["instagram"] = {"handle": "salon.sonnenschein", "url": "https://www.instagram.com/salon.sonnenschein/",
                             "via": "google", "status": "verlinkt", "metrics": None}
        lead["tiktok"] = {"handle": "", "status": "nicht_gefunden", "metrics": None}
        market = scoring.evaluate([lead])
        result = {"version": "test", "erstellt": "2026-11-04T12:00:00+01:00",
                  "suche": {"titel": "Friseur in Bielefeld", "branchen": ["Friseur"], "orte": ["Bielefeld"],
                            "anzahl": 20, "quelle": "google"},
                  "optionen": {}, "markt": market, "hinweise": [], "abgebrochen": False, "dauer_s": 5, "leads": [lead]}
        with tempfile.TemporaryDirectory() as tmp:
            files = report.write_all(result, Path(tmp))
            html = (Path(tmp) / files["html"]).read_text(encoding="utf-8")
            self.assertEqual(html.count("</script>"), 2)  # nur die beiden echten Script-Enden, nichts aus den Daten
            self.assertIn("Friseur in Bielefeld", html)
            raw = (Path(tmp) / files["csv"]).read_bytes()
            self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
            rows = list(csv.DictReader(raw.decode("utf-8-sig").splitlines(), delimiter=";"))
            self.assertEqual(rows[0]["Firma"][0], "'")  # Schutz vor Excel-Formeln
            self.assertEqual(rows[0]["Google-Bewertung"], "4,8")
            data = json.loads((Path(tmp) / files["json"]).read_text(encoding="utf-8"))
            self.assertEqual(data["leads"][0]["scores"]["website"], 0)
            listed = report.list_reports(Path(tmp))
            self.assertEqual(listed[0]["firmen"], 1)


if __name__ == "__main__":
    unittest.main()
