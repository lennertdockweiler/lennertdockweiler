#!/usr/bin/env python3
"""Baut generator.html aus MASTER-PROMPT.md, tools/branchen-vorschlaege.json und tools/generator.template.html.

Aufruf (im Ordner website-studio):
    python3 tools/build-generator.py
Optional zusätzlich eine Fassung ohne HTML-Grundgerüst (für das Veröffentlichen als Artefakt):
    python3 tools/build-generator.py /pfad/zur/datei.html
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MASTER = ROOT / "MASTER-PROMPT.md"
PRESETS = ROOT / "tools" / "branchen-vorschlaege.json"
TEMPLATE = ROOT / "tools" / "generator.template.html"
OUTPUT = ROOT / "generator.html"


def js_list(template: str, name: str) -> set:
    """Liest eine Liste wie `const FUNCS = ['…', …];` aus der Vorlage."""
    m = re.search(rf"const {name} = \[(.*?)\];", template, re.S)
    return set(re.findall(r"'([^']+)'", m.group(1))) if m else set()


def check_presets(presets: dict, titles: set, template: str) -> list:
    """Prüft die Branchen-Vorschläge auf unbekannte Profile und ungültige Werte."""
    styles, funcs, goals = js_list(template, "STYLES"), js_list(template, "FUNCS"), js_list(template, "GOALS")
    problems = []
    for title, profile in presets.items():
        if title not in titles:
            problems.append(f"Profil „{title}“ fehlt in der Branchen-Bibliothek des Master-Prompts")
        scopes = [(title, profile)] + [(f"{title} › {v.get('name', '?')}", v) for v in profile.get("varianten", [])]
        for scope, obj in scopes:
            if "stil" in obj and obj["stil"] not in styles:
                problems.append(f"{scope}: unbekannter Stil „{obj['stil']}“")
            if "hauptziel" in obj and obj["hauptziel"] not in goals:
                problems.append(f"{scope}: unbekanntes Hauptziel „{obj['hauptziel']}“")
            for f in obj.get("funktionen", []):
                if f not in funcs:
                    problems.append(f"{scope}: unbekannte Funktion „{f}“")
            if scope != title and not obj.get("erkennen") and not obj.get("muss"):
                problems.append(f"{scope}: keine Erkennungswörter („erkennen“)")
    return problems


def block(text: str, tag: str) -> re.Match:
    """Findet einen <tag>…</tag>-Abschnitt, dessen Tags allein auf einer Zeile stehen."""
    m = re.search(rf"(?ms)^<{tag}>$(.*?)^</{tag}>$", text)
    if not m:
        sys.exit(f"Abschnitt <{tag}> nicht gefunden – bitte MASTER-PROMPT.md prüfen.")
    return m


def main() -> None:
    master = MASTER.read_text(encoding="utf-8")
    template = TEMPLATE.read_text(encoding="utf-8")

    lib = block(master, "branchen_bibliothek")
    open_end = master.index("\n", lib.start()) + 1  # Ende der Zeile mit dem öffnenden Tag
    close_start = lib.end() - len("</branchen_bibliothek>")
    before = master[:open_end].rstrip("\n")
    inner = master[open_end:close_start]
    after = master[close_start:].strip("\n") + "\n"

    parts = re.split(r"(?m)^### ", inner)
    intro = parts[0].strip()
    entries = []
    for part in parts[1:]:
        title = part.split("\n", 1)[0].strip()
        entries.append({"title": title, "body": ("### " + part).strip()})
    if not entries:
        sys.exit("Keine Branchenprofile (### …) in <branchen_bibliothek> gefunden.")

    commands = []
    for line in block(master, "anpassung").group(1).splitlines():
        if not line.startswith("| `"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        commands.append({
            "cmd": cells[0].strip("`"),
            "effect": cells[1],
            "example": cells[2].strip("`"),
        })

    try:
        presets = json.loads(PRESETS.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        sys.exit(f"{PRESETS.name} ist kein gültiges JSON: {err}")
    problems = check_presets(presets, {e["title"] for e in entries}, template)
    if problems:
        sys.exit("Fehler in den Branchen-Vorschlägen:\n- " + "\n- ".join(problems))

    version = re.search(r"Version\s+([\d.]+)", master)
    stand = re.search(r"Stand:\s*([^·\n]+)", master)
    data = {
        "version": version.group(1) if version else "",
        "stand": stand.group(1).strip() if stand else "",
        "before": before,
        "intro": intro,
        "entries": entries,
        "after": after,
        "full": master,
        "commands": commands,
        "presets": presets,
    }
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    if template.count("__DATA__") != 1:
        sys.exit("Platzhalter __DATA__ muss genau einmal in der Vorlage stehen.")
    page = template.replace("__DATA__", payload)

    head, sep, body = page.partition("<!--BODY-->")
    if not sep:
        sys.exit("Markierung <!--BODY--> fehlt in der Vorlage.")
    standalone = (
        "<!doctype html>\n<html lang=\"de\">\n<head>\n<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n"
        f"{head.strip()}\n</head>\n<body>\n{body.strip()}\n</body>\n</html>\n"
    )
    OUTPUT.write_text(standalone, encoding="utf-8")
    variants = sum(len(p.get("varianten", [])) for p in presets.values())
    print(f"{OUTPUT.relative_to(ROOT)}: {len(entries)} Branchenprofile, {len(presets)} Vorlagen mit {variants} Fachrichtungen, "
          f"{len(commands)} Befehle, {len(standalone):,} Zeichen")

    if len(sys.argv) > 1:
        target = Path(sys.argv[1])
        target.write_text(head.strip() + "\n" + body.strip() + "\n", encoding="utf-8")
        print(f"Artefakt-Fassung: {target}")


if __name__ == "__main__":
    main()
