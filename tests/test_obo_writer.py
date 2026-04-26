"""Tests for the UNIMOD OBO round-trip writer."""

from unimodpy import UnimodDatabase, parse_obo, write_obo


def test_write_produces_file(db: UnimodDatabase, tmp_path) -> None:
    out = tmp_path / "out.obo"
    write_obo(db, out, header_lines=db.header_lines)
    assert out.exists()
    assert out.stat().st_size > 0


def test_round_trip_entry_count(db: UnimodDatabase, tmp_path) -> None:
    out = tmp_path / "out.obo"
    write_obo(db, out, header_lines=db.header_lines)
    db2 = parse_obo(out)
    assert len(db2) == len(db)


def test_round_trip_name(db: UnimodDatabase, tmp_path) -> None:
    out = tmp_path / "out.obo"
    write_obo(db, out, header_lines=db.header_lines)
    db2 = parse_obo(out)
    assert db2[1].name == db[1].name


def test_round_trip_definition(db: UnimodDatabase, tmp_path) -> None:
    out = tmp_path / "out.obo"
    write_obo(db, out, header_lines=db.header_lines)
    db2 = parse_obo(out)
    assert db2[1].definition == db[1].definition


def test_round_trip_definition_ref(db: UnimodDatabase, tmp_path) -> None:
    out = tmp_path / "out.obo"
    write_obo(db, out, header_lines=db.header_lines)
    db2 = parse_obo(out)
    assert db2[1].definition_ref == db[1].definition_ref


def test_round_trip_scalars(db: UnimodDatabase, tmp_path) -> None:
    out = tmp_path / "out.obo"
    write_obo(db, out, header_lines=db.header_lines)
    db2 = parse_obo(out)
    e1, e2 = db[1], db2[1]
    assert e1.delta_mono_mass == e2.delta_mono_mass
    assert e1.delta_avge_mass == e2.delta_avge_mass
    assert e1.delta_composition == e2.delta_composition
    assert e1.record_id == e2.record_id
    assert e1.approved == e2.approved


def test_round_trip_synonyms(db: UnimodDatabase, tmp_path) -> None:
    out = tmp_path / "out.obo"
    write_obo(db, out, header_lines=db.header_lines)
    db2 = parse_obo(out)
    e1, e2 = db[1], db2[1]
    assert set(e1.synonyms) == set(e2.synonyms)


def test_round_trip_is_a(db: UnimodDatabase, tmp_path) -> None:
    out = tmp_path / "out.obo"
    write_obo(db, out, header_lines=db.header_lines)
    db2 = parse_obo(out)
    # Every non-root entry should have is_a preserved
    e1, e2 = db[1], db2[1]
    assert e1.is_a == e2.is_a


def test_round_trip_specificities(db: UnimodDatabase, tmp_path) -> None:
    out = tmp_path / "out.obo"
    write_obo(db, out, header_lines=db.header_lines)
    db2 = parse_obo(out)
    e1, e2 = db[1], db2[1]
    assert len(e1.specificities) == len(e2.specificities)
    for s1, s2 in zip(e1.specificities, e2.specificities):
        assert s1.site == s2.site
        assert s1.position == s2.position
        assert s1.classification == s2.classification
        assert s1.group == s2.group
        assert s1.hidden == s2.hidden


def test_round_trip_neutral_losses(db: UnimodDatabase, tmp_path) -> None:
    out = tmp_path / "out.obo"
    write_obo(db, out, header_lines=db.header_lines)
    db2 = parse_obo(out)
    # UNIMOD:4 (Carbamidomethyl) has neutral losses
    entry_with_nl = next(e for e in db if any(s.neutral_losses for s in e.specificities))
    spec_with_nl = next(s for s in entry_with_nl.specificities if s.neutral_losses)
    nl1 = spec_with_nl.neutral_losses[0]
    e2 = db2[entry_with_nl.id]
    spec2 = next(s for s in e2.specificities if s.spec_num == spec_with_nl.spec_num)
    nl2 = spec2.neutral_losses[0]
    assert nl1.key == nl2.key
    assert abs(nl1.mono_mass - nl2.mono_mass) < 1e-6
    assert nl1.composition == nl2.composition
    assert nl1.flag == nl2.flag


def test_round_trip_root_node(db: UnimodDatabase, tmp_path) -> None:
    out = tmp_path / "out.obo"
    write_obo(db, out, header_lines=db.header_lines)
    db2 = parse_obo(out)
    root = db2[0]
    assert root.name == db[0].name
    assert root.delta_mono_mass is None
    assert root.is_a is None


def test_minimal_header_when_no_header_lines(db: UnimodDatabase, tmp_path) -> None:
    out = tmp_path / "out.obo"
    write_obo(db, out)  # no header_lines arg
    content = out.read_text(encoding="utf-8")
    assert content.startswith("format-version:")


def test_stored_header_lines_preserved(db: UnimodDatabase, tmp_path) -> None:
    out = tmp_path / "out.obo"
    write_obo(db, out, header_lines=db.header_lines)
    db2 = parse_obo(out)
    assert db2.header_lines == db.header_lines


def test_creates_parent_directory(db: UnimodDatabase, tmp_path) -> None:
    out = tmp_path / "nested" / "out.obo"
    write_obo(db, out, header_lines=db.header_lines)
    assert out.exists()


def test_database_method_returns_path(db: UnimodDatabase, tmp_path) -> None:
    out = tmp_path / "out.obo"
    result = db.write_obo(out)
    assert result == out
    assert out.exists()


def test_database_method_round_trip(db: UnimodDatabase, tmp_path) -> None:
    out = tmp_path / "out.obo"
    db.write_obo(out)
    db2 = parse_obo(out)
    assert len(db2) == len(db)
    assert db2[1].name == db[1].name
