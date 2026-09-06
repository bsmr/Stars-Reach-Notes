# Stars-Reach-Notes

Player notes on the game [Stars Reach](https://starsreach.com/), built from
in-game screenshots.

[`Sectors.md`](Sectors.md) holds the sector map: connections, planets, starbases,
ecology values and edicts, plus a Mermaid graph of how the sectors link up. It is
**generated** from the screenshots in [`media/screenshots/`](media/screenshots/)
by [`tools/extract_sector.py`](tools/extract_sector.py) — edit the screenshots or
the tool, not the Markdown.

[`Crafting.md`](Crafting.md) lists the resource categories and every refinery
conversion. It is **hand-maintained**: those two Galactopedia infographics use
type too small for OCR, so they are transcribed from the screenshots by hand and
need re-checking after a patch.

## Contributing screenshots

Take the screenshot at the resolution you play at and file it by what it shows:

```text
media/screenshots/<Sector>/map/<name>.png              # the MAP tab, LOCAL view
media/screenshots/<Sector>/ecology/<name>.png          # PLANET ECOLOGY - SUMMARY
media/screenshots/<Sector>/<Planet>/govbot/<name>.png  # <PLANET> GOVBOT - CITIZENSHIP
```

The path is how the tool knows what a capture is, so the directory names matter:
`<Sector>` as the game spells it, `<Planet>` as `<Sector> <designator>` — for
example `media/screenshots/Kai/Kai I/govbot/image.png`. The **file name is
free**: drop several captures of the same view into one directory (`image-0.png`,
`image-1.png`, …) to record how a sector changed over time. Connections and
planets are merged across them, so no capture can remove what another found.

**Resolution:** at least 1280px wide, and do not downscale to save space. Small
images are enlarged before the text is read, so anything above that floor works;
below it the map loses planets. Full-screen captures are fine — the tool finds
the panels on its own, no cropping needed.

Despite its title, the ecology dialog describes the *sector*, not the planet you
are standing on. Only the govbot dialog is per-planet.

## Running the tool

Needs Python 3 and the Tesseract OCR binary:

```bash
sudo dnf install tesseract tesseract-langpack-eng   # Fedora
sudo apt install tesseract-ocr tesseract-ocr-eng    # Debian/Ubuntu

./tools/setup_venv.sh
source ~/.python/venv/starsreachnotes/bin/activate

python tools/extract_sector.py media/screenshots/Kai/map/image.png
python tools/extract_sector.py <screenshot> --dry-run   # preview, writes nothing
```

Each run merges into `Sectors.md` and rewrites the connection graph. The three
screenshot types can be imported in any order, and existing entries are never
dropped — a capture taken while a planet's portal was closed will not delete it.

Run the self-check after changing the tool:

```bash
cd tools && python test_extract_sector.py   # prints "ok"
```
