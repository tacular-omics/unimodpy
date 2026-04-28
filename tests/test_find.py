from __future__ import annotations

import pytest

import unimodpy
from unimodpy.database import UnimodDatabase


@pytest.fixture(scope="module")
def db() -> UnimodDatabase:
    return unimodpy.load()


def test_find_no_filters_returns_all(db: UnimodDatabase) -> None:
    assert len(db.find()) == len(db)


def test_find_text(db: UnimodDatabase) -> None:
    results = db.find(text="phospho", limit=5)
    assert 0 < len(results) <= 5
    for e in results:
        hay = e.name.lower() + " " + e.definition.lower() + " " + " ".join(s.lower() for s in e.synonyms)
        assert "phospho" in hay


def test_find_mass_range_mono(db: UnimodDatabase) -> None:
    results = db.find(mass_min=79.96, mass_max=79.98, mass_type="mono")
    assert len(results) > 0
    for e in results:
        assert e.delta_mono_mass is not None
        assert 79.96 <= e.delta_mono_mass <= 79.98


def test_find_mass_skips_none(db: UnimodDatabase) -> None:
    results = db.find(mass_min=-1e9, mass_max=1e9, mass_type="mono")
    assert all(e.delta_mono_mass is not None for e in results)


def test_find_residues_phospho_sty(db: UnimodDatabase) -> None:
    results = db.find(
        mass_min=79.96,
        mass_max=79.98,
        residues=["S", "T", "Y"],
    )
    assert len(results) > 0
    names = {e.name.lower() for e in results}
    assert "phospho" in names


def test_find_position_invalid_returns_empty(db: UnimodDatabase) -> None:
    assert db.find(position="NOPE") == []


def test_find_classification_invalid_returns_empty(db: UnimodDatabase) -> None:
    assert db.find(classification="NOPE") == []


def test_find_classification_n_linked_glyco(db: UnimodDatabase) -> None:
    results = db.find(classification="N-linked glycosylation", limit=10)
    assert len(results) > 0
    for e in results:
        non_hidden = [s for s in e.specificities if not s.hidden]
        assert any(str(s.classification) == "N-linked glycosylation" for s in non_hidden)


def test_find_has_neutral_loss_true(db: UnimodDatabase) -> None:
    results = db.find(has_neutral_loss=True, limit=10)
    assert len(results) > 0
    for e in results:
        non_hidden = [s for s in e.specificities if not s.hidden]
        assert any(s.neutral_losses for s in non_hidden)


def test_find_limit(db: UnimodDatabase) -> None:
    assert len(db.find(limit=3)) == 3


def test_find_combined_excludes(db: UnimodDatabase) -> None:
    # Phospho mass on residue C should give few/no results.
    results = db.find(mass_min=79.96, mass_max=79.98, residues=["C"])
    # Either 0 or only entries that genuinely list a Cys site for this mass.
    for e in results:
        non_hidden = [s for s in e.specificities if not s.hidden]
        assert any(str(s.site) == "C" for s in non_hidden)
