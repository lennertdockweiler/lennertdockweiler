"""Kommandozeile. Ohne Angaben startet die Oberfläche im Browser."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__, pipeline
from .config import SetupError, load_settings

EPILOG = """Beispiele:
  python3 leadscout.py                              Oberfläche im Browser starten
  python3 leadscout.py "Friseur" "Bielefeld"        Suche direkt in der Kommandozeile
  python3 leadscout.py "Friseur, Barbershop" "Bielefeld, Gütersloh" --anzahl 40 --pagespeed
  python3 leadscout.py --liste firmen.txt           eigene Liste bewerten
  python3 leadscout.py --pruefen                    API-Schlüssel und Verbindungen testen
  python3 leadscout.py --neu-bewerten berichte/….json   Bericht nach Änderung der Gewichte neu berechnen
"""


def _console_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def _print_checks(settings) -> int:
    print("Verbindungen werden getestet …\n")
    worst = 0
    for name, ok, message in pipeline.check_connections(settings):
        mark = "OK  " if ok is True else ("FEHLT" if ok is None else "FEHLER")
        if ok is False:
            worst = 1
        print(f"  [{mark}] {name}\n          {message}")
    return worst


def _print_summary(result: dict, report_dir: Path) -> None:
    leads = result["leads"]
    print()
    for note in result.get("hinweise") or []:
        print(f"Hinweis: {note}")
    print(f"\nTop-Leads ({len(leads)} Firmen bewertet):\n")
    print(f"  {'Pot.':>4}  {'Firma':<34} {'Web':>4} {'IG':>4} {'TT':>4}  Wichtigster Ansatzpunkt")
    for lead in leads[:15]:
        s = lead["scores"]
        web = "–" if s["website"] is None else str(s["website"])
        top = (lead.get("ansatzpunkte") or [{"text": ""}])[0]["text"]
        print(f"  {s['potenzial']:>4}  {lead['name'][:34]:<34} {web:>4} {s['instagram']:>4} {s['tiktok']:>4}  {top[:70]}")
    files = result["dateien"]
    print(f"\nBericht:  {report_dir / files['html']}")
    print(f"Excel:    {report_dir / files['csv']}")
    print(f"Rohdaten: {report_dir / files['json']}")


def main(argv=None) -> int:
    _console_utf8()
    parser = argparse.ArgumentParser(
        prog="leadscout.py", formatter_class=argparse.RawDescriptionHelpFormatter, epilog=EPILOG,
        description=f"Lead-Scout {__version__}: Firmen nach Branche und Ort finden und Website, Instagram und "
                    "TikTok bewerten.")
    parser.add_argument("branche", nargs="?", help="z. B. \"Friseur\" (mehrere mit Komma trennen)")
    parser.add_argument("ort", nargs="?", help="z. B. \"Bielefeld\" (mehrere mit Komma trennen)")
    parser.add_argument("--anzahl", type=int, default=20, help="Firmen pro Suche (1–60, Standard 20)")
    parser.add_argument("--quelle", choices=["auto", "google", "osm"], default="auto",
                        help="auto = Google, wenn ein Schlüssel hinterlegt ist, sonst OpenStreetMap")
    parser.add_argument("--liste", metavar="DATEI", help="eigene Liste: eine Firma oder Website pro Zeile")
    parser.add_argument("--pagespeed", action="store_true", help="Ladezeit mobil mit Google PageSpeed messen (langsamer)")
    parser.add_argument("--ohne-tiktok", action="store_true", help="TikTok-Profile nicht prüfen")
    parser.add_argument("--ohne-instagram", action="store_true", help="keine Instagram-Kennzahlen abrufen")
    parser.add_argument("--pruefen", action="store_true", help="API-Schlüssel und Verbindungen testen")
    parser.add_argument("--neu-bewerten", metavar="JSON", help="gespeicherten Bericht neu bewerten (nach Änderungen an der Bewertung)")
    parser.add_argument("--port", type=int, default=8765, help="Port der Oberfläche (Standard 8765)")
    parser.add_argument("--kein-browser", action="store_true", help="Oberfläche starten, ohne den Browser zu öffnen")
    args = parser.parse_args(argv)
    settings = load_settings()

    try:
        if args.pruefen:
            return _print_checks(settings)
        if args.neu_bewerten:
            result = pipeline.rescore(Path(args.neu_bewerten))
            _print_summary(result, Path(args.neu_bewerten).parent)
            return 0
        if not args.liste and not (args.branche and args.ort):
            if args.branche and not args.ort:
                parser.error("Bitte Branche UND Ort angeben, z. B.: python3 leadscout.py \"Friseur\" \"Bielefeld\"")
            from .server import serve
            serve(args.port, open_browser=not args.kein_browser)
            return 0

        data = {"branche": args.branche or "", "ort": args.ort or "", "anzahl": args.anzahl, "quelle": args.quelle,
                "pagespeed": args.pagespeed, "tiktok": not args.ohne_tiktok, "instagram": not args.ohne_instagram}
        if args.liste:
            data["quelle"] = "liste"
            data["liste"] = Path(args.liste).read_text(encoding="utf-8-sig")
        options = pipeline.Options.from_dict(data)
        progress = pipeline.Progress(on_log=lambda msg: print(msg, flush=True))
        try:
            result = pipeline.run(options, settings, progress)
        except KeyboardInterrupt:
            print("\nAbgebrochen.")
            return 130
        _print_summary(result, settings.report_dir)
        return 0
    except SetupError as e:
        print(f"\nFehler: {e}", file=sys.stderr)
        return 2
    except FileNotFoundError as e:
        print(f"\nDatei nicht gefunden: {e.filename}", file=sys.stderr)
        return 2
