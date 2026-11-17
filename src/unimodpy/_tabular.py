"""Tabular (TSV/CSV) writer for UNIMOD entries."""

from __future__ import annotations

import csv
import datetime
from collections.abc import Iterable
from pathlib import Path

from unimodpy.models import NeutralLoss, Specificity, UnimodEntry

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
    "specificities_hidden",
    "definition_ref",
    "synonym_scopes",
    "specificities_spec_num",
    "specificities_group",
    "specificities_misc_notes",
    "specificities_neutral_losses",
)

_SUB_DELIM = "; "
_LOSS_DELIM = "|"


def _cell(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _fmt_datetime(dt: datetime.datetime | None) -> str:
    if dt is None:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _escape(text: str) -> str:
    """Percent-escape ``%``, ``;`` and ``|`` so free text cannot be read as a sub-delimiter.

    ``%`` is escaped first, so the escape is reversible (``%3B`` is ``;``, ``%7C`` is ``|``,
    ``%25`` is ``%``). Text without those characters is unchanged.
    """
    return text.replace("%", "%25").replace(";", "%3B").replace("|", "%7C")


def _escape_in_loss(text: str) -> str:
    """``_escape`` plus ``:`` as ``%3A``, for a field written inside a neutral-loss item.

    ``:`` separates the five fields of a loss item, so a value carrying one would make the item
    unsplittable. No composition in the bundled database contains ``:``, so this changes nothing
    there; it keeps the five-field split true for any future data. Still reversible, because
    ``_escape`` has already replaced every ``%``: a ``%3A`` in the output can only be a ``:``.
    """
    return _escape(text).replace(":", "%3A")


def _fmt_neutral_loss(loss: NeutralLoss) -> str:
    flag = "1" if loss.flag else "0"
    return f"{loss.key}:{loss.mono_mass}:{loss.avge_mass}:{flag}:{_escape_in_loss(loss.composition)}"


def _fmt_spec(spec: Specificity) -> str:
    return f"{spec.site}:{spec.position}:{spec.classification}"


def to_row(entry: UnimodEntry) -> list[str]:
    """Flatten a UnimodEntry to a list of column values.

    ``specificities_hidden`` holds one ``1``/``0`` per entry of ``specificities``, in the
    same order: Unimod hides most specificities, and the flag is parsed, so dropping it
    from the export would leave a reader unable to tell which rows Unimod shows.

    The six columns after it follow the same rule. ``specificities_spec_num``,
    ``specificities_group``, ``specificities_misc_notes`` and ``specificities_neutral_losses``
    hold one slot per entry of ``specificities``, in the same order, joined with ``"; "``; a
    specificity without a value leaves its slot empty. A slot of ``specificities_neutral_losses``
    holds that specificity's losses joined with ``"|"``, each as
    ``key:mono_mass:avge_mass:flag:composition``. ``%``, ``;`` and ``|`` inside ``misc_notes`` are
    percent-escaped, and a ``composition`` escapes ``:`` as well, so a loss item always splits into
    exactly five fields (see ``_escape`` and ``_escape_in_loss``). An entry with no specificities
    leaves all six of those cells empty. ``definition_ref`` and ``synonym_scopes`` (paired with
    ``synonyms``) sit at entry level.
    """
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
        _SUB_DELIM.join("1" if s.hidden else "0" for s in entry.specificities),
        entry.definition_ref,
        _SUB_DELIM.join(entry.synonym_scopes),
        _SUB_DELIM.join(str(s.spec_num) for s in entry.specificities),
        _SUB_DELIM.join(str(s.group) for s in entry.specificities),
        _SUB_DELIM.join(_escape(s.misc_notes or "") for s in entry.specificities),
        _SUB_DELIM.join(
            _LOSS_DELIM.join(_fmt_neutral_loss(nl) for nl in s.neutral_losses) for s in entry.specificities
        ),
    ]


def write_tsv(
    entries: Iterable[UnimodEntry],
    path: Path | str,
    *,
    delimiter: str = "\t",
) -> Path:
    """Write UNIMOD entries to a tab-separated file.

    One row per entry. ``specificities`` joins each specificity as
    ``site:position:classification`` with ``"; "``, and ``specificities_hidden`` carries
    their hidden flags as ``1``/``0`` in the same order. The remaining columns carry
    ``definition_ref``, ``synonym_scopes``, and each specificity's number, group, misc notes and
    neutral losses, index-aligned with ``specificities`` (see ``to_row`` for the cell format).

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
