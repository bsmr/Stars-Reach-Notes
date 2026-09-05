#!/usr/bin/env python3
"""Extract sector info from a Stars Reach map screenshot into Sectors.md.

Usage: extract_sector.py <screenshot.png> [--sector NAME] [--file Sectors.md] [--dry-run]

The sector name defaults to the sector directory in the path
(media/screenshots/<Sector>/map/image.png).
"""

import argparse
import re
import sys
from pathlib import Path

import pytesseract
from PIL import Image

# Waypoint panel lines look like: "Cohufotag II (245, 87, 321)"
WAYPOINT = re.compile(r"^\s*(.+?)\s*\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\)\s*$")


def extract(image_path, sector):
    """OCR the screenshot and classify its waypoint entries."""
    return classify(pytesseract.image_to_string(Image.open(image_path)), sector)


def classify(text, sector):
    """Split OCR'd waypoint lines into starbase flag, connections and planets."""
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


def format_entry(sector, starbase, connections, planets):
    lines = [f"### {sector}", ""]
    if starbase:
        lines.append("- Starbase")
    if connections:
        lines.append("- Sector Connections")
        lines += [f"  - {c}" for c in connections]
    if planets:
        lines.append("- Planets")
        lines += [f"  - {p}" for p in planets]
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


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("screenshot", type=Path)
    p.add_argument("--sector", help="sector name (default: the <Sector> directory in the path)")
    p.add_argument("--file", type=Path, default=Path(__file__).parent.parent / "Sectors.md")
    p.add_argument("--dry-run", action="store_true", help="print the entry, write nothing")
    args = p.parse_args()

    if not args.screenshot.is_file():
        sys.exit(f"No such screenshot: {args.screenshot}")

    sector = args.sector or args.screenshot.parent.parent.name
    starbase, connections, planets = extract(args.screenshot, sector)
    if not (connections or planets):
        sys.exit(f"No waypoints recognised in {args.screenshot} - is Tesseract reading the panel?")

    entry = format_entry(sector, starbase, connections, planets)
    print(entry)
    if not args.dry_run:
        upsert(args.file, sector, entry)
        render_graph(args.file)
        print(f"Wrote {args.file}")


if __name__ == "__main__":
    main()
