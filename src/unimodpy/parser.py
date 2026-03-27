"""Parser for UNIMOD OBO format files."""

from __future__ import annotations

import datetime
import re
from importlib.resources import as_file, files
from pathlib import Path

from unimodpy.database import UnimodDatabase
from unimodpy.models import Classification, NeutralLoss, Position, Site, Specificity, UnimodEntry

# Module-level compiled regexes — avoids recompilation on every entry.
_XREF_RE = re.compile(r'^xref:\s+(\S+)\s+"(.*)"$')
_DEF_RE = re.compile(r'^def:\s+"(.*)"\s+\[.*\]$')
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


def _build_entry(lines: list[str]) -> UnimodEntry:
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

    for line in lines:
        if line.startswith("id:"):
            raw = line[3:].strip()
            entry_id = int(raw.upper().removeprefix("UNIMOD:"))
        elif line.startswith("name:"):
            name = line[5:].strip()
        elif line.startswith("def:"):
            m = _DEF_RE.match(line)
            definition = m.group(1) if m else line[4:].strip()
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

    # Build neutral losses per spec
    spec_nls: dict[int, tuple[NeutralLoss, ...]] = {}
    for spec_n, nl_dict in nls.items():
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
            site=Site(fields["site"]),
            position=Position(fields["position"]),
            classification=Classification(fields["classification"]),
            misc_notes=fields.get("misc_notes"),
            neutral_losses=spec_nls.get(spec_n, ()),
        )
        for spec_n, fields in sorted(specs.items())
    )

    if entry_id is None:
        raise ValueError("OBO entry is missing required 'id' tag")
    if name is None:
        raise ValueError("OBO entry is missing required 'name' tag")

    return UnimodEntry(
        id=entry_id,
        name=name,
        definition=definition or "",
        synonyms=tuple(synonyms),
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
    """
    path = Path(path)
    entries: list[UnimodEntry] = []
    current_lines: list[str] = []
    in_term = False

    with path.open(encoding="utf-8") as fh:
        for raw_line in fh:
            line = raw_line.rstrip("\n")
            if line == "[Term]":
                in_term = True
                current_lines = []
            elif in_term:
                if line == "":
                    entries.append(_build_entry(current_lines))
                    in_term = False
                else:
                    current_lines.append(line)

    # Flush final entry when file ends without a trailing blank line
    if in_term and current_lines:
        entries.append(_build_entry(current_lines))

    return UnimodDatabase(entries)


def load(source: Path | str | None = None, *, refresh: bool = False) -> UnimodDatabase:
    """Load the UNIMOD database.

    Args:
        source:  Path to an OBO file. If omitted, uses the bundled file.
        refresh: Download the latest OBO from unimod.org before loading.
                 Ignored when *source* is given explicitly.

    Returns:
        A :class:`UnimodDatabase` ready for lookups.
    """
    if source is not None:
        return parse_obo(source)
    if refresh:
        from unimodpy._download import download

        return parse_obo(download())
    ref = files("unimodpy") / "data" / "UNIMOD.obo"
    with as_file(ref) as path:
        return parse_obo(path)
