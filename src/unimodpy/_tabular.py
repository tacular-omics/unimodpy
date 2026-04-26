"""Tabular (TSV/CSV) writer for UNIMOD entries."""

from __future__ import annotations

import csv
import datetime
from collections.abc import Iterable
from pathlib import Path

from unimodpy.models import Specificity, UnimodEntry

_COLUMNS: tuple[str, ...] = (
    "id",
    "name",
    "definition",
    "synonyms",
    "comment",
    "record_id",
    "delta_mono_mass",
    "delta_avge_mass",
    "delta_composition",
    "username_of_poster",
    "group_of_poster",
    "date_time_posted",
    "date_time_modified",
    "approved",
    "is_a",
    "specificities",
)

_SUB_DELIM = "; "


def _cell(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _fmt_datetime(dt: datetime.datetime | None) -> str:
    if dt is None:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _fmt_spec(spec: Specificity) -> str:
    return f"{spec.site}:{spec.position}:{spec.classification}"


def to_row(entry: UnimodEntry) -> list[str]:
    """Flatten a UnimodEntry to a list of column values."""
    return [
        f"UNIMOD:{entry.id}",
        entry.name,
        entry.definition,
        _SUB_DELIM.join(entry.synonyms),
        _cell(entry.comment),
        _cell(entry.record_id),
        _cell(entry.delta_mono_mass),
        _cell(entry.delta_avge_mass),
        _cell(entry.delta_composition),
        _cell(entry.username_of_poster),
        _cell(entry.group_of_poster),
        _fmt_datetime(entry.date_time_posted),
        _fmt_datetime(entry.date_time_modified),
        "" if entry.approved is None else ("1" if entry.approved else "0"),
        f"UNIMOD:{entry.is_a}" if entry.is_a is not None else "",
        _SUB_DELIM.join(_fmt_spec(s) for s in entry.specificities),
    ]


def write_tsv(
    entries: Iterable[UnimodEntry],
    path: Path | str,
    *,
    delimiter: str = "\t",
) -> Path:
    """Write UNIMOD entries to a tab-separated file.

    Pass ``delimiter=","`` to emit CSV instead. Returns the resolved Path.
    """
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter=delimiter, lineterminator="\n")
        writer.writerow(_COLUMNS)
        for entry in entries:
            writer.writerow(to_row(entry))
    return out
