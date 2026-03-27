"""Tests for UNIMOD OBO parser and lookup."""

from __future__ import annotations

import dataclasses
import datetime
from pathlib import Path

import pytest

from unimodpy import UnimodDatabase, parse_obo
from unimodpy.models import UnimodEntry


# ---------------------------------------------------------------------------
# Parsing — entry count and root node
# ---------------------------------------------------------------------------


def test_entry_count(db: UnimodDatabase) -> None:
    assert len(db) == 1552


def test_root_node(db: UnimodDatabase) -> None:
    root = db.get_by_id(0)
    assert root is not None
    assert root.name == "unimod root node"
    # Root has no xref lines
    assert root.record_id is None
    assert root.delta_mono_mass is None
    assert root.approved is None
    assert root.specificities == ()


# ---------------------------------------------------------------------------
# Parsing — scalar xref fields (Acetyl, UNIMOD:1)
# ---------------------------------------------------------------------------


def test_acetyl_scalars(db: UnimodDatabase) -> None:
    e = db["UNIMOD:1"]
    assert e.id == 1
    assert e.name == "Acetyl"
    assert e.delta_mono_mass == pytest.approx(42.010565)
    assert e.delta_avge_mass == pytest.approx(42.0367)
    assert e.delta_composition == "H(2) C(2) O"
    assert e.approved is True
    assert e.date_time_posted == datetime.datetime(2002, 8, 19, 19, 17, 11)


def test_negative_delta_mass(db: UnimodDatabase) -> None:
    # Amidated (UNIMOD:2) has a negative mono mass
    e = db[2]
    assert e.delta_mono_mass == pytest.approx(-0.984016)


# ---------------------------------------------------------------------------
# Parsing — specificities
# ---------------------------------------------------------------------------


def test_acetyl_first_specificity(db: UnimodDatabase) -> None:
    e = db[1]
    assert len(e.specificities) > 0
    spec1 = e.specificities[0]
    assert spec1.spec_num == 1
    assert spec1.site == "K"
    assert spec1.position == "Anywhere"
    assert spec1.hidden is False
    assert spec1.neutral_losses == ()


def test_specificity_nterm(db: UnimodDatabase) -> None:
    e = db[1]
    # Second specificity of Acetyl is N-term
    spec2 = e.specificities[1]
    assert spec2.site == "N-term"


# ---------------------------------------------------------------------------
# Parsing — neutral losses (Carbamidomethyl, UNIMOD:4)
# ---------------------------------------------------------------------------


def test_neutral_losses(db: UnimodDatabase) -> None:
    e = db[4]
    # Find a spec that has neutral losses
    specs_with_nl = [s for s in e.specificities if s.neutral_losses]
    assert len(specs_with_nl) > 0

    # Find the spec with two neutral losses (keys 0 and 106)
    spec = next((s for s in specs_with_nl if len(s.neutral_losses) == 2), None)
    assert spec is not None

    keys = [nl.key for nl in spec.neutral_losses]
    assert 0 in keys
    assert 106 in keys

    nl0 = next(nl for nl in spec.neutral_losses if nl.key == 0)
    assert nl0.mono_mass == pytest.approx(0.0)
    assert nl0.flag is False

    nl106 = next(nl for nl in spec.neutral_losses if nl.key == 106)
    assert nl106.mono_mass == pytest.approx(105.024835)
    assert nl106.composition == "H(7) C(3) N O S"


def test_neutral_losses_sorted_by_key(db: UnimodDatabase) -> None:
    for entry in db:
        for spec in entry.specificities:
            keys = [nl.key for nl in spec.neutral_losses]
            assert keys == sorted(keys)


# ---------------------------------------------------------------------------
# Parsing — optional fields
# ---------------------------------------------------------------------------


def test_synonyms_present(db: UnimodDatabase) -> None:
    e = db[2]  # Amidated
    assert "Top-Down sequencing c-type fragment ion" in e.synonyms


def test_synonyms_empty(db: UnimodDatabase) -> None:
    e = db[1]  # Acetyl has no synonym lines
    assert e.synonyms == ()


def test_comment_optional(db: UnimodDatabase) -> None:
    # At least one entry must have a comment and at least one must not
    with_comment = [e for e in db if e.comment is not None]
    without_comment = [e for e in db if e.comment is None]
    assert len(with_comment) > 0
    assert len(without_comment) > 0


