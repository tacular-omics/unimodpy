"""Regression tests for the 1.0 pre-release fix round (shared with psimodpy / uniprotptmpy)."""

from __future__ import annotations

import warnings
from pathlib import Path

import pytest

from unimodpy import UnimodDatabase, UnimodParseError, load
from unimodpy._download import UNIMOD_OBO_URL
from unimodpy._formula import parse_delta_composition


@pytest.mark.parametrize("bad", ["1_0", "UNIMOD:1_0", "+1", "-1", "١", "UNIMOD:١", "1.0", " 1 0 "])
def test_get_by_id_rejects_non_ascii_digit_strings(db: UnimodDatabase, bad: str) -> None:
    # int() accepts "1_0" (-> 10), "+1" and Arabic-Indic digits; ids must be plain ASCII digits.
    assert db.get_by_id(bad) is None
    assert bad not in db or db.get_by_name(bad) is not None


def test_get_by_id_still_accepts_valid_strings(db: UnimodDatabase) -> None:
    assert db.get_by_id("21") is db.get_by_id(21)
    assert db.get_by_id(" unimod:21 ") is db.get_by_id(21)


@pytest.mark.parametrize("bad", [None, 1, 1.5, b"Phospho", ["Phospho"]])
def test_get_by_name_non_str_returns_none(db: UnimodDatabase, bad: object) -> None:
    assert db.get_by_name(bad) is None  # type: ignore[arg-type]


@pytest.mark.parametrize("bad", [None, 1, b"phospho"])
def test_search_non_str_returns_empty(db: UnimodDatabase, bad: object) -> None:
    assert db.search(bad) == []  # type: ignore[arg-type]


def test_bundled_obo_loads_without_warnings() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        db = load()
    assert len(db) == 1561


def test_download_url_is_https() -> None:
    assert UNIMOD_OBO_URL.startswith("https://")


def test_load_source_and_refresh_is_an_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("unimodpy._download.download", lambda *a, **k: pytest.fail("must not download"))
    with pytest.raises(ValueError, match="pass either source or refresh=True, not both"):
        load(tmp_path / "x.obo", refresh=True)


def test_entry_accession(db: UnimodDatabase) -> None:
    assert db.get_by_id(21).accession == "UNIMOD:21"  # type: ignore[union-attr]
    assert db.get_by_id(0).accession == "UNIMOD:0"  # type: ignore[union-attr]


@pytest.mark.parametrize("bad", ["H(2", "H(x)", "Foo(2)", "Foo", "H(2)x", "H()", "Xx(1)", "13Foo", "(2)"])
def test_parse_delta_composition_malformed_raises(bad: str) -> None:
    with pytest.raises(UnimodParseError):
        parse_delta_composition(bad)


def test_parse_delta_composition_valid_still_parses() -> None:
    assert parse_delta_composition("H(2) C(2) O") == {"H": 2, "C": 2, "O": 1}
    assert parse_delta_composition("2H(8) 13C(3) H(-8)") == {"2H": 8, "13C": 3, "H": -8}
    assert parse_delta_composition("Hex(1) Water") == {"C": 6, "H": 12, "O": 6}
    assert parse_delta_composition("0") == {}
    assert parse_delta_composition("") == {}


def _unknown_token_entry():
    from unimodpy import UnimodEntry

    return UnimodEntry(id=99999, name="NewSugar", definition="", synonyms=(), delta_composition="H(2) Foo(1)")


def test_unknown_composition_token_gives_none_and_warns() -> None:
    entry = _unknown_token_entry()
    with pytest.warns(UserWarning, match=r"UNIMOD:99999.*Foo"):
        assert entry.dict_composition is None
    with pytest.warns(UserWarning, match=r"UNIMOD:99999.*Foo") as record:
        assert entry.proforma_formula is None
    assert len(record) == 1, "one warning per property access"
    with pytest.raises(UnimodParseError):
        parse_delta_composition("H(2) Foo(1)")


def test_server_and_dashboard_survive_unknown_composition_token() -> None:
    pytest.importorskip("fastapi")
    from unimodpy.server.dashboard import dashboard_entries
    from unimodpy.server.models import to_unimod_entry, to_unimod_summary

    entry = _unknown_token_entry()
    with pytest.warns(UserWarning):
        wire = to_unimod_entry(entry)
    assert wire.proforma_formula is None and wire.dict_composition is None
    with pytest.warns(UserWarning):
        assert to_unimod_summary(entry).proforma_formula is None
    with pytest.warns(UserWarning):
        rows = dashboard_entries(UnimodDatabase([entry]))
    assert rows[0]["proforma_formula"] is None
