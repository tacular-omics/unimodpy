"""OBO format writer for UNIMOD entries."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from unimodpy.models import NeutralLoss, Specificity, UnimodEntry

_DT_FMT = "%Y-%m-%d %H:%M:%S"

_MINIMAL_HEADER = """\
format-version: 1.4
default-namespace: UNIMOD
"""


def _xref(key: str, value: str) -> str:
    return f'xref: {key} "{value}"\n'


def _write_entry(fh, entry: UnimodEntry, names: dict[int, str]) -> None:
    fh.write("[Term]\n")
    fh.write(f"id: UNIMOD:{entry.id}\n")
    fh.write(f"name: {entry.name}\n")
    fh.write(f'def: "{entry.definition}" [{entry.definition_ref}]\n')
    for syn in entry.synonyms:
        fh.write(f'synonym: "{syn}" EXACT []\n')
    if entry.comment is not None:
        fh.write(f"comment: {entry.comment}\n")
    if entry.is_a is not None:
        parent_comment = names.get(entry.is_a, "")
        suffix = f" ! {parent_comment}" if parent_comment else ""
        fh.write(f"is_a: UNIMOD:{entry.is_a}{suffix}\n")
    if entry.record_id is not None:
        fh.write(_xref("record_id", str(entry.record_id)))
    if entry.delta_mono_mass is not None:
        fh.write(_xref("delta_mono_mass", f"{entry.delta_mono_mass:.6f}"))
    if entry.delta_avge_mass is not None:
        fh.write(_xref("delta_avge_mass", f"{entry.delta_avge_mass:.4f}"))
    if entry.delta_composition is not None:
        fh.write(_xref("delta_composition", entry.delta_composition))
    if entry.username_of_poster is not None:
        fh.write(_xref("username_of_poster", entry.username_of_poster))
    if entry.group_of_poster is not None:
        fh.write(_xref("group_of_poster", entry.group_of_poster))
    if entry.date_time_posted is not None:
        fh.write(_xref("date_time_posted", entry.date_time_posted.strftime(_DT_FMT)))
    if entry.date_time_modified is not None:
        fh.write(_xref("date_time_modified", entry.date_time_modified.strftime(_DT_FMT)))
    if entry.approved is not None:
        fh.write(_xref("approved", "1" if entry.approved else "0"))
    for spec in entry.specificities:
        _write_spec(fh, spec)
    fh.write("\n")


def _write_spec(fh, spec: Specificity) -> None:
    n = spec.spec_num
    fh.write(_xref(f"spec_{n}_group", str(spec.group)))
    fh.write(_xref(f"spec_{n}_hidden", "1" if spec.hidden else "0"))
    fh.write(_xref(f"spec_{n}_site", str(spec.site)))
    fh.write(_xref(f"spec_{n}_position", str(spec.position)))
    fh.write(_xref(f"spec_{n}_classification", str(spec.classification)))
    if spec.misc_notes is not None:
        fh.write(_xref(f"spec_{n}_misc_notes", spec.misc_notes))
    for nl in spec.neutral_losses:
        _write_nl(fh, n, nl)


def _write_nl(fh, spec_num: int, nl: NeutralLoss) -> None:
    k = nl.key
    fh.write(_xref(f"spec_{spec_num}_neutral_loss_{k}_mono_mass", f"{nl.mono_mass:.6f}"))
    fh.write(_xref(f"spec_{spec_num}_neutral_loss_{k}_avge_mass", f"{nl.avge_mass:.4f}"))
    fh.write(_xref(f"spec_{spec_num}_neutral_loss_{k}_flag", "true" if nl.flag else "false"))
    fh.write(_xref(f"spec_{spec_num}_neutral_loss_{k}_composition", nl.composition))


def write_obo(
    entries: Iterable[UnimodEntry],
    path: Path | str,
    *,
    header_lines: Iterable[str] = (),
) -> Path:
    """Write UNIMOD entries to an OBO-format file.

    The output is suitable for re-parsing with parse_obo(). Returns the
    resolved Path.
    """
    materialized = list(entries)
    names = {e.id: e.name for e in materialized}

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        header = list(header_lines)
        if header:
            for line in header:
                fh.write(line + "\n")
            fh.write("\n")
        else:
            fh.write(_MINIMAL_HEADER)
            fh.write("\n")
        for entry in materialized:
            _write_entry(fh, entry, names)
    return out