def test_misc_notes_optional(db: UnimodDatabase) -> None:
    # Some specs have misc_notes, some don't
    all_specs = [s for e in db for s in e.specificities]
    assert any(s.misc_notes is not None for s in all_specs)
    assert any(s.misc_notes is None for s in all_specs)


# ---------------------------------------------------------------------------
# UnimodDatabase — lookup by ID
# ---------------------------------------------------------------------------


def test_get_by_id_int(db: UnimodDatabase) -> None:
    assert db.get_by_id(1).name == "Acetyl"  # type: ignore[union-attr]


def test_get_by_id_unimod_str(db: UnimodDatabase) -> None:
    assert db.get_by_id("UNIMOD:1").name == "Acetyl"  # type: ignore[union-attr]


def test_get_by_id_bare_str(db: UnimodDatabase) -> None:
    assert db.get_by_id("1").name == "Acetyl"  # type: ignore[union-attr]


def test_get_by_id_lowercase_prefix(db: UnimodDatabase) -> None:
    assert db.get_by_id("unimod:1").name == "Acetyl"  # type: ignore[union-attr]


def test_get_by_id_missing_returns_none(db: UnimodDatabase) -> None:
    assert db.get_by_id(999999) is None


def test_get_by_id_invalid_str_returns_none(db: UnimodDatabase) -> None:
    assert db.get_by_id("not_an_id") is None


def test_getitem_success(db: UnimodDatabase) -> None:
    assert db[1].name == "Acetyl"


def test_getitem_raises_on_missing(db: UnimodDatabase) -> None:
    with pytest.raises(KeyError):
        _ = db[999999]


# ---------------------------------------------------------------------------
# UnimodDatabase — lookup by name
# ---------------------------------------------------------------------------


def test_get_by_name_exact(db: UnimodDatabase) -> None:
    assert db.get_by_name("Acetyl").id == 1  # type: ignore[union-attr]


def test_get_by_name_lowercase(db: UnimodDatabase) -> None:
    assert db.get_by_name("acetyl").id == 1  # type: ignore[union-attr]


def test_get_by_name_uppercase(db: UnimodDatabase) -> None:
    assert db.get_by_name("ACETYL").id == 1  # type: ignore[union-attr]


def test_get_by_name_missing(db: UnimodDatabase) -> None:
    assert db.get_by_name("does_not_exist_xyz") is None


# ---------------------------------------------------------------------------
# UnimodDatabase — search
# ---------------------------------------------------------------------------


def test_search_returns_name_matches(db: UnimodDatabase) -> None:
    results = db.search("acetyl")
    names = [e.name for e in results]
    assert "Acetyl" in names
    assert len(results) > 1


def test_search_synonym_match(db: UnimodDatabase) -> None:
    results = db.search("Carboxyamidomethylation")
    assert any(e.id == 4 for e in results)


def test_search_empty_matches_all(db: UnimodDatabase) -> None:
    assert len(db.search("")) == len(db)


def test_search_no_match(db: UnimodDatabase) -> None:
    assert db.search("xyzzy_no_match_ever") == []


# ---------------------------------------------------------------------------
# UnimodDatabase — iteration and length
# ---------------------------------------------------------------------------


def test_iter_yields_all_entries(db: UnimodDatabase) -> None:
    entries = list(db)
    assert len(entries) == len(db)


def test_iter_first_is_root(db: UnimodDatabase) -> None:
    assert next(iter(db)).id == 0


# ---------------------------------------------------------------------------
# Immutability (frozen dataclasses)
# ---------------------------------------------------------------------------


def test_entry_is_frozen(db: UnimodDatabase) -> None:
    e = db[1]
    with pytest.raises((AttributeError, dataclasses.FrozenInstanceError)):
        e.name = "mutated"  # type: ignore[misc]


def test_specificity_is_frozen(db: UnimodDatabase) -> None:
    spec = db[1].specificities[0]
    with pytest.raises((AttributeError, dataclasses.FrozenInstanceError)):
        spec.site = "X"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# parse_obo — accepts Path and str, works on minimal file
# ---------------------------------------------------------------------------


