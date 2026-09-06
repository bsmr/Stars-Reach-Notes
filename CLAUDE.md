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

`Crafting.md` is the opposite: **hand-maintained**, transcribed from the two
Galactopedia infographics under `media/screenshots/{Resources,Refining}/`. Their
type is below what OCR can read — measured, the full-image pass returns about a
quarter of the entries, with errors like "Bauxite -> inum" — so do not build an
extractor for them. Read the images directly (crop and upscale) when updating.

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
head -8 Sectors.md > /tmp/header.md   # title + the note on temporary portals
{ cat /tmp/header.md; echo '## Sectors'; } > Sectors.md
for f in media/screenshots/*/map/*.png \
         media/screenshots/*/ecology/*.png \
         media/screenshots/*/*/govbot/*.png; do
  python tools/extract_sector.py "$f" >/dev/null
done
```

## Architecture

The screenshot's path decides what a capture is and what it belongs to:

```text
media/screenshots/<Sector>/map/*.png                  # sector structure
media/screenshots/<Sector>/ecology/*.png              # sector values
media/screenshots/<Sector>/<Planet>/govbot/*.png      # planet values
```

Domain facts that are not visible in the code or the screenshots:

- The ecology dialog is titled "PLANET ECOLOGY" but describes the **sector**,
  including the edicts that govern farming in the sector's space. Only the
  govbot dialog is per-planet.
- Edicts, health and the resource percentages are **snapshots of a
  player-driven economy**, not constants. Identical edicts across sectors mean
  players currently need the same resources, not that the values are fixed.
  Treat them as "true when captured"; only connections and planets are
  structural enough to accumulate.
- Planets are named `<Sector> <designator>` (`Kai I`, `Kai III-C`). `locate()`
  relies on this to tell a planet directory from a screenshot type.
- Each sector has two fixed planets (`I`, `II`) and two whose portals are not
  always open (`III-x`, `IV-x`), and their coordinates move between captures.
  Sector connections come and go the same way.
- Some portals open only for a limited time and the game announces it in chat
  ("the portal to Pewazi is now open"). A capture therefore shows what was
  reachable at that moment, never the full set.
- Therefore **connections and planets are only ever added, never removed**, and
  a starbase is never unset. `Sectors.md` records what has *ever* been reachable,
  not what is reachable right now, and a single capture is never evidence that
  something is gone. This is also what makes the result independent of the order
  captures are read in.
- Sector connections are symmetric, but the *sections* need not be: a sector
  whose capture predates a new neighbour will not list it. The Mermaid graph
  unions both directions, so the edge still shows up.
- Not every sector has a starbase or planets. `Pewazi` is a hub reached through
  such a temporary portal: connections to every other sector, no starbase, no
  planets, and rich in mined resources. A section with only a Connections block
  is valid output, not a failed extraction.
- The starbase sits at the same sector-relative coordinates (594, 150, 391) in
  every sector that has one, so it is part of the sector layout. Waypoint
  coordinates are relative to the sector they are viewed from.

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
