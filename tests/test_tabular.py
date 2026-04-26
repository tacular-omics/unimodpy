"""Tests for the TSV/CSV tabular writer."""

import csv

from unimodpy import UnimodDatabase, write_tsv
from unimodpy._tabular import _COLUMNS


def _read(path, delimiter="\t"):
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.reader(fh, delimiter=delimiter))


def _read_dict(path, delimiter="\t"):
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh, delimiter=delimiter))


def test_header_columns(db: UnimodDatabase, tmp_path) -> None:
    out = tmp_path / "out.tsv"
    write_tsv(db, out)
    rows = _read(out)
    assert tuple(rows[0]) == _COLUMNS


def test_row_count(db: UnimodDatabase, tmp_path) -> None:
    out = tmp_path / "out.tsv"
    write_tsv(db, out)
    rows = _read(out)
    assert len(rows) == len(db) + 1


def test_id_format(db: UnimodDatabase, tmp_path) -> None:
    out = tmp_path / "out.tsv"
    write_tsv(db, out)
    rows = _read_dict(out)
    assert rows[0]["id"].startswith("UNIMOD:")


def test_acetyl_scalars(db: UnimodDatabase, tmp_path) -> None:
    out = tmp_path / "out.tsv"
    write_tsv(db, out)
    rows = _read_dict(out)
    row = next(r for r in rows if r["id"] == "UNIMOD:1")
    assert row["name"] == "Acetyl"
    assert float(row["delta_mono_mass"]) == 42.010565


def test_root_node_empty_scalars(db: UnimodDatabase, tmp_path) -> None:
    out = tmp_path / "out.tsv"
    write_tsv(db, out)
    rows = _read_dict(out)
    root = next(r for r in rows if r["id"] == "UNIMOD:0")
    assert root["delta_mono_mass"] == ""
    assert root["delta_avge_mass"] == ""
    assert root["record_id"] == ""
    assert "None" not in root.values()


def test_synonyms_joined(db: UnimodDatabase, tmp_path) -> None:
    out = tmp_path / "out.tsv"
    write_tsv(db, out)
    rows = _read_dict(out)
    # Find an entry known to have synonyms
    entry_with_syns = next(r for r in rows if r["synonyms"])
    assert "; " in entry_with_syns["synonyms"] or len(entry_with_syns["synonyms"]) > 0


def test_specificities_compact_format(db: UnimodDatabase, tmp_path) -> None:
    out = tmp_path / "out.tsv"
    write_tsv(db, out)
    rows = _read_dict(out)
    row = next(r for r in rows if r["id"] == "UNIMOD:1")
    specs = row["specificities"]
    # Each spec should be "site:position:classification"
    assert specs
    parts = specs.split("; ")
    assert all(p.count(":") == 2 for p in parts)


def test_approved_values(db: UnimodDatabase, tmp_path) -> None:
    out = tmp_path / "out.tsv"
    write_tsv(db, out)
    rows = _read_dict(out)
    approved_vals = {r["approved"] for r in rows if r["approved"]}
    assert approved_vals <= {"1", "0"}


def test_is_a_format(db: UnimodDatabase, tmp_path) -> None:
    out = tmp_path / "out.tsv"
    write_tsv(db, out)
    rows = _read_dict(out)
    # All non-root entries have is_a
    rows_with_parent = [r for r in rows if r["is_a"]]
    assert len(rows_with_parent) > 0
    assert all(r["is_a"].startswith("UNIMOD:") for r in rows_with_parent)


def test_csv_delimiter(db: UnimodDatabase, tmp_path) -> None:
    out = tmp_path / "out.csv"
    write_tsv(db, out, delimiter=",")
    rows = _read_dict(out, delimiter=",")
    assert len(rows) == len(db)
    assert any(r["id"] == "UNIMOD:1" for r in rows)


def test_creates_parent_directory(db: UnimodDatabase, tmp_path) -> None:
    out = tmp_path / "nested" / "out.tsv"
    write_tsv(db, out)
    assert out.exists()


def test_database_method_returns_path(db: UnimodDatabase, tmp_path) -> None:
    out = tmp_path / "out.tsv"
    result = db.write_tsv(out)
    assert result == out
    assert out.exists()


def test_database_method_csv(db: UnimodDatabase, tmp_path) -> None:
    out = tmp_path / "out.csv"
    db.write_tsv(out, delimiter=",")
    rows = _read_dict(out, delimiter=",")
    assert len(rows) == len(db)