def test_parse_obo_minimal(tmp_path: Path) -> None:
    obo = tmp_path / "mini.obo"
    obo.write_text(
        "format-version: 1.4\n\n"
        "[Term]\n"
        "id: UNIMOD:0\n"
        'name: unimod root node\n'
        'def: "Root node." [UNIMOD:0]\n'
        "\n"
    )
    result = parse_obo(str(obo))
    assert len(result) == 1
    assert result[0].name == "unimod root node"
    assert result[0].id == 0


def test_parse_obo_accepts_path(tmp_path: Path) -> None:
    obo = tmp_path / "mini.obo"
    obo.write_text(
        "[Term]\n"
        "id: UNIMOD:0\n"
        'name: unimod root node\n'
        'def: "Root." [UNIMOD:0]\n'
    )
    result = parse_obo(obo)  # Path object, no trailing newline
    assert len(result) == 1


def test_parse_obo_entry_with_all_fields(tmp_path: Path) -> None:
    obo = tmp_path / "full.obo"
    obo.write_text(
        "[Term]\n"
        "id: UNIMOD:1\n"
        "name: Acetyl\n"
        'def: "Acetylation." [PMID:1234]\n'
        'synonym: "AcK" RELATED []\n'
        "comment: A common modification\n"
        'xref: record_id "1"\n'
        'xref: delta_mono_mass "42.010565"\n'
        'xref: delta_avge_mass "42.0367"\n'
        'xref: delta_composition "H(2) C(2) O"\n'
        'xref: username_of_poster "admin"\n'
        'xref: group_of_poster "admin"\n'
        'xref: date_time_posted "2002-08-19 19:17:11"\n'
        'xref: date_time_modified "2017-11-08 16:08:56"\n'
        'xref: approved "1"\n'
        'xref: spec_1_group "1"\n'
        'xref: spec_1_hidden "0"\n'
        'xref: spec_1_site "K"\n'
        'xref: spec_1_position "Anywhere"\n'
        'xref: spec_1_classification "Post-translational"\n'
        "is_a: UNIMOD:0 ! unimod root node\n"
        "\n"
    )
    result = parse_obo(obo)
    e = result[1]
    assert e.id == 1
    assert e.name == "Acetyl"
    assert e.synonyms == ("AcK",)
    assert e.comment == "A common modification"
    assert e.delta_mono_mass == pytest.approx(42.010565)
    assert e.approved is True
    assert e.date_time_posted == datetime.datetime(2002, 8, 19, 19, 17, 11)
    assert len(e.specificities) == 1
    spec = e.specificities[0]
    assert spec.site == "K"
    assert spec.hidden is False
    assert spec.misc_notes is None


def test_parse_obo_neutral_loss(tmp_path: Path) -> None:
    obo = tmp_path / "nl.obo"
    obo.write_text(
        "[Term]\n"
        "id: UNIMOD:4\n"
        "name: Carbamidomethyl\n"
        'def: "Test." [PMID:1]\n'
        'xref: record_id "4"\n'
        'xref: delta_mono_mass "57.021464"\n'
        'xref: delta_avge_mass "57.0513"\n'
        'xref: delta_composition "H(3) C(2) N O"\n'
        'xref: username_of_poster "unimod"\n'
        'xref: group_of_poster "admin"\n'
        'xref: date_time_posted "2002-08-19 19:17:11"\n'
        'xref: date_time_modified "2002-08-19 19:17:11"\n'
        'xref: approved "1"\n'
        'xref: spec_1_group "1"\n'
        'xref: spec_1_hidden "0"\n'
        'xref: spec_1_site "C"\n'
        'xref: spec_1_position "Anywhere"\n'
        'xref: spec_1_classification "Chemical derivative"\n'
        'xref: spec_1_neutral_loss_0_mono_mass "0"\n'
        'xref: spec_1_neutral_loss_0_avge_mass "0"\n'
        'xref: spec_1_neutral_loss_0_flag "false"\n'
        'xref: spec_1_neutral_loss_0_composition "0"\n'
        'xref: spec_1_neutral_loss_106_mono_mass "105.024835"\n'
        'xref: spec_1_neutral_loss_106_avge_mass "105.1588"\n'
        'xref: spec_1_neutral_loss_106_flag "false"\n'
        'xref: spec_1_neutral_loss_106_composition "H(7) C(3) N O S"\n'
    )
    result = parse_obo(obo)
    e = result[4]
    assert len(e.specificities) == 1
    nls = e.specificities[0].neutral_losses
    assert len(nls) == 2
    assert nls[0].key == 0
    assert nls[1].key == 106
    assert nls[1].mono_mass == pytest.approx(105.024835)


