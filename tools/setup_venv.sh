#!/bin/bash
# Set up the virtualenv for the sector extractor.
# Needs the Tesseract binary: sudo dnf install tesseract tesseract-langpack-eng
set -euo pipefail

VENV="$HOME/.python/venv/starsreachnotes"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python3 -m venv "$VENV"
"$VENV/bin/pip" install -q -r "$HERE/requirements.txt"

echo "Done. Run: $VENV/bin/python $HERE/extract_sector.py <screenshot>"
