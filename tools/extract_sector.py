#!/usr/bin/env python3
"""Extract Stars Reach screenshot data into Sectors.md.

Usage: extract_sector.py <screenshot.png> [--file Sectors.md] [--dry-run]

The screenshot's path says what the image is and what it belongs to:

    media/screenshots/<Sector>/map/image.png
    media/screenshots/<Sector>/ecology/image.png
    media/screenshots/<Sector>/<Planet>/govbot/image.png

Existing entries are merged, never dropped, so the three screenshot types
can be imported in any order.
"""

import argparse
import re
import sys
from pathlib import Path

import pytesseract
from PIL import Image

# Screenshots narrower than this are enlarged before OCR (see ocr()).
OCR_MIN_WIDTH = 3200

# Map waypoints look like: "Cohufotag II (245, 87, 321)"
WAYPOINT = re.compile(r"^\s*(.+?)\s*\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\)\s*$")

# Order of the detail lines; unknown fields are kept and listed after these.
SECTOR_FIELDS = ["Health", "Minerals", "Flora", "Fauna", "Servitor Edicts", "Guardian Edicts"]
PLANET_FIELDS = ["Population", "Mineral Edicts", "Flora Edicts", "Fauna Edicts"]


def ocr(image_path):
    """OCR a screenshot, enlarging it first if it was taken at a low resolution.

    Tesseract needs large glyphs. Measured on the map screenshots, a native
    1920px capture loses a planet and a 1024px one loses everything, while the
    same images upscaled to OCR_MIN_WIDTH read correctly. Contributors can
    therefore submit screenshots at whatever resolution they play at.
    """
    img = Image.open(image_path)
    if img.width < OCR_MIN_WIDTH:
        factor = OCR_MIN_WIDTH / img.width
        img = img.resize((round(img.width * factor), round(img.height * factor)), Image.LANCZOS)
    return pytesseract.image_to_string(img)


def classify_map(text, sector):
    """Split map waypoints into starbase flag, connections and planet names."""
    starbase, connections, planets = False, [], []
    for line in text.splitlines():
        m = WAYPOINT.match(line)
        if not m:
            continue
        # OCR reads the waypoint icon as a stray glyph in front of the name
        name = re.sub(r"^[^\w]+\s*", "", m.group(1))
        if name.endswith("Starbase"):
            starbase = True
        elif name.endswith(" Sector"):
            connections.append(name[: -len(" Sector")])
        elif pl := planet(name, sector):
            planets.append(pl)
        # ponytail: everything else (Current location, Public event) is transient, ignored
    return starbase, sorted(set(connections)), sorted(set(planets))


def planet(name, sector):
    """Rebuild "<Sector> <designator>" from an OCR'd waypoint, or None if it is not a planet."""
    m = re.search(rf"{re.escape(sector)}\s*(.*)$", name)
    if not m:
        return None
    # OCR renders roman "I" as a lowercase L or a pipe and may swallow the space before it
    designator = m.group(1).strip().replace("l", "I").replace("|", "I")
    if not re.fullmatch(r"[IVX]+(-[A-Z])?", designator):
        return None
    # ponytail: designators beyond "IV-B" style would be dropped, widen the pattern if they appear
    return f"{sector} {designator}"


def parse_ecology(text):
    """Read the PLANET ECOLOGY dialog into sector fields.

    Despite the dialog's title everything in it describes the sector, including
    the edicts that govern farming in the sector's space.
    """
    # Matched generically so Guardian edicts land here too, without a code change
    fields = {m.group(1): m.group(2).strip()
              for m in re.finditer(r"^\s*(\w+ Edicts):\s*(.+?)\s*$", text, re.M)}
    if m := re.search(r"Overall Planet Health:\s*([\d.]+\s*%)", text):
        fields["Health"] = m.group(1).replace(" ", "")
    # The em dash and the middle dot come back from OCR as assorted punctuation
    for kind, quantity, diversity in re.findall(
        r"(Minerals|Flora|Fauna)\s*\W+\s*Quantity\s*(\d+)\s*%\s*\W+\s*Diversity\s*(\d+)\s*%", text
    ):
        fields[kind] = f"Quantity {quantity}%, Diversity {diversity}%"
    return fields