def test_entry_is_dataclass(db: UnimodDatabase) -> None:
    e = db[1]
    assert dataclasses.is_dataclass(e)
    fields = {f.name for f in dataclasses.fields(e)}
    assert "id" in fields
    assert "name" in fields
    assert "specificities" in fields


def test_all_entries_have_id_and_name(db: UnimodDatabase) -> None:
    for entry in db:
        assert isinstance(entry.id, int)
        assert isinstance(entry.name, str)
        assert len(entry.name) > 0


# ---------------------------------------------------------------------------
# composition and proforma_formula properties
# ---------------------------------------------------------------------------


def test_composition_simple(db: UnimodDatabase) -> None:
    # Acetyl: delta_composition = "H(2) C(2) O"
    comp = db[1].dict_composition
    assert comp == {"C": 2, "H": 2, "O": 1}


def test_composition_negative_counts(db: UnimodDatabase) -> None:
    # Amidated: delta_composition = "H N O(-1)"
    comp = db[2].dict_composition
    assert comp is not None
    assert comp["N"] == 1
    assert comp["O"] == -1
    assert comp["H"] == 1


def test_composition_monosaccharide_only(db: UnimodDatabase) -> None:
    # Hex modification: delta_composition = "Hex"  → C6H10O5
    e = next(e for e in db if e.delta_composition == "Hex")
    comp = e.dict_composition
    assert comp == {"C": 6, "H": 10, "O": 5}


def test_composition_mixed_monosaccharide_and_elements(db: UnimodDatabase) -> None:
    # "H O(3) P Hex(3) HexNAc(2)" appears in the file
    e = next(e for e in db if e.delta_composition == "H O(3) P Hex(3) HexNAc(2)")
    comp = e.dict_composition
    assert comp is not None
    # Hex(3) = C18H30O15, HexNAc(2) = C16H26N2O10, + H, O3, P
    assert comp["C"] == 18 + 16       # 34
    assert comp["N"] == 2
    assert comp["P"] == 1


def test_composition_isotope_labels(db: UnimodDatabase) -> None:
    # "H(-1) 2H(3) C(2) O" — deuterium labelled
    e = next(e for e in db if e.delta_composition == "H(-1) 2H(3) C(2) O")
    comp = e.dict_composition
    assert comp is not None
    assert comp["H"] == -1
    assert comp["2H"] == 3
    assert comp["C"] == 2


def test_composition_root_node_is_none(db: UnimodDatabase) -> None:
    assert db[0].dict_composition is None


def test_proforma_formula_simple(db: UnimodDatabase) -> None:
    # Acetyl: C2H2O
    assert db[1].proforma_formula == "C2H2O"


def test_proforma_formula_negative_count(db: UnimodDatabase) -> None:
    # Amidated: H N O(-1) → "HNO-1"
    assert db[2].proforma_formula == "HNO-1"


def test_proforma_formula_monosaccharide(db: UnimodDatabase) -> None:
    # Hex → C6H10O5
    e = next(e for e in db if e.delta_composition == "Hex")
    assert e.proforma_formula == "C6H10O5"


def test_proforma_formula_hill_order(db: UnimodDatabase) -> None:
    # Hill order: C before H before others
    formula = db[1].proforma_formula
    assert formula is not None
    assert formula.index("C") < formula.index("H")


def test_proforma_formula_root_node_is_none(db: UnimodDatabase) -> None:
    assert db[0].proforma_formula is None


def test_proforma_formula_isotope_preserved(db: UnimodDatabase) -> None:
    # "H(-1) 2H(3) C(2) O" — 2H must appear in output
    e = next(e for e in db if e.delta_composition == "H(-1) 2H(3) C(2) O")
    formula = e.proforma_formula
    assert formula is not None
    assert "2H" in formula
    assert "C2" in formula


def test_composition_returns_new_dict_each_call(db: UnimodDatabase) -> None:
    # Property computes fresh each time; mutations don't persist
    e = db[1]
    comp1 = e.dict_composition
    assert comp1 is not None
    comp1["C"] = 999
    assert e.dict_composition == {"C": 2, "H": 2, "O": 1}
