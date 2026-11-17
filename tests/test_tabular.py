"""Tests for the TSV/CSV tabular writer."""

import csv
import re
from pathlib import Path

from unimodpy import UnimodDatabase, write_tsv
from unimodpy._tabular import _COLUMNS


def test_readme_documents_export_columns_in_order() -> None:
    readme = (Path(__file__).parent.parent / "README.md").read_text(encoding="utf-8")
    section = readme.split("### TSV/CSV columns\n", 1)[1].split("</details>", 1)[0]
    columns = re.findall(r"^\| `([^`]+)` \|", section, flags=re.MULTILINE)
    assert tuple(columns) == _COLUMNS


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


def test_export_keeps_every_entry_and_specificity_including_hidden(db: UnimodDatabase, tmp_path) -> None:
    """The export is lossless by count: one row per parsed entry, every specificity in its cell.

    Hidden specificities are the ones at risk, because the server drops them by default and
    most of the database is hidden (2,747 of 2,826 in the bundled file). Counted, not sampled.
    """
    out = tmp_path / "out.tsv"
    db.write_tsv(out)
    rows = _read_dict(out)
    assert len(rows) == len(db)
    assert [row["id"] for row in rows] == [f"UNIMOD:{entry.id}" for entry in db]

    parsed = sum(len(entry.specificities) for entry in db)
    hidden = sum(1 for entry in db for spec in entry.specificities if spec.hidden)
    exported = sum(len(row["specificities"].split("; ")) if row["specificities"] else 0 for row in rows)
    assert hidden > 0
    assert exported == parsed


_FIRST_17 = (
    "id name definition synonyms comment record_id delta_mono_mass delta_avge_mass delta_composition "
    "username_of_poster group_of_poster date_time_posted date_time_modified approved is_a "
    "specificities specificities_hidden"
).split()


def test_new_columns_are_appended_after_the_original_17(db: UnimodDatabase, tmp_path) -> None:
    """Appended, not inserted: a positional reader of the older export keeps its column numbers."""
    assert _COLUMNS[:17] == tuple(_FIRST_17)
    assert _COLUMNS[17:] == (
        "definition_ref",
        "synonym_scopes",
        "specificities_spec_num",
        "specificities_group",
        "specificities_misc_notes",
        "specificities_neutral_losses",
    )
    out = tmp_path / "out.tsv"
    db.write_tsv(out)
    assert _read(out)[0][:17] == _FIRST_17


def test_original_columns_keep_their_contents(db: UnimodDatabase, tmp_path) -> None:
    out = tmp_path / "out.tsv"
    db.write_tsv(out)
    rows = _read(out)[1:]
    for row, entry in zip(rows, db, strict=True):
        assert row[0] == f"UNIMOD:{entry.id}"
        assert row[3] == "; ".join(entry.synonyms)
        assert row[15] == "; ".join(f"{s.site}:{s.position}:{s.classification}" for s in entry.specificities)
        assert row[16] == "; ".join("1" if s.hidden else "0" for s in entry.specificities)


def _slots(cell: str) -> list[str]:
    return cell.split("; ") if cell else []


def test_export_carries_every_neutral_loss_and_misc_note(db: UnimodDatabase, tmp_path) -> None:
    """Counted from the TSV's own cells, against the parsed model (1713 losses, 228 notes in the bundled file)."""
    out = tmp_path / "out.tsv"
    db.write_tsv(out)
    rows = _read_dict(out)
    losses = notes = 0
    for row in rows:
        for slot in _slots(row["specificities_neutral_losses"]):
            losses += len(slot.split("|")) if slot else 0
        notes += sum(1 for slot in _slots(row["specificities_misc_notes"]) if slot)
    assert losses == sum(len(s.neutral_losses) for e in db for s in e.specificities) == 1713
    assert notes == sum(1 for e in db for s in e.specificities if s.misc_notes) == 228


