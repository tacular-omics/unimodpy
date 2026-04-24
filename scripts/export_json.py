#!/usr/bin/env python3
"""Export the bundled UNIMOD database to JSON for the GitHub Pages browser."""
import json
from pathlib import Path

import unimodpy

db = unimodpy.load()

entries = []
for entry in db:
    if entry.id == 0:
        continue
    entries.append({
        "id": entry.id,
        "name": entry.name,
        "definition": entry.definition,
        "synonyms": list(entry.synonyms),
        "delta_mono_mass": entry.delta_mono_mass,
        "delta_avge_mass": entry.delta_avge_mass,
        "proforma_formula": entry.proforma_formula,
        "comment": entry.comment,
        "approved": entry.approved,
        "specificities": [
            {
                "spec_num": s.spec_num,
                "site": str(s.site),
                "position": str(s.position),
                "classification": str(s.classification),
            }
            for s in entry.specificities
        ],
    })

out = Path("docs/data.json")
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(entries, separators=(",", ":")))
print(f"Exported {len(entries)} entries → {out}")
