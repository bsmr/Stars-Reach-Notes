"""Self-check: python3 test_extract_sector.py"""

from pathlib import Path
from tempfile import TemporaryDirectory

from extract_sector import classify, format_entry, planet, render_graph, upsert

OCR = """
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

starbase, connections, planets = classify(OCR, "Cohufotag")
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

entry = format_entry("Cohufotag", starbase, connections, planets)
assert entry == (
    "### Cohufotag\n\n"
    "- Starbase\n"
    "- Sector Connections\n  - Letiemopas\n"
    "- Planets\n  - Cohufotag I\n  - Cohufotag II\n"
), repr(entry)

with TemporaryDirectory() as d:
    md = Path(d) / "Sectors.md"
    md.write_text("# Stars Reach - Sectors\n\n## Sectors\n\n### Cohufotag\n\n- Planets\n  - old\n\n### Zzz\n\n- Starbase\n")
    upsert(md, "Cohufotag", entry)
    out = md.read_text()
    assert "- old" not in out
    assert out.count("### Cohufotag") == 1
    assert "### Zzz" in out and out.index("### Cohufotag") < out.index("### Zzz")
    assert "\n\n### Zzz" in out, "replacement ate the blank line between sections"
    upsert(md, "Newsec", "### Newsec\n\n- Starbase\n")
    assert md.read_text().rstrip().endswith("### Newsec\n\n- Starbase")

with TemporaryDirectory() as d:
    md = Path(d) / "Sectors.md"
    md.write_text(
        "# Stars Reach - Sectors\n\n## Sectors\n\n"
        "### Kai\n\n- Sector Connections\n  - Owiis Nuheuno\n- Planets\n  - Kai I\n\n"
        "### Owiis Nuheuno\n\n- Sector Connections\n  - Kai\n"
    )
    render_graph(md)
    out = md.read_text()
    assert out.count("Kai --- Owiis_Nuheuno") == 1, "symmetric connection not deduplicated"
    assert '  Owiis_Nuheuno["Owiis Nuheuno"]' in out
    assert "  - Kai I" not in out.split("## Sectors")[0], "planet leaked into the graph"
    assert out.index("## Connections") < out.index("## Sectors")
    render_graph(md)
    assert md.read_text() == out, "render_graph is not idempotent"

print("ok")
