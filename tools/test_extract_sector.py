"""Self-check: python3 test_extract_sector.py"""

from pathlib import Path
from tempfile import TemporaryDirectory

from extract_sector import (
    classify_map,
    format_entry,
    parse_ecology,
    parse_govbot,
    govbot_planet,
    locate,
    planet,
    read_sector,
    render_graph,
    upsert,
)

MAP_OCR = """
COHUFOTAG
WAYPOINTS
Current location (588, 162, 389)
Cohufotag II (245, 87, 321)
Letiemopas Sector (483, 69, 929)
Starbase (594, 150, 391)
Cohufotag I (355, 131, 222)
Public event (367, 186, 336)
Star type
"""

# Verbatim from tesseract on media/screenshots/Kai/ecology/image.png
ECOLOGY_OCR = """
PLANET ECOLOGY — SUMMARY
Overall Planet Health: 96.0%
Servitor Edicts: Copper, Iron, Vesuvianite, Nickel, Tungsten
Minerals — Quantity 70% - Diversity 100% VIEW DETAILS
Flora — Quantity 100% - Diversity 100% VIEW DETAILS
Fauna — Quantity 100% - Diversity 100% VIEW DETAILS
"""

# Verbatim from tesseract on media/screenshots/Kai/Kai I/govbot/image.png
GOVBOT_OCR = """
KAI | GOVBOT — CITIZENSHIP
Welcome to Kai I!
Current Mayor: leti Moonlighter
Population: 178
Current Edicts:
Mineral: Garnet, Gold, Salt, Amethyst, Bismuth
Flora: None
Fauna: None
Would you like to become a citizen here?
"""

starbase, connections, planets = classify_map(MAP_OCR, "Cohufotag")
assert starbase is True
assert connections == ["Letiemopas"], connections
assert planets == ["Cohufotag I", "Cohufotag II"], planets

# OCR mangles roman numerals after short sector names
assert planet("Kail", "Kai") == "Kai I"
assert planet("Kai Il", "Kai") == "Kai II"
assert planet("Kai Ill-C", "Kai") == "Kai III-C"
assert planet("eB & Kai IV-C", "Kai") == "Kai IV-C"
assert planet("Owiis Nuheuno |", "Owiis Nuheuno") == "Owiis Nuheuno I"
assert planet("Letiemopas III-B", "Letiemopas") == "Letiemopas III-B"
assert planet("Kai Sector", "Kai") is None
assert planet("Public event", "Kai") is None

# The whole ecology dialog describes the sector, despite its "PLANET" title
assert parse_ecology(ECOLOGY_OCR) == {
    "Servitor Edicts": "Copper, Iron, Vesuvianite, Nickel, Tungsten",
    "Health": "96.0%",
    "Minerals": "Quantity 70%, Diversity 100%",
    "Flora": "Quantity 100%, Diversity 100%",
    "Fauna": "Quantity 100%, Diversity 100%",
}, parse_ecology(ECOLOGY_OCR)
# A Guardian edict line is picked up without a code change
assert "Guardian Edicts" in parse_ecology("Guardian Edicts: Copper\n")

# locate() derives kind, sector and planet from the path
assert locate(Path("media/screenshots/Kai/map/image.png")) == ("map", "Kai", None)
assert locate(Path("media/screenshots/Kai/ecology/image.png")) == ("ecology", "Kai", None)
assert locate(Path("media/screenshots/Kai/Kai I/govbot/image.png")) == ("govbot", "Kai", "Kai I")
# a govbot screenshot filed under the sector instead of a planet must not invent a sector
try:
    locate(Path("media/screenshots/Kai/govbot/image.png"))
    raise AssertionError("misfiled govbot screenshot was accepted")
except SystemExit:
    pass

# The govbot dialog names its own planet, which catches a misfiled screenshot
assert govbot_planet(GOVBOT_OCR) == "KAI I", govbot_planet(GOVBOT_OCR)
assert govbot_planet("TAPINEXE PAVI Il GOVBOT - CITIZENSHIP\n") == "TAPINEXE PAVI II"
assert govbot_planet("no title here\n") is None, "a missing title must not be an error"

gov = parse_govbot(GOVBOT_OCR)
assert "Mayor" not in gov, "the mayor's name is deliberately not extracted"
assert gov["Population"] == "178"
assert gov["Mineral Edicts"] == "Garnet, Gold, Salt, Amethyst, Bismuth"
assert gov["Flora Edicts"] == "None" and gov["Fauna Edicts"] == "None"
assert "Servitor Edicts" not in gov, "govbot data must not reach the sector level"