def parse_govbot(text):
    """Read the GOVBOT citizenship dialog into per-planet fields."""
    fields = {}
    # ponytail: the mayor's name is skipped, OCR turns "Ieti" into "leti" and
    # proper names cannot be corrected without a name list
    if m := re.search(r"Population:\s*(\d+)", text):
        fields["Population"] = m.group(1)
    for kind in ("Mineral", "Flora", "Fauna"):
        if m := re.search(rf"^{kind}:\s*(.+)$", text, re.M):
            fields[f"{kind} Edicts"] = m.group(1).strip()
    return fields


def govbot_planet(text):
    """Return the planet the govbot dialog names, or None if OCR missed the title.

    The title reads "<PLANET> GOVBOT - CITIZENSHIP". It is not always legible, so
    a missing title is not an error; only a title naming a *different* planet is.
    """
    m = re.search(r"^(.+?)\s+GOVBOT", text, re.M)
    # OCR renders roman "I" as a lowercase L or a pipe here too
    return re.sub(r"[l|]", "I", m.group(1)).strip().upper() if m else None


def read_sector(content, sector):
    """Parse an existing sector section back into its parts."""
    data = {"starbase": False, "fields": {}, "connections": [], "planets": {}}
    m = re.search(rf"^### {re.escape(sector)}$(.*?)(?=^### |\Z)", content, re.M | re.S)
    if not m:
        return data
    body = m.group(1)
    data["starbase"] = bool(re.search(r"^- Starbase$", body, re.M))
    data["fields"] = dict(re.findall(r"^- (.+?):\s*(.+?)\s*$", body, re.M))
    if block := re.search(r"^- Sector Connections$((?:\n  - .+)*)", body, re.M):
        data["connections"] = re.findall(r"^  - (.+?)\s*$", block.group(1), re.M)
    if block := re.search(r"^- Planets$((?:\n  +- .+)*)", body, re.M):
        current = None
        for line in block.group(1).splitlines():
            if pm := re.match(r"^  - (.+?)\s*$", line):
                current = pm.group(1)
                data["planets"][current] = {}
            elif fm := re.match(r"^    - (.+?):\s*(.+?)\s*$", line):
                if current:
                    data["planets"][current][fm.group(1)] = fm.group(2)
    return data


def format_entry(sector, data):
    """Render a sector section: an Information block, then a Connections block.

    Planets live under Connections because reaching one means taking a portal,
    the same as reaching a neighbouring sector.
    """
    lines = [f"### {sector}"]

    fields = data["fields"]
    info = [f"- {k}: {fields[k]}" for k in SECTOR_FIELDS if k in fields]
    info += [f"- {k}: {v}" for k, v in fields.items() if k not in SECTOR_FIELDS]
    if info:
        lines += ["", f"#### {sector} - Information", ""] + info

    conn = ["- Starbase"] if data["starbase"] else []
    if data["connections"]:
        conn.append("- Sector Connections")
        conn += [f"  - {c}" for c in data["connections"]]
    if data["planets"]:
        conn.append("- Planets")
        for name in sorted(data["planets"]):
            conn.append(f"  - {name}")
            planet_fields = data["planets"][name]
            known = [k for k in PLANET_FIELDS if k in planet_fields]
            conn += [f"    - {k}: {planet_fields[k]}" for k in known]
            conn += [f"    - {k}: {v}" for k, v in planet_fields.items()
                     if k not in PLANET_FIELDS]
    if conn:
        lines += ["", f"#### {sector} - Connections", ""] + conn

    return "\n".join(lines) + "\n"


def upsert(md_path, sector, entry):
    """Replace the sector's section if present, else append it."""
    content = md_path.read_text() if md_path.exists() else "# Stars Reach - Sectors\n\n## Sectors\n"
    pattern = re.compile(rf"^### {re.escape(sector)}$.*?(?=^### |\Z)", re.M | re.S)
    if pattern.search(content):
        content = pattern.sub(lambda _: entry + "\n", content)
    else:
        content = content.rstrip() + "\n\n" + entry
    md_path.write_text(content.rstrip() + "\n")


