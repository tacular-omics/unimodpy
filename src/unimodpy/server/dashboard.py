"""Build the data payload consumed by the static dashboard."""

from __future__ import annotations

import unimodpy


def dashboard_entries() -> list[dict]:
    db = unimodpy.load()
    entries: list[dict] = []
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
    return entries
