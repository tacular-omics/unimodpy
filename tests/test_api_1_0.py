"""Shared 1.0 API contract (psimodpy / unimodpy / uniprotptmpy)."""

from __future__ import annotations

import tomllib
import typing
import warnings
from pathlib import Path

import pytest

import unimodpy
from unimodpy import (
    Classification,
    NeutralLoss,
    Position,
    Site,
    UnimodDatabase,
    UnimodEntry,
    UnimodError,
    UnimodParseError,
    download,
    load,
    parse_obo,
    write_obo,
)

_TERM = """[Term]
id: UNIMOD:{id}
name: {name}
def: "A modification." [PMID:1]
xref: delta_composition "H(2) C(2) O"
xref: spec_1_group "1"
xref: spec_1_hidden "0"
xref: spec_1_site "{site}"
xref: spec_1_position "{position}"
xref: spec_1_classification "{classification}"

"""


def _term(id: int = 1, name: str = "Acetyl", site="K", position="Anywhere", classification="Multiple") -> str:
    return _TERM.format(id=id, name=name, site=site, position=position, classification=classification)


def _write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "t.obo"
    p.write_text("format-version: 1.4\n\n" + text, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


def test_errors_exported_and_hierarchy() -> None:
    assert issubclass(UnimodParseError, UnimodError)
    assert issubclass(UnimodParseError, ValueError)
    assert issubclass(UnimodError, Exception)
    assert {"UnimodError", "UnimodParseError", "__version__"} <= set(unimodpy.__all__)
    from unimodpy.errors import UnimodError as E1
    from unimodpy.errors import UnimodParseError as E2

    assert E1 is UnimodError and E2 is UnimodParseError


@pytest.mark.parametrize(
    ("field", "value", "enum"),
    [
        ("site", "Z", Site),
        ("position", "Somewhere new", Position),
        ("classification", "Brand new class", Classification),
    ],
)
def test_unknown_enum_value_keeps_raw_and_warns(tmp_path: Path, field: str, value: str, enum: type) -> None:
    p = _write(tmp_path, _term(**{field: value}))
    with pytest.warns(UserWarning, match=value):
        db = parse_obo(p)
    spec = db[1].specificities[0]
    raw = getattr(spec, field)
    assert raw == value
    assert type(raw) is str and not isinstance(raw, enum)
    # Known values are still enum members.
    others = {"site", "position", "classification"} - {field}
    for other in others:
        assert isinstance(getattr(spec, other), (Site, Position, Classification))


def test_unknown_enum_round_trips_through_writer(tmp_path: Path) -> None:
    p = _write(tmp_path, _term(site="Z"))
    with pytest.warns(UserWarning):
        db = parse_obo(p)
    out = write_obo(db, tmp_path / "out.obo")
    with pytest.warns(UserWarning):
        db2 = parse_obo(out)
    assert db2[1] == db[1]


@pytest.mark.parametrize("drop", ["id", "name"])
def test_block_missing_id_or_name_is_skipped_with_warning(tmp_path: Path, drop: str) -> None:
    bad = "\n".join(line for line in _term(id=2, name="Bad").splitlines() if not line.startswith(f"{drop}:")) + "\n\n"
    p = _write(tmp_path, _term() + bad + _term(id=3, name="Other"))
    with pytest.warns(UserWarning, match=f"missing '{drop}'"):
        db = parse_obo(p)
    assert len(db) == 2
    assert [e.id for e in db] == [1, 3]


def test_malformed_id_raises_parse_error_with_line_hint(tmp_path: Path) -> None:
    p = _write(tmp_path, _term() + _term(id=2).replace("UNIMOD:2", "UNIMOD:abc"))
    with pytest.raises(UnimodParseError, match=r"line \d+") as exc:
        parse_obo(p)
    assert isinstance(exc.value, ValueError)


def test_malformed_mass_raises_parse_error(tmp_path: Path) -> None:
    text = _term().replace('xref: delta_composition "H(2) C(2) O"', 'xref: delta_mono_mass "not-a-number"')
    with pytest.raises(UnimodParseError, match="UNIMOD:1"):
        parse_obo(_write(tmp_path, text))


def test_incomplete_neutral_loss_raises_parse_error(tmp_path: Path) -> None:
    text = _term().replace(
        'xref: spec_1_group "1"', 'xref: spec_1_group "1"\nxref: spec_1_neutral_loss_0_mono_mass "0"'
    )
    with pytest.raises(UnimodParseError, match="neutral_loss"):
        parse_obo(_write(tmp_path, text))


# ---------------------------------------------------------------------------
# Duplicates
# ---------------------------------------------------------------------------


def test_duplicate_id_raises(tmp_path: Path) -> None:
    p = _write(tmp_path, _term(id=1, name="A") + _term(id=1, name="B"))
    with pytest.raises(UnimodError, match="UNIMOD:1"):
        parse_obo(p)


def test_duplicate_id_in_constructor_raises(db: UnimodDatabase) -> None:
    with pytest.raises(UnimodError):
        UnimodDatabase([db[1], db[1]])


def test_duplicate_name_first_wins(tmp_path: Path) -> None:
    db = parse_obo(_write(tmp_path, _term(id=1, name="Same") + _term(id=2, name="SAME")))
    assert len(db) == 2
    assert db.get_by_name("same").id == 1
    assert db.get_by_id(2).name == "SAME"


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad", ["foo", "", "UNIMOD:", True, False, 1.0, None])
def test_get_by_id_invalid_returns_none(db: UnimodDatabase, bad: object) -> None:
    assert db.get_by_id(bad) is None  # type: ignore[arg-type]


def test_bool_is_not_an_id(db: UnimodDatabase) -> None:
    assert True not in db
    assert db.get(True) is None
    with pytest.raises(KeyError):
        db[True]


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


def test_neutral_loss_formula_types_are_not_optional() -> None:
    nl = NeutralLoss(key=0, mono_mass=0.0, avge_mass=0.0, flag=False, composition="0")
    assert nl.dict_composition == {}
    assert nl.proforma_formula == ""
    assert typing.get_type_hints(NeutralLoss.__dict__["dict_composition"].fget)["return"] == dict[str, int]
    assert typing.get_type_hints(NeutralLoss.__dict__["proforma_formula"].fget)["return"] is str


def test_definition_ref_default_is_empty() -> None:
    e = UnimodEntry(id=5, name="x", definition="d", synonyms=())
    assert e.definition_ref == ""


def test_definition_ref_parsed_bracketless(tmp_path: Path, db: UnimodDatabase) -> None:
    text = _term().replace("[PMID:1]", "[]")
    parsed = parse_obo(_write(tmp_path, text))
    assert parsed[1].definition_ref == ""
    assert db[0].definition_ref == "UNIMOD:0"  # the real root node cites itself
    ref = db[1].definition_ref
    assert ref.startswith("RESID:") and not ref.startswith("[") and not ref.endswith("]")


def test_formula_conventions(db: UnimodDatabase) -> None:
    phospho = db["Phospho"]
    assert phospho.proforma_formula == "HO3P"
    assert " " not in phospho.proforma_formula
    label = db["Label:13C(6)"]
    assert label.proforma_formula == "C-6[13C6]"
    assert label.dict_composition == {"C": -6, "13C": 6}
    assert all(v != 0 for e in db for v in (e.dict_composition or {}).values())


# ---------------------------------------------------------------------------
# download / load
# ---------------------------------------------------------------------------


def test_download_force_semantics(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_retrieve(url: str, dest) -> None:
        calls.append(url)
        Path(dest).write_text("fresh", encoding="utf-8")

    monkeypatch.setattr("unimodpy._download.urllib.request.urlretrieve", fake_retrieve)
    dest = tmp_path / "sub" / "UNIMOD.obo"
    assert download(dest) == dest
    assert len(calls) == 1
    dest.write_text("cached", encoding="utf-8")
    assert download(dest) == dest
    assert len(calls) == 1, "existing file must be reused without force"
    assert dest.read_text() == "cached"
    download(dest, force=True)
    assert len(calls) == 2
    assert dest.read_text() == "fresh"


def test_load_refresh_forces_download(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}
    obo = _write(tmp_path, _term())

    def fake_download(dest=None, *, force: bool = False) -> Path:
        seen["force"] = force
        return obo

    monkeypatch.setattr("unimodpy._download.download", fake_download)
    db = load(refresh=True)
    assert seen["force"] is True
    assert len(db) == 1


def test_load_refresh_survives_new_upstream_enum(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    obo = _write(tmp_path, _term(site="Z") + _term(id=2, name="B", classification="Novel"))
    monkeypatch.setattr("unimodpy._download.download", lambda dest=None, *, force=False: obo)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        db = load(refresh=True)
    assert len(db) == 2
    assert len(w) == 2


# ---------------------------------------------------------------------------
# Packaging
# ---------------------------------------------------------------------------


def test_classifier_is_production_stable() -> None:
    pyproject = tomllib.loads((Path(__file__).parents[1] / "pyproject.toml").read_text(encoding="utf-8"))
    assert "Development Status :: 5 - Production/Stable" in pyproject["project"]["classifiers"]
