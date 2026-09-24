"""Parser for UNIMOD OBO format files."""

from __future__ import annotations

import datetime
import functools
import re
import warnings
from enum import StrEnum
from importlib.resources import as_file, files
from pathlib import Path

from unimodpy.database import UnimodDatabase
from unimodpy.errors import UnimodParseError
from unimodpy.models import Classification, NeutralLoss, Position, Site, Specificity, UnimodEntry

# Module-level compiled regexes — avoids recompilation on every entry.
_XREF_RE = re.compile(r'^xref:\s+(\S+)\s+"(.*)"$')
_DEF_RE = re.compile(r'^def:\s+"(.*)"\s+\[([^\]]*)\]$')
_SYN_RE = re.compile(r'^synonym:\s+"(.*)"\s+\w+\s+\[\]$')
_SPEC_RE = re.compile(r"^spec_(\d+)_(group|hidden|site|position|classification|misc_notes)$")
_NL_RE = re.compile(r"^spec_(\d+)_neutral_loss_(\d+)_(mono_mass|avge_mass|flag|composition)$")
_IS_A_RE = re.compile(r"^is_a:\s+UNIMOD:(\d+)")
_DT_FMT = "%Y-%m-%d %H:%M:%S"

_SCALAR_XREFS = frozenset(
    {
        "record_id",
        "delta_mono_mass",
        "delta_avge_mass",
        "delta_composition",
        "username_of_poster",
        "group_of_poster",
        "date_time_posted",
        "date_time_modified",
        "approved",
    }
)


def _coerce[E: StrEnum](enum: type[E], value: str, where: str) -> E | str:
    """Return ``enum(value)``, or the raw string plus a warning for a value this version does not know."""
    try:
        return enum(value)
    except ValueError:
        warnings.warn(
            f"{where}: unknown {enum.__name__} {value!r} kept as a plain string",
            UserWarning,
            stacklevel=2,
        )
        return value


def _build_entry(lines: list[str], line_no: int, source: str) -> UnimodEntry | None:
    """Build one entry from the lines of a ``[Term]`` block starting at *line_no*.

    Returns None (with a warning) for a block without ``id`` or ``name``.
    Raises UnimodParseError for a malformed value.
    """
    where = f"{source}, line {line_no}"
    raw_id = next((line[3:].strip() for line in lines if line.startswith("id:")), None)
    if raw_id:
        where = f"{where} ({raw_id})"
    try:
        return _build_entry_inner(lines, where)
    except UnimodParseError:
        raise
    except (ValueError, KeyError) as exc:
        detail = f"missing {exc}" if isinstance(exc, KeyError) else str(exc)
        raise UnimodParseError(f"{where}: {detail}") from exc


def _build_entry_inner(lines: list[str], where: str) -> UnimodEntry | None:
    entry_id: int | None = None
    name: str | None = None
    definition: str | None = None
    synonyms: list[str] = []
    comment: str | None = None
    is_a: int | None = None

    scalars: dict[str, str] = {}
    # specs[spec_num][field] = value
    specs: dict[int, dict[str, str]] = {}
    # nls[spec_num][nl_key][field] = value
    nls: dict[int, dict[int, dict[str, str]]] = {}

    definition_ref: str = ""

    for line in lines:
        if line.startswith("id:"):
            raw = line[3:].strip()
            try:
                entry_id = int(raw.upper().removeprefix("UNIMOD:"))
            except ValueError:
                raise UnimodParseError(f"{where}: invalid id {raw!r}") from None
        elif line.startswith("name:"):
            name = line[5:].strip()
        elif line.startswith("def:"):
            m = _DEF_RE.match(line)
            if m:
                definition = m.group(1)
                definition_ref = m.group(2)
            else:
                definition = line[4:].strip()
        elif line.startswith("synonym:"):
            m = _SYN_RE.match(line)
            if m:
                synonyms.append(m.group(1))
        elif line.startswith("comment:"):
            comment = line[8:].strip()
        elif line.startswith("is_a:"):
            m = _IS_A_RE.match(line)
            if m:
                is_a = int(m.group(1))
        elif line.startswith("xref:"):
            m = _XREF_RE.match(line)
            if not m:
                continue
            key, value = m.group(1), m.group(2)

            nl_m = _NL_RE.match(key)
            if nl_m:
                spec_n = int(nl_m.group(1))
                nl_k = int(nl_m.group(2))
                field = nl_m.group(3)
                nls.setdefault(spec_n, {}).setdefault(nl_k, {})[field] = value
                continue

            spec_m = _SPEC_RE.match(key)
            if spec_m:
                spec_n = int(spec_m.group(1))
                field = spec_m.group(2)
                specs.setdefault(spec_n, {})[field] = value
                continue

            if key in _SCALAR_XREFS:
                scalars[key] = value

    if entry_id is None or name is None:
        missing = "id" if entry_id is None else "name"
        warnings.warn(f"{where}: [Term] block missing '{missing}' skipped", UserWarning, stacklevel=2)
        return None

    # Build neutral losses per spec
    spec_nls: dict[int, tuple[NeutralLoss, ...]] = {}
    for spec_n, nl_dict in nls.items():
        for nl_k, fields in nl_dict.items():
            absent = [f for f in ("mono_mass", "avge_mass", "flag", "composition") if f not in fields]
            if absent:
                raise UnimodParseError(f"{where}: spec_{spec_n}_neutral_loss_{nl_k} missing {', '.join(absent)}")
        nl_objs = sorted(
            (
                NeutralLoss(
                    key=nl_k,
                    mono_mass=float(fields["mono_mass"]),
                    avge_mass=float(fields["avge_mass"]),
                    flag=fields["flag"] == "true",
                    composition=fields["composition"],
                )
                for nl_k, fields in nl_dict.items()
            ),
            key=lambda nl: nl.key,
        )
        spec_nls[spec_n] = tuple(nl_objs)

    # Build specificities
    specificities = tuple(
        Specificity(
            spec_num=spec_n,
            group=int(fields["group"]),
            hidden=fields["hidden"] == "1",
            site=_coerce(Site, fields["site"], where),
            position=_coerce(Position, fields["position"], where),
            classification=_coerce(Classification, fields["classification"], where),
            misc_notes=fields.get("misc_notes"),
            neutral_losses=spec_nls.get(spec_n, ()),
        )
        for spec_n, fields in sorted(specs.items())
    )

    return UnimodEntry(
        id=entry_id,
        name=name,
        definition=definition or "",
        synonyms=tuple(synonyms),
        definition_ref=definition_ref,
        comment=comment,
        record_id=int(scalars["record_id"]) if "record_id" in scalars else None,
        delta_mono_mass=float(scalars["delta_mono_mass"]) if "delta_mono_mass" in scalars else None,
        delta_avge_mass=float(scalars["delta_avge_mass"]) if "delta_avge_mass" in scalars else None,
        delta_composition=scalars.get("delta_composition"),
        username_of_poster=scalars.get("username_of_poster"),
        group_of_poster=scalars.get("group_of_poster"),
        date_time_posted=(
            datetime.datetime.strptime(scalars["date_time_posted"], _DT_FMT) if "date_time_posted" in scalars else None
        ),
        date_time_modified=(
            datetime.datetime.strptime(scalars["date_time_modified"], _DT_FMT)
            if "date_time_modified" in scalars
            else None
        ),
        approved=scalars["approved"] == "1" if "approved" in scalars else None,
        is_a=is_a,
        specificities=specificities,
    )


