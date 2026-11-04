"""Kostenlose Firmensuche über OpenStreetMap (Nominatim + Overpass), ohne API-Schlüssel.

Weniger vollständig als Google, aber ideal zum Ausprobieren. Die Branche wird über eine
Stichwortliste auf OSM-Merkmale abgebildet; unbekannte Branchen werden im Firmennamen gesucht.
"""
from __future__ import annotations

import re
import threading
import urllib.parse

from . import net

NOMINATIM = "https://nominatim.openstreetmap.org/search"
OVERPASS = [
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
BUSINESS_KEYS = ["shop", "amenity", "office", "craft", "healthcare", "leisure", "tourism"]

# (Stichwörter, Overpass-Filter). Stichwörter in Kleinschreibung, Umlaute als ae/oe/ue, ß als ss.
# "NAME:<regex>" sucht zusätzlich im Firmennamen.
BRANCHEN = [
    (["friseur", "frisoer", "frisur", "coiffeur", "haarstudio", "hairstylist", "haarsalon"], ['["shop"="hairdresser"]']),
    (["barber", "barbier", "barbershop"], ['["shop"="hairdresser"]["hairdresser"~"barber"]', "NAME:barb"]),
    (["hundesalon", "hundefriseur", "hundepflege", "tierpflege"], ['["shop"="pet_grooming"]']),
    (["kosmetik", "beauty", "schoenheit", "wimpern", "lashes", "augenbrauen"], ['["shop"="beauty"]']),
    (["nagelstudio", "nagel", "naegel", "nails", "nail"], ['["shop"="beauty"]["beauty"~"nails"]', "NAME:nail|nagel"]),
    (["solarium", "sonnenstudio"], ['["shop"="beauty"]["beauty"~"tanning"]', '["leisure"="tanning_salon"]']),
    (["tattoo", "taetowier", "piercing"], ['["shop"="tattoo"]', '["shop"="piercing"]']),
    (["massage"], ['["shop"="massage"]']),
    (["zahnarzt", "zahnaerzt", "zahnmedizin", "zahnklinik", "dental"], ['["amenity"="dentist"]', '["healthcare"="dentist"]']),
    (["kieferorthopaed"], ['["healthcare:speciality"~"orthodontics"]', "NAME:kieferorthop"]),
    (["tierarzt", "tieraerzt", "tierklinik", "tiermedizin"], ['["amenity"="veterinary"]']),
    (["arzt", "aerzt", "hausarzt", "hausaerzt", "arztpraxis", "allgemeinmedizin", "kinderarzt", "kinderaerzt",
      "hautarzt", "hautaerzt", "frauenarzt", "frauenaerzt", "augenarzt", "augenaerzt", "orthopaed"],
     ['["amenity"="doctors"]', '["healthcare"="doctor"]']),
    (["physio", "krankengymnast"], ['["healthcare"="physiotherapist"]', '["amenity"="physiotherapist"]']),
    (["ergotherap"], ['["healthcare"="occupational_therapist"]']),
    (["logopaed"], ['["healthcare"="speech_therapist"]']),
    (["psychotherap", "psycholog"], ['["healthcare"="psychotherapist"]']),
    (["heilpraktik", "naturheil", "osteopath"], ['["healthcare"="alternative"]', "NAME:osteopath|heilprakt"]),
    (["podolog", "fusspflege"], ['["healthcare"="podiatrist"]', '["shop"="beauty"]["beauty"~"pedicure"]']),
    (["hebamme"], ['["healthcare"="midwife"]']),
    (["pflegedienst", "ambulante pflege"], ['["healthcare"="nurse"]', "NAME:pflegedienst"]),
    (["apotheke"], ['["amenity"="pharmacy"]']),
    (["optiker", "brillen", "augenoptik"], ['["shop"="optician"]']),
    (["hoerakustik", "hoergeraet", "hoerakustiker"], ['["shop"="hearing_aids"]']),
    (["sanitaetshaus", "orthopaedietechnik"], ['["shop"="medical_supply"]']),
    (["restaurant", "gaststaette", "gasthaus", "gasthof", "lokal", "bistro", "steakhouse", "sushi"], ['["amenity"="restaurant"]']),
    (["pizzeria", "pizza"], ['["amenity"~"^(restaurant|fast_food)$"]["cuisine"~"pizza"]']),
    (["imbiss", "doener", "burger", "fastfood", "snack", "kebab"], ['["amenity"="fast_food"]']),
    (["cafe", "kaffee", "coffee", "kaffeehaus", "roesterei"], ['["amenity"="cafe"]']),
    (["baeckerei", "baecker", "backstube"], ['["shop"="bakery"]']),
    (["konditorei", "patisserie", "torten", "confiserie"], ['["shop"~"^(pastry|confectionery)$"]']),
    (["eisdiele", "eiscafe", "gelateria", "eisladen"], ['["amenity"="ice_cream"]', '["shop"="ice_cream"]']),
    (["bar", "cocktailbar", "cocktail", "lounge", "weinbar"], ['["amenity"="bar"]']),
    (["kneipe", "pub", "brauhaus"], ['["amenity"="pub"]']),
    (["biergarten"], ['["amenity"="biergarten"]']),
    (["catering", "partyservice"], ['["craft"="caterer"]', "NAME:catering|partyservice"]),
    (["hotel"], ['["tourism"="hotel"]']),
    (["pension", "gaestehaus", "ferienwohnung", "ferienhaus"], ['["tourism"~"^(guest_house|apartment|chalet)$"]']),
    (["fitness", "fitnessstudio", "gym", "crossfit", "kraftsport"], ['["leisure"="fitness_centre"]']),
    (["yoga", "pilates"], ['["sport"~"yoga|pilates"]', "NAME:yoga|pilates"]),
    (["kampfsport", "karate", "judo", "boxen", "kickbox", "taekwondo", "selbstverteidigung"],
     ['["sport"~"martial_arts|karate|judo|boxing|kickboxing|taekwondo"]']),
    (["tanzschule", "tanzstudio", "ballett"], ['["leisure"="dance"]', '["amenity"="dancing_school"]']),
    (["fahrschule"], ['["amenity"="driving_school"]']),
    (["musikschule"], ['["amenity"="music_school"]']),
    (["sprachschule"], ['["amenity"="language_school"]']),
    (["nachhilfe"], ['["amenity"="prep_school"]', "NAME:nachhilfe|lernstudio"]),
    (["hundeschule"], ['["amenity"="animal_training"]', "NAME:hundeschule"]),
    (["autowerkstatt", "kfz", "werkstatt", "autoservice", "autoreparatur", "reifen"], ['["shop"="car_repair"]', '["shop"="tyres"]']),
    (["autohaus", "autohaendler", "gebrauchtwagen", "autohandel"], ['["shop"="car"]']),
    (["autowaesche", "waschanlage", "autopflege", "fahrzeugpflege", "aufbereitung"], ['["amenity"="car_wash"]', "NAME:aufbereitung|detailing"]),
    (["fahrrad", "bike", "ebike"], ['["shop"="bicycle"]']),
    (["motorrad"], ['["shop"="motorcycle"]']),
    (["elektriker", "elektro", "elektrotechnik", "elektroinstallation"], ['["craft"="electrician"]']),
    (["sanitaer", "heizung", "installateur", "klempner", "shk", "haustechnik", "badsanierung"],
     ['["craft"~"^(plumber|hvac|heating_engineer)$"]']),
    (["dachdecker", "bedachung"], ['["craft"="roofer"]']),
    (["maler", "lackierer", "malerbetrieb"], ['["craft"="painter"]']),
    (["tischler", "schreiner", "tischlerei", "schreinerei"], ['["craft"~"^(carpenter|joiner|cabinet_maker)$"]']),
    (["zimmerei", "zimmermann", "holzbau"], ['["craft"="carpenter"]']),
    (["fliesen", "fliesenleger"], ['["craft"="tiler"]']),
    (["gaertner", "galabau", "landschaftsbau", "gartenbau", "gaertnerei"], ['["craft"="gardener"]', '["shop"="garden_centre"]']),
    (["schluesseldienst", "schlosser", "schlosserei"], ['["craft"~"^(locksmith|key_cutter|metal_construction)$"]', '["shop"="locksmith"]']),
    (["metallbau"], ['["craft"="metal_construction"]']),
    (["bauunternehmen", "bauunternehmung", "hochbau", "tiefbau"], ['["craft"="builder"]', '["office"="construction_company"]']),
    (["steuerberat", "steuerkanzlei", "lohnsteuer"], ['["office"="tax_advisor"]']),
    (["rechtsanwalt", "rechtsanwaelt", "anwalt", "anwaelt", "kanzlei", "notar"], ['["office"~"^(lawyer|notary)$"]']),
    (["immobilien", "makler", "immobilienmakler"], ['["office"="estate_agent"]']),
    (["versicherung"], ['["office"="insurance"]']),
    (["finanzberat", "vermoegensberat", "finanzdienst"], ['["office"~"^(financial_advisor|financial)$"]']),
    (["architekt"], ['["office"="architect"]']),
    (["werbeagentur", "marketingagentur", "agentur"], ['["office"="advertising_agency"]']),
    (["itservice", "edv", "software", "systemhaus"], ['["office"="it"]']),
    (["fotograf", "fotostudio"], ['["craft"="photographer"]', '["shop"="photo"]']),
    (["blumen", "florist", "floristik"], ['["shop"="florist"]']),
    (["metzger", "fleischer", "fleischerei", "metzgerei"], ['["shop"="butcher"]']),
    (["juwelier", "schmuck", "goldschmied"], ['["shop"="jewelry"]']),
    (["brautmode", "brautkleid", "brautladen", "hochzeitsmode"], ['["shop"="wedding"]', '["shop"="clothes"]["clothes"~"wedding"]']),
    (["mode", "modehaus", "boutique", "bekleidung", "kleidung", "fashion"], ['["shop"="clothes"]']),
    (["schuh", "schuhe", "schuhgeschaeft"], ['["shop"="shoes"]']),
    (["moebel", "einrichtung", "kueche", "kuechenstudio", "raumausstatter"], ['["shop"~"^(furniture|kitchen|interior_decoration)$"]']),
    (["buchhandlung", "buecher"], ['["shop"="books"]']),
    (["spielwaren"], ['["shop"="toys"]']),
    (["tierbedarf", "zoohandlung", "zoofachhandel"], ['["shop"="pet"]']),
    (["weingut", "winzer"], ['["craft"="winery"]', '["shop"="winery"]']),
    (["wein", "weinhandlung"], ['["shop"="wine"]']),
    (["getraenke"], ['["shop"="beverages"]']),
    (["supermarkt", "lebensmittel"], ['["shop"="supermarket"]']),
    (["bioladen", "biomarkt", "unverpackt", "hofladen"], ['["shop"~"^(organic|farm)$"]']),
    (["handy", "smartphone", "mobilfunk", "handyreparatur"], ['["shop"="mobile_phone"]']),
    (["computer"], ['["shop"="computer"]']),
    (["elektronik"], ['["shop"="electronics"]']),
    (["reisebuero", "reiseveranstalter"], ['["shop"="travel_agency"]']),
    (["bestatt"], ['["shop"="funeral_directors"]']),
    (["reinigung", "waescherei", "textilreinigung"], ['["shop"~"^(dry_cleaning|laundry)$"]']),
    (["schneiderei", "aenderungsschneider", "schneider"], ['["craft"="tailor"]', '["shop"="tailor"]']),
    (["coworking"], ['["amenity"="coworking_space"]']),
    (["kino"], ['["amenity"="cinema"]']),
    (["escape"], ['["leisure"="escape_game"]']),
    (["bowling"], ['["leisure"="bowling_alley"]']),
    (["sauna", "therme", "wellness", "spa"], ['["leisure"="sauna"]', '["shop"="beauty"]["beauty"~"spa"]', "NAME:wellness|spa"]),
    (["druckerei", "copyshop"], ['["craft"="printer"]', '["shop"="copyshop"]']),
    (["umzug", "umzuege"], ['["office"="moving_company"]', "NAME:umz"]),
    (["tankstelle"], ['["amenity"="fuel"]']),
    (["baumarkt"], ['["shop"="doityourself"]']),
    (["parfuemerie", "drogerie"], ['["shop"~"^(perfumery|chemist)$"]']),
    (["feinkost", "delikatess"], ['["shop"="deli"]']),
    (["eventlocation", "veranstaltungsort", "festsaal"], ['["amenity"="events_venue"]']),
]

_cache_lock = threading.Lock()
_area_cache: dict = {}


def normalize(text: str) -> str:
    t = text.lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss"), ("é", "e"), ("è", "e")):
        t = t.replace(a, b)
    return re.sub(r"[^a-z0-9 ]+", "", t.replace("-", "").replace("/", " "))


def filters_for(branche: str) -> tuple:
    """Gibt (Filterliste, Suchbegriff für Namen, bekannt?) zurück."""
    tokens = normalize(branche).split() or [normalize(branche)]
    best_len, best = 0, None
    for keywords, filters in BRANCHEN:
        for kw in keywords:
            if len(kw) <= 3:  # kurze Stichwörter (bar, spa, kfz …) nur bei exaktem Treffer
                hit = kw in tokens
            else:
                hit = any(tok == kw or tok.startswith(kw) or tok.endswith(kw) for tok in tokens)
            if hit and len(kw) > best_len:
                best_len, best = len(kw), filters
    name_term = re.sub(r"[^\wäöüÄÖÜß \-]+", "", branche).strip()
    if best:
        return best, name_term, True
    return [], name_term, False


def _resolve_area(ort: str, land: str, user_agent: str) -> dict:
    key = (ort.lower(), land)
    with _cache_lock:
        if key in _area_cache:
            return _area_cache[key]
    params = {"q": ort, "format": "jsonv2", "limit": 5, "countrycodes": land.lower()}
    net.THROTTLE.wait("nominatim", 1.1)
    r = net.fetch(NOMINATIM + "?" + urllib.parse.urlencode(params), accept=net.ACCEPT_JSON,
                  user_agent=user_agent, timeout=30)
    if not r.ok:
        raise RuntimeError(f"OpenStreetMap (Nominatim) nicht erreichbar: {r.describe_error() or r.status}")
    results = r.json() or []
    if not results:
        raise RuntimeError(f"Ort „{ort}“ wurde in OpenStreetMap nicht gefunden.")
    rel = next((x for x in results if x.get("osm_type") == "relation"), None)
    chosen = rel or results[0]
    s, n, w, e = (float(v) for v in chosen.get("boundingbox", [0, 0, 0, 0]))
    if abs(n - s) < 0.02:  # Punkt statt Fläche: ca. 3 km Umkreis
        lat, lon = float(chosen["lat"]), float(chosen["lon"])
        s, n, w, e = lat - 0.03, lat + 0.03, lon - 0.045, lon + 0.045
    if chosen.get("osm_type") == "relation":
        area = {"type": "area", "id": 3600000000 + int(chosen["osm_id"]), "bbox": (s, w, n, e),
                "name": chosen.get("display_name", ort)}
    else:
        area = {"type": "bbox", "bbox": (s, w, n, e), "name": chosen.get("display_name", ort)}
    with _cache_lock:
        _area_cache[key] = area
    return area


def build_query(filters: list, name_term: str, area: dict, limit: int) -> str:
    if area["type"] == "area":
        head = f"area(id:{area['id']})->.a;"
        scope = "(area.a)"
    else:
        s, w, n, e = area["bbox"]
        head = ""
        scope = f"({s:.5f},{w:.5f},{n:.5f},{e:.5f})"
    parts = []
    for flt in filters:
        if flt.startswith("NAME:"):
            regex = flt[5:].replace('"', "")
            parts += [f'nwr["name"~"{regex}",i]["{k}"]{scope};' for k in BUSINESS_KEYS]
        else:
            parts.append(f"nwr{flt}{scope};")
    if not filters:
        regex = re.escape(name_term).replace("\\", "\\\\").replace('"', "")
        parts += [f'nwr["name"~"{regex}",i]["{k}"]{scope};' for k in BUSINESS_KEYS]
    return f"[out:json][timeout:45];{head}({''.join(parts)});out center tags {max(limit * 3, 60)};"


def _overpass(query: str, user_agent: str) -> list:
    last = ""
    for endpoint in OVERPASS:
        for attempt in range(2):
            net.THROTTLE.wait("overpass", 1.0)
            r = net.fetch(endpoint, method="POST", data=urllib.parse.urlencode({"data": query}),
                          headers={"Content-Type": "application/x-www-form-urlencoded"},
                          accept=net.ACCEPT_JSON, user_agent=user_agent, timeout=50, max_bytes=20_000_000)
            if r.ok:
                data = r.json()
                if isinstance(data, dict) and "elements" in data:
                    return data["elements"]
            last = r.describe_error() or f"HTTP {r.status}"
            if r.status in (429, 502, 503, 504) and attempt == 0:
                net.THROTTLE.wait("overpass", 5.0)  # überlastet: kurz warten, einmal wiederholen
                continue
            break
    raise RuntimeError(f"OpenStreetMap (Overpass) nicht erreichbar: {last}")


def _nominatim_search(query: str, area: dict, land: str, user_agent: str) -> list:
    s, w, n, e = area["bbox"]
    params = {"q": query, "format": "jsonv2", "limit": 40, "countrycodes": land.lower(), "extratags": 1,
              "addressdetails": 1, "viewbox": f"{w},{n},{e},{s}", "bounded": 1}
    net.THROTTLE.wait("nominatim", 1.1)
    r = net.fetch(NOMINATIM + "?" + urllib.parse.urlencode(params), accept=net.ACCEPT_JSON,
                  user_agent=user_agent, timeout=30)
    data = r.json() if r.ok else None
    return data if isinstance(data, list) else []


def _nominatim_to_element(x: dict) -> dict:
    addr = x.get("address") or {}
    tags = dict(x.get("extratags") or {})
    tags.update({
        "name": x.get("name", ""),
        x.get("category", "shop"): x.get("type", ""),
        "addr:street": addr.get("road", ""),
        "addr:housenumber": addr.get("house_number", ""),
        "addr:postcode": addr.get("postcode", ""),
        "addr:city": addr.get("city") or addr.get("town") or addr.get("village") or "",
    })
    return {"type": x.get("osm_type", "node"), "id": x.get("osm_id"), "lat": x.get("lat"), "lon": x.get("lon"),
            "tags": tags, "_category": x.get("category", "")}


def nominatim_fallback(branche: str, ort: str, filters: list, area: dict, land: str, user_agent: str) -> list:
    """Ersatzweg, wenn Overpass ausfällt: Nominatim-Suche (max. 40 Treffer je Suchbegriff)."""
    queries = []
    for flt in filters:
        if flt.startswith("NAME:"):
            queries += [f"{alt} {ort}" for alt in flt[5:].split("|")[:2] if len(alt) >= 3]
            continue
        m = re.search(r'\["[a-z:_]+"="([a-z_]+)"\]', flt)
        if m:
            queries.append(f"{m.group(1).replace('_', ' ')} in {ort}")
    queries.append(f"{branche} {ort}")
    elements, seen = [], set()
    for query in list(dict.fromkeys(queries))[:4]:
        for x in _nominatim_search(query, area, land, user_agent):
            key = (x.get("osm_type"), x.get("osm_id"))
            if key in seen or x.get("category") not in BUSINESS_KEYS or not x.get("name"):
                continue
            seen.add(key)
            elements.append(_nominatim_to_element(x))
    return elements


def _first(tags: dict, *keys) -> str:
    for k in keys:
        if tags.get(k):
            return str(tags[k]).split(";")[0].strip()
    return ""


def element_to_lead(el: dict, branche: str, ort: str) -> dict:
    tags = el.get("tags") or {}
    street = " ".join(x for x in [tags.get("addr:street", ""), tags.get("addr:housenumber", "")] if x)
    city = " ".join(x for x in [tags.get("addr:postcode", ""), tags.get("addr:city", "")] if x)
    address = ", ".join(x for x in [street, city] if x)
    lat = el.get("lat") or (el.get("center") or {}).get("lat")
    lon = el.get("lon") or (el.get("center") or {}).get("lon")
    name = tags.get("name", "").strip()
    query = urllib.parse.quote_plus(f"{name} {address or ort}")
    hints = {}
    for platform, keys in (("instagram", ("contact:instagram", "instagram")),
                           ("tiktok", ("contact:tiktok", "tiktok")),
                           ("facebook", ("contact:facebook", "facebook")),
                           ("youtube", ("contact:youtube", "youtube"))):
        value = _first(tags, *keys)
        if value:
            hints[platform] = value
    category = branche  # verständlicher als OSM-Merkmale wie „shop=hairdresser“
    return {
        "id": f"osm:{el.get('type', 'x')}/{el.get('id')}",
        "name": name,
        "address": address,
        "phone": _first(tags, "phone", "contact:phone", "contact:mobile"),
        "email_hint": _first(tags, "email", "contact:email"),
        "website_raw": _first(tags, "website", "contact:website", "url"),
        "maps_url": f"https://www.google.com/maps/search/?api=1&query={query}",
        "osm_url": f"https://www.openstreetmap.org/{el.get('type', 'node')}/{el.get('id')}",
        "rating": None,
        "reviews": None,
        "category": category,
        "business_status": "",
        "lat": lat,
        "lng": lon,
        "source": "osm",
        "branche": branche,
        "ort": ort,
        "hints": hints,
    }


def search(branche: str, ort: str, *, land: str = "DE", limit: int = 20, user_agent: str = "", log=None) -> list:
    filters, name_term, known = filters_for(branche)
    if not known and log:
        log(f"  Branche „{branche}“ ist nicht in der OSM-Stichwortliste – suche im Firmennamen.")
    area = _resolve_area(ort, land, user_agent)
    try:
        elements = _overpass(build_query(filters, name_term, area, limit), user_agent)
    except RuntimeError as e:
        if log:
            log(f"  {e} – nutze Ersatzweg über Nominatim (weniger Treffer).")
        elements = nominatim_fallback(branche, ort, filters, area, land, user_agent)
        if not elements:
            raise
    leads = [element_to_lead(el, branche, ort) for el in elements if (el.get("tags") or {}).get("name")]
    # Einträge mit Website zuerst, dann alphabetisch
    leads.sort(key=lambda x: (0 if x["website_raw"] else 1, x["name"].lower()))
    seen, unique = set(), []
    for lead in leads:
        key = (lead["name"].lower(), lead["address"].lower())
        if key in seen:
            continue
        seen.add(key)
        unique.append(lead)
    return unique[:limit]
