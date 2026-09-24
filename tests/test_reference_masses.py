"""Recompute every entry's masses from its parsed composition and compare with UNIMOD.

The element and isotope masses come from an independent table frozen from pyteomics
(NIST); see tests/reference/generate_element_masses.py. A mismatch means the
composition parser (or monosaccharide expansion) lost or misread a token.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from unimodpy import UnimodDatabase

_ELEMENTS: dict[str, dict[str, float]] = json.loads(
    (Path(__file__).parent / "reference" / "element_masses.json").read_text()
)["elements"]

# UNIMOD states 6 decimals, but its atomic mass table is not the same AME release as
# NIST's: Hg (UNIMOD:291) differs by 2.6e-5 Da.
MONO_TOL = 5e-5
AVG_TOL = 0.01  # UNIMOD's atomic-weight table is older than the NIST one used here


def _mass(composition: dict[str, int], kind: str) -> float:
    return sum(_ELEMENTS[token][kind] * count for token, count in composition.items())


def test_delta_masses_match_composition(db: UnimodDatabase) -> None:
    mismatches = []
    checked = 0
    for e in db:
        if e.delta_composition is None:
            continue
        checked += 1
        mono, avg = _mass(e.dict_composition, "mono"), _mass(e.dict_composition, "avg")
        if abs(mono - e.delta_mono_mass) > MONO_TOL or abs(avg - e.delta_avge_mass) > AVG_TOL:
            mismatches.append((e.id, e.delta_composition, e.delta_mono_mass, round(mono, 6)))
    assert checked > 1500
    assert mismatches == []


def test_neutral_loss_masses_match_composition(db: UnimodDatabase) -> None:
    mismatches = []
    checked = 0
    for e in db:
        for spec in e.specificities:
            for nl in spec.neutral_losses:
                checked += 1
                mono, avg = _mass(nl.dict_composition, "mono"), _mass(nl.dict_composition, "avg")
                if abs(mono - nl.mono_mass) > MONO_TOL or abs(avg - nl.avge_mass) > AVG_TOL:
                    mismatches.append((e.id, nl.composition, nl.mono_mass, round(mono, 6)))
    assert checked > 100
    assert mismatches == []


@pytest.mark.parametrize(
    ("unimod_id", "mono"),
    [
        (1, 42.010565),  # Acetyl, H(2) C(2) O
        (21, 79.966331),  # Phospho, H O(3) P
        (43, 203.079373),  # HexNAc, monosaccharide expansion
        (259, 8.014199),  # Label:13C(6)15N(2)
    ],
)
def test_spot_values(db: UnimodDatabase, unimod_id: int, mono: float) -> None:
    assert _mass(db[unimod_id].dict_composition, "mono") == pytest.approx(mono, abs=MONO_TOL)
