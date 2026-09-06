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

`Coordinates.md` is generated too, from map captures only, and holds the
**history**: a row per waypoint per capture, but written only when the
coordinates changed. Unlike `Sectors.md` it cannot be rebuilt from the current
screenshots — a replaced capture is gone from disk but its row stays. So never
delete it to regenerate; the tool merges into it and sorts by time, which is
what keeps the result independent of the order captures are read in.

Every row names its capture by git blob hash, so a screenshot does not have to
stay in the working tree once it has been read — one map capture per sector is
enough to keep the tree readable:

```bash
git cat-file blob <id> > capture.png   # the image the row came from
```

This only works while the blob is reachable, i.e. it was committed at least
once. Read a capture *before* removing it, never after.

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
# keep the hand-written header (title + the note on temporary portals)
{ sed '/^## Connections$/,$d' Sectors.md; echo '## Sectors'; } > Sectors.md.new
mv Sectors.md.new Sectors.md
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
- **Edicts are a do-not-farm list.** Harvesting a resource an edict names is
  punished: the yield is withheld — farming iron under an iron edict returned
  nothing. So a short edict list is good news for a planet, and the sector's
  Servitor Edicts apply on top of the planet's own.
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
- **`III-x` and `IV-x` have no govbot.** They are unsettled and hostile — one
  landing zone was inside lava — so a planet section with nothing but a name is
  complete data, not a missing capture. Only `I` and `II` carry population and
  edicts.
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
- A capture's timestamp comes from the PNG's `Creation Time`, which
  gnome-screenshot writes. The file's mtime is only when it was copied into the
  repo and a clone resets it, so it is a fallback, not the source.
- OCR reads a roman "I" as a pipe, which would break the Markdown table in
  `Coordinates.md`. `waypoints()` runs labels through `planet()` for that
  reason, not just for tidiness.

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
