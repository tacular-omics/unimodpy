"""Adding ``position`` to a ``search_mass`` query must narrow the result set, never widen it.

Stated as a subset invariant over a sweep of queries, because the failure mode is silent:
a filter that adds hits gives a wrong answer the caller has no reason to doubt.
"""

from __future__ import annotations

import pytest

from unimodpy import UnimodDatabase
from unimodpy._mass import POSITIONS

_DELTAS = (0.984016, 15.994915, 42.010565, 79.966331, 28.031300, 114.042927, -17.026549, 226.077598, 57.021464)
_SITES = (None, "S", "T", "Y", "K", "C", "N", "Q", "M", "P", "G", "A", "N-term", "C-term", "ST", "STY")


def _ids(hits) -> set[int]:
    return {entry.id for entry, _ in hits}


@pytest.mark.parametrize("position", POSITIONS)
def test_position_only_removes_hits(db: UnimodDatabase, position: str) -> None:
    widened = []
    for delta in _DELTAS:
        for site in _SITES:
            without = _ids(db.search_mass(delta, tolerance=0.02, site=site))
            with_position = _ids(db.search_mass(delta, tolerance=0.02, site=site, position=position))
            extra = with_position - without
            if extra:
                widened.append((delta, site, sorted(extra)[:5]))
    assert not widened, f"position={position!r} added hits for {len(widened)} queries: {widened[:5]}"


def test_a_terminus_specificity_matches_a_residue_query_without_a_position(db: UnimodDatabase) -> None:
    """Acetyl is ``N-term @ Protein N-term``: any residue at the protein N-terminus, alanine among them."""
    names = [entry.name for entry, _ in db.search_mass(42.010565, site="A")]
    assert "Acetyl" in names
    assert "Acetyl" in [entry.name for entry, _ in db.search_mass(42.010565, site="A", position="protein n-term")]
    assert "Acetyl" not in [entry.name for entry, _ in db.search_mass(42.010565, site="A", position="anywhere")]