def node_id(name):
    return re.sub(r"\W+", "_", name)


def render_graph(md_path):
    """Rewrite the Mermaid graph from the connections listed in the sector sections."""
    content = md_path.read_text()
    edges, nodes = set(), set()
    for sector, body in re.findall(r"^### (.+?)\s*$(.*?)(?=^### |\Z)", content, re.M | re.S):
        nodes.add(sector)
        block = re.search(r"^- Sector Connections$((?:\n  - .+)*)", body, re.M)
        for other in re.findall(r"^  - (.+?)\s*$", block.group(1), re.M) if block else []:
            nodes.add(other)
            # connections are symmetric, so an unordered pair deduplicates both directions
            edges.add(tuple(sorted((sector, other))))

    lines = ["## Connections", "", "```mermaid", "graph LR"]
    lines += [f'  {node_id(n)}["{n}"]' for n in sorted(nodes)]
    lines += [f"  {node_id(a)} --- {node_id(b)}" for a, b in sorted(edges)]
    lines += ["```", ""]
    graph = "\n".join(lines) + "\n"

    existing = re.compile(r"^## Connections$.*?(?=^## )", re.M | re.S)
    if existing.search(content):
        content = existing.sub(lambda _: graph, content)
    else:
        content = content.replace("## Sectors", graph + "## Sectors", 1)
    md_path.write_text(content)


def locate(screenshot):
    """Derive (kind, sector, planet) from the screenshot's path."""
    kind = screenshot.parent.name
    if kind in ("map", "ecology"):
        return kind, screenshot.parent.parent.name, None
    if kind == "govbot":
        sector, planet_name = screenshot.parent.parent.parent.name, screenshot.parent.parent.name
        # Planets are named "<Sector> <designator>", so this also catches a
        # screenshot filed under the sector instead of under one of its planets
        if not planet_name.startswith(sector):
            sys.exit(f"{planet_name!r} is not a planet of {sector!r}; expected "
                     f"<Sector>/<Planet>/govbot/, for example Kai/Kai I/govbot/")
        return kind, sector, planet_name
    sys.exit(f"Unknown screenshot type {kind!r}, expected map, ecology or govbot in the path")


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("screenshot", type=Path)
    p.add_argument("--file", type=Path, default=Path(__file__).parent.parent / "Sectors.md")
    p.add_argument("--dry-run", action="store_true", help="print the entry, write nothing")
    args = p.parse_args()

    if not args.screenshot.is_file():
        sys.exit(f"No such screenshot: {args.screenshot}")

    kind, sector, planet_name = locate(args.screenshot)
    text = ocr(args.screenshot)
    content = args.file.read_text() if args.file.exists() else ""
    data = read_sector(content, sector)

    if kind == "map":
        starbase, connections, planets = classify_map(text, sector)
        if not (connections or planets):
            sys.exit(f"No waypoints recognised in {args.screenshot}")
        # Connections and planets are only ever added: portals are not always
        # open, and a capture taken while one was closed must not delete it.
        # This also makes the result independent of the order captures are read.
        data["starbase"] = data["starbase"] or starbase
        data["connections"] = sorted(set(data["connections"]) | set(connections))
        for name in planets:
            data["planets"].setdefault(name, {})
    else:
        if kind == "govbot" and (shown := govbot_planet(text)):
            if shown != planet_name.upper():
                sys.exit(f"{args.screenshot} shows {shown}, but sits in a directory "
                         f"for {planet_name!r} - move it to the right planet")
        fields = parse_ecology(text) if kind == "ecology" else parse_govbot(text)
        if not fields:
            sys.exit(f"No {kind} data recognised in {args.screenshot}")
        if kind == "ecology":
            data["fields"].update(fields)
        else:
            data["planets"].setdefault(planet_name, {}).update(fields)

    entry = format_entry(sector, data)
    print(entry)
    if not args.dry_run:
        upsert(args.file, sector, entry)
        render_graph(args.file)
        print(f"Wrote {args.file}")


if __name__ == "__main__":
    main()
