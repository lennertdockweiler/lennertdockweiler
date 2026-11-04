#!/usr/bin/env python3
"""Lead-Scout starten.

    python3 leadscout.py                         Oberfläche im Browser
    python3 leadscout.py "Friseur" "Bielefeld"   Suche in der Kommandozeile
    python3 leadscout.py --help                  alle Optionen
"""
import sys

if sys.version_info < (3, 9):
    sys.exit("Lead-Scout braucht Python 3.9 oder neuer. Download: https://www.python.org/downloads/")

from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from leadscout.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
