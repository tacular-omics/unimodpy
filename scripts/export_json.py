#!/usr/bin/env python3
"""Export the bundled UNIMOD database to JSON for the GitHub Pages browser."""
import json
from pathlib import Path

import unimodpy
from unimodpy.server.dashboard import dashboard_entries

ROOT = Path(__file__).parent.parent
OBO_PATH = ROOT / "src" / "unimodpy" / "data" / "UNIMOD.obo"
OUT_PATH = ROOT / "docs" / "data.json"
META_PATH = ROOT / "docs" / "meta.json"


def export() -> None:
    entries = dashboard_entries()

    OUT_PATH.parent.mkdir(exist_ok=True)
    OUT_PATH.write_text(json.dumps(entries, separators=(",", ":")))
    print(f"Exported {len(entries)} entries → {OUT_PATH}")

    # Package version for the page footer (the Vercel app serves /api/health instead).
    META_PATH.write_text(json.dumps({"package": "unimodpy", "version": unimodpy.__version__}))
    print(f"Wrote {META_PATH}")


if __name__ == "__main__":
    export()