def parse_obo(path: Path | str) -> UnimodDatabase:
    """Parse a UNIMOD OBO file and return a searchable UnimodDatabase.

    Streams the file line-by-line; peak memory is proportional to one entry
    at a time, not the full file.

    Unknown ``site``/``position``/``classification`` values are kept as raw
    strings and ``[Term]`` blocks without ``id`` or ``name`` are skipped; both
    emit a ``UserWarning``.

    Raises:
        UnimodParseError: a malformed value (bad id, number or date, incomplete
            neutral loss). The message names the file, line and entry.
        UnimodError: two entries share an id.
    """
    path = Path(path)
    entries: list[UnimodEntry] = []
    header_lines: list[str] = []
    current_lines: list[str] = []
    in_term = False
    past_header = False
    term_line = 0

    def flush() -> None:
        entry = _build_entry(current_lines, term_line, path.name)
        if entry is not None:
            entries.append(entry)

    with path.open(encoding="utf-8") as fh:
        for line_no, raw_line in enumerate(fh, start=1):
            line = raw_line.rstrip("\n")
            if line == "[Term]":
                in_term = True
                past_header = True
                current_lines = []
                term_line = line_no
            elif in_term:
                if line == "":
                    flush()
                    in_term = False
                else:
                    current_lines.append(line)
            elif not past_header:
                header_lines.append(line)

    # Flush final entry when file ends without a trailing blank line
    if in_term and current_lines:
        flush()

    while header_lines and header_lines[-1] == "":
        header_lines.pop()
    return UnimodDatabase(entries, header_lines=tuple(header_lines))


@functools.cache
def _load_bundled() -> UnimodDatabase:
    """Parse the bundled OBO once; backs ``load(cache=True)``."""
    return load()


def load(source: Path | str | None = None, *, refresh: bool = False, cache: bool = False) -> UnimodDatabase:
    """Load the UNIMOD database.

    Args:
        source:  Path to an OBO file. If omitted, uses the bundled file.
        refresh: Download the latest OBO from unimod.org (``download(force=True)``)
                 and load it instead of the bundled file.
        cache:   If True, parse the bundled file only once per process and return
                 that same database object on every later ``load(cache=True)`` call.
                 The shared object is read-only in practice (entries are frozen and
                 it has no mutating methods); do not reassign its attributes. Only
                 for the bundled file: cannot be combined with *source* or *refresh*.
                 Default False: a new database each call.

    Returns:
        A :class:`UnimodDatabase` ready for lookups.

    Raises:
        ValueError: both *source* and ``refresh=True`` were given, or ``cache=True``
            was combined with either.
    """
    if cache:
        if source is not None or refresh:
            raise ValueError("cache=True only applies to the bundled file; drop source and refresh")
        return _load_bundled()
    if source is not None and refresh:
        raise ValueError("pass either source or refresh=True, not both")
    if source is not None:
        return parse_obo(source)
    if refresh:
        from unimodpy._download import download

        return parse_obo(download(force=True))
    ref = files("unimodpy") / "data" / "UNIMOD.obo"
    with as_file(ref) as path:
        return parse_obo(path)
