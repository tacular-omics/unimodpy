#!/usr/bin/env python3
"""Export the bundled UNIMOD database to JSON for the GitHub Pages browser."""
import json
from pathlib import Path

from unimodpy.server.dashboard import dashboard_entries

entries = dashboard_entries()

out = Path("docs/data.json")
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(entries, separators=(",", ":")))
print(f"Exported {len(entries)} entries → {out}")