entry = format_entry("Cohufotag", {
    "starbase": True,
    "fields": {"Servitor Edicts": "Copper, Iron", "Health": "96.0%"},
    "connections": ["Letiemopas"],
    "planets": {"Cohufotag I": {"Population": "178"}},
})
assert entry == (
    "### Cohufotag\n\n"
    "#### Cohufotag - Information\n\n"
    "- Health: 96.0%\n"
    "- Servitor Edicts: Copper, Iron\n\n"
    "#### Cohufotag - Connections\n\n"
    "- Starbase\n"
    "- Sector Connections\n  - Letiemopas\n"
    "- Planets\n  - Cohufotag I\n"
    "    - Population: 178\n"
), repr(entry)

# A sector without ecology data must not produce an empty Information block
bare = format_entry("Kai", {"starbase": True, "fields": {},
                            "connections": ["Owiis Nuheuno"], "planets": {}})
assert "Information" not in bare, bare
assert bare == "### Kai\n\n#### Kai - Connections\n\n- Starbase\n- Sector Connections\n  - Owiis Nuheuno\n", repr(bare)

# read_sector is the inverse of format_entry, so details survive a rewrite
back = read_sector("## Sectors\n\n" + entry, "Cohufotag")
assert back["starbase"] is True
assert back["fields"] == {"Servitor Edicts": "Copper, Iron", "Health": "96.0%"}
assert back["connections"] == ["Letiemopas"]
assert back["planets"] == {"Cohufotag I": {"Population": "178"}}
assert format_entry("Cohufotag", back) == entry, "round trip changed the entry"

with TemporaryDirectory() as d:
    md = Path(d) / "Sectors.md"
    md.write_text("# Stars Reach - Sectors\n\n## Sectors\n\n" + entry)

    # A later map run must not wipe the planet details a govbot run wrote
    data = read_sector(md.read_text(), "Cohufotag")
    data["starbase"], data["connections"] = True, ["Letiemopas", "Owiis Nuheuno"]
    for name in ["Cohufotag I", "Cohufotag II"]:
        data["planets"].setdefault(name, {})
    upsert(md, "Cohufotag", format_entry("Cohufotag", data))
    out = md.read_text()
    assert "    - Population: 178" in out, "map run dropped the planet details"
    assert "- Servitor Edicts: Copper, Iron" in out, "map run dropped the sector edicts"
    assert "- Health: 96.0%" in out, "map run dropped the sector ecology data"
    assert "  - Cohufotag II" in out, "map run did not add the new planet"

    # The portals to the two variable planets are not always open, so a map run
    # that only sees the fixed ones must not delete the others
    data = read_sector(out, "Cohufotag")
    data["planets"].setdefault("Cohufotag III-B", {})
    upsert(md, "Cohufotag", format_entry("Cohufotag", data))
    seen_without_portals = read_sector(md.read_text(), "Cohufotag")
    seen_without_portals["planets"].setdefault("Cohufotag I", {})
    upsert(md, "Cohufotag", format_entry("Cohufotag", seen_without_portals))
    assert "  - Cohufotag III-B" in md.read_text(), "closed portal deleted a known planet"

    # Sector portals open and close too, so a later capture that no longer shows
    # a neighbour must not drop it either
    data = read_sector(md.read_text(), "Cohufotag")
    data["connections"] = sorted(set(data["connections"]) | {"Letiemopas"})
    upsert(md, "Cohufotag", format_entry("Cohufotag", data))
    assert "  - Owiis Nuheuno" in md.read_text(), "closed portal deleted a known connection"

with TemporaryDirectory() as d:
    md = Path(d) / "Sectors.md"
    md.write_text(
        "# Stars Reach - Sectors\n\n## Sectors\n\n"
        "### Kai\n\n- Sector Connections\n  - Owiis Nuheuno\n- Planets\n  - Kai I\n"
        "    - Mineral Edicts: Gold\n\n"
        "### Owiis Nuheuno\n\n- Sector Connections\n  - Kai\n"
    )
    render_graph(md)
    out = md.read_text()
    assert out.count("Kai --- Owiis_Nuheuno") == 1, "symmetric connection not deduplicated"
    assert '  Owiis_Nuheuno["Owiis Nuheuno"]' in out
    graph = out.split("## Sectors")[0]
    assert "Kai I" not in graph and "Gold" not in graph, "planet detail leaked into the graph"
    assert out.index("## Connections") < out.index("## Sectors")
    render_graph(md)
    assert md.read_text() == out, "render_graph is not idempotent"

print("ok")
