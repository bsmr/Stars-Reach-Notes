# Stars-Reach-Notes

## Language & Communication

- **Responses to the user**: Always in German — short, concise, technically precise.
- **Everything else** (code, commits, code comments, file contents): Always in English.
- **Prompt correction**: Check the user's German prompt for style, grammar, and
  spelling before answering. If errors are found: prepend brief corrections,
  then the actual answer.
- **Style (all languages)**: Precise, concise, technical. No filler text, no platitudes.

## Project Overview

Player notes on the game *Stars Reach*. In-game screenshots are the source of
truth; `tools/extract_sector.py` reads them with OCR and maintains `Sectors.md`.

**`Sectors.md` is generated.** Do not hand-edit its content — the next tool run
overwrites the sector sections. To change the *layout*, change `format_entry()`
and `read_sector()` together, then regenerate.

## Build & Test Commands

```bash
./tools/setup_venv.sh                      # venv at ~/.python/venv/starsreachnotes
sudo dnf install tesseract tesseract-langpack-eng   # Fedora; the OCR binary

python tools/extract_sector.py media/screenshots/<Sector>/map/image.png
python tools/extract_sector.py <screenshot> --dry-run   # print, write nothing

cd tools && python test_extract_sector.py  # assert-based self-check, prints "ok"
```

Regenerate everything from scratch:

```bash
printf '# Stars Reach - Sectors\n\n## Sectors\n' > Sectors.md
for f in media/screenshots/*/map/image.png \
         media/screenshots/*/ecology/image.png \
         media/screenshots/*/*/govbot/image.png; do
  python tools/extract_sector.py "$f" >/dev/null
done
```

## Architecture

The screenshot's path decides what a capture is and what it belongs to:

```text
media/screenshots/<Sector>/map/image.png              # sector structure
media/screenshots/<Sector>/ecology/image.png          # sector values
media/screenshots/<Sector>/<Planet>/govbot/image.png  # planet values
```

Domain facts that are not visible in the code or the screenshots:

- The ecology dialog is titled "PLANET ECOLOGY" but describes the **sector**,
  including the edicts that govern farming in the sector's space. Only the
  govbot dialog is per-planet.
- Planets are named `<Sector> <designator>` (`Kai I`, `Kai III-C`). `locate()`
  relies on this to tell a planet directory from a screenshot type.
- Each sector has two fixed planets (`I`, `II`) and two whose portals are not
  always open (`III-x`, `IV-x`). A map capture without them is normal, so
  **planets are only ever added, never removed**.
- Sector connections are symmetric; the Mermaid graph deduplicates each pair.

Every run rewrites the `## Connections` Mermaid graph from the sector sections,
so `Sectors.md` stays the single source for the graph.

## Screenshots

- Submit at native resolution, **at least 1280px wide**. Below that the map
  loses planets even after upscaling.
- Do not downscale to save space. Measured: a native 1920px map capture loses a
  planet, 1024px loses everything. `ocr()` enlarges small images before reading
  them, so any resolution above the floor works without preprocessing.

## Style Guide

Python: [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html).

## Git Workflow

See `/git-workflow`. Hard rules:

- `main` and `production-*` are protected — no force-push, merge only.
- Commits with signoff (`git commit -s`) and a conventional-commit prefix.