def test_per_specificity_columns_align_with_the_specificities_cell(db: UnimodDatabase, tmp_path) -> None:
    out = tmp_path / "out.tsv"
    db.write_tsv(out)
    for row, entry in zip(_read_dict(out), db, strict=True):
        n = len(entry.specificities)
        for column in (
            "specificities_hidden",
            "specificities_spec_num",
            "specificities_group",
            "specificities_misc_notes",
            "specificities_neutral_losses",
        ):
            assert row[column].count("; ") == max(n - 1, 0), (row["id"], column)
        assert _slots(row["specificities_spec_num"]) == [str(s.spec_num) for s in entry.specificities]
        assert _slots(row["specificities_group"]) == [str(s.group) for s in entry.specificities]


def test_entry_level_new_columns(db: UnimodDatabase, tmp_path) -> None:
    out = tmp_path / "out.tsv"
    db.write_tsv(out)
    rows = _read_dict(out)
    assert sum(1 for r in rows if r["definition_ref"]) == sum(1 for e in db if e.definition_ref) == 1561
    assert sum(len(_slots(r["synonym_scopes"])) for r in rows) == sum(len(e.synonym_scopes) for e in db) == 434
    assert [r["definition_ref"] for r in rows] == [e.definition_ref for e in db]


def test_phospho_neutral_loss_is_readable(db: UnimodDatabase, tmp_path) -> None:
    out = tmp_path / "out.tsv"
    db.write_tsv(out)
    row = next(r for r in _read_dict(out) if r["id"] == "UNIMOD:21")
    entry = db.get_by_id(21)
    assert entry is not None
    specs = _slots(row["specificities"])
    losses = _slots(row["specificities_neutral_losses"])
    s_idx = next(i for i, spec in enumerate(specs) if spec.startswith("S:Anywhere"))
    assert "97.976896" in losses[s_idx]
    assert "H(3) O(4) P" in losses[s_idx]
    assert len(set(_slots(row["specificities_group"]))) >= 1


def test_free_text_cannot_collide_with_sub_delimiters(tmp_path) -> None:
    from unimodpy.models import NeutralLoss, Specificity, UnimodEntry

    def spec(num: int, notes: str | None, losses: tuple[NeutralLoss, ...]) -> Specificity:
        return Specificity(num, 1, False, "S", "Anywhere", "Other", notes, losses)

    loss = NeutralLoss(key=1, mono_mass=1.5, avge_mass=1.6, flag=True, composition="a|b; c%")
    entry = UnimodEntry(
        id=9999,
        name="X",
        definition="d",
        synonyms=(),
        specificities=(spec(1, "a; b|c 100%", (loss, loss)), spec(2, None, ()), spec(3, "plain", ())),
    )
    out = tmp_path / "x.tsv"
    write_tsv([entry], out)
    row = _read_dict(out)[0]
    notes = _slots(row["specificities_misc_notes"])
    assert notes == ["a%3B b%7Cc 100%25", "", "plain"]
    losses = _slots(row["specificities_neutral_losses"])
    assert len(losses) == 3
    assert losses[0].split("|") == ["1:1.5:1.6:1:a%7Cb%3B c%25"] * 2
    assert losses[1] == losses[2] == ""


def test_hidden_flags_align_with_the_specificities_cell(db: UnimodDatabase, tmp_path) -> None:
    out = tmp_path / "out.tsv"
    db.write_tsv(out)
    rows = _read_dict(out)
    exported_hidden = 0
    for row, entry in zip(rows, db, strict=True):
        flags = row["specificities_hidden"].split("; ") if row["specificities_hidden"] else []
        specs = row["specificities"].split("; ") if row["specificities"] else []
        assert flags == ["1" if spec.hidden else "0" for spec in entry.specificities]
        assert len(flags) == len(specs)
        exported_hidden += flags.count("1")
    assert exported_hidden == sum(1 for entry in db for spec in entry.specificities if spec.hidden)
