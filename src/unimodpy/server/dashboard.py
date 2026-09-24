"""Build the data payload consumed by the static dashboard."""

from __future__ import annotations

from typing import TypedDict

import unimodpy
from unimodpy.database import UnimodDatabase


class DashboardSpecificity(TypedDict):
    spec_num: int
    site: str
    position: str
    classification: str


class DashboardEntry(TypedDict):
    id: int
    name: str
    definition: str
    synonyms: list[str]
    delta_mono_mass: float | None
    delta_avge_mass: float | None
    proforma_formula: str | None
    comment: str | None
    approved: bool | None
    specificities: list[DashboardSpecificity]


def dashboard_entries(db: UnimodDatabase | None = None) -> list[DashboardEntry]:
    """Dashboard rows for every entry except the root node; loads the bundled database if *db* is omitted."""
    if db is None:
        db = unimodpy.load()
    entries: list[DashboardEntry] = []
    for entry in db:
        if entry.id == 0:
            continue
        entries.append(
            {
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
            }
        )
    return entries
