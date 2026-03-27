"""Audit UNIMOD.obo for fields not captured by the current dataclasses.

Reports:
  - Top-level tags that are not id/name/def/synonym/comment/is_a/xref
  - synonym: lines whose qualifier doesn't match the _SYN_RE pattern
  - xref: keys that are not scalar fields, spec_N_*, or spec_N_neutral_loss_M_*
  - xref: lines whose overall format doesn't match _XREF_RE
  - spec_N sub-fields that are not group/hidden/site/position/classification/misc_notes
  - spec_N_neutral_loss_M sub-fields that are not mono_mass/avge_mass/flag/composition
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

_XREF_RE = re.compile(r'^xref:\s+(\S+)\s+"(.*)"$')
_SYN_RE = re.compile(r'^synonym:\s+"(.*)"\s+\w+\s+\[\]$')
_SPEC_RE = re.compile(r"^spec_(\d+)_(group|hidden|site|position|classification|misc_notes)$")
_NL_RE = re.compile(r"^spec_(\d+)_neutral_loss_(\d+)_(mono_mass|avge_mass|flag|composition)$")
_SPEC_PREFIX = re.compile(r"^spec_(\d+)_(.+)$")

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

_HANDLED_TAGS = frozenset({"id", "name", "def", "synonym", "comment", "is_a", "xref"})


def _example(examples: dict[str, list[str]], key: str, value: str, limit: int = 3) -> None:
    if len(examples[key]) < limit:
        examples[key].append(value)


def audit(path: Path) -> None:
    unknown_tags: dict[str, int] = defaultdict(int)
    unknown_tag_examples: dict[str, list[str]] = defaultdict(list)

    unmatched_synonyms: list[str] = []

    malformed_xrefs: list[str] = []

    unknown_xref_keys: dict[str, int] = defaultdict(int)
    unknown_xref_examples: dict[str, list[str]] = defaultdict(list)

    unknown_spec_fields: dict[str, int] = defaultdict(int)
    unknown_spec_examples: dict[str, list[str]] = defaultdict(list)

    unknown_nl_fields: dict[str, int] = defaultdict(int)
    unknown_nl_examples: dict[str, list[str]] = defaultdict(list)

    in_term = False
    entry_id = "?"

    with path.open(encoding="utf-8") as fh:
        for raw_line in fh:
            line = raw_line.rstrip("\n")

            if line == "[Term]":
                in_term = True
                entry_id = "?"
                continue

            if not in_term:
                continue

            if line == "":
                in_term = False
                continue

            tag, _, rest = line.partition(": ")

            if tag == "id":
                entry_id = rest.strip()
                continue

            if tag not in _HANDLED_TAGS:
                unknown_tags[tag] += 1
                _example(unknown_tag_examples, tag, f"[{entry_id}] {line}")
                continue

            if tag == "synonym":
                if not _SYN_RE.match(line):
                    unmatched_synonyms.append(f"[{entry_id}] {line}")
                continue

            if tag == "xref":
                m = _XREF_RE.match(line)
                if not m:
                    malformed_xrefs.append(f"[{entry_id}] {line}")
                    continue

                key = m.group(1)
                value = m.group(2)

                # Neutral loss — check sub-fields
                nl_m = _NL_RE.match(key)
                if nl_m:
                    continue  # fully handled

                # Check for spec_N_neutral_loss_M_* with unknown sub-field
                nl_prefix = re.match(r"^spec_(\d+)_neutral_loss_(\d+)_(.+)$", key)
                if nl_prefix:
                    field = nl_prefix.group(3)
                    unknown_nl_fields[field] += 1
                    _example(unknown_nl_examples, field, f"[{entry_id}] {key} = {value!r}")
                    continue

                # Spec field — check sub-fields
                spec_m = _SPEC_RE.match(key)
                if spec_m:
                    continue  # fully handled

                # Check for spec_N_* with unknown sub-field
                spec_prefix = _SPEC_PREFIX.match(key)
                if spec_prefix:
                    field = spec_prefix.group(2)
                    unknown_spec_fields[field] += 1
                    _example(unknown_spec_examples, field, f"[{entry_id}] {key} = {value!r}")
                    continue

                # Scalar xref
                if key in _SCALAR_XREFS:
                    continue  # fully handled

                # Genuinely unknown xref key
                unknown_xref_keys[key] += 1
                _example(unknown_xref_examples, key, f"[{entry_id}] {key} = {value!r}")

    # ---- Report --------------------------------------------------------

    def section(title: str) -> None:
        print(f"\n{'=' * 60}")
        print(f"  {title}")
        print("=" * 60)

    section("Unknown top-level tags")
    if unknown_tags:
        for tag, count in sorted(unknown_tags.items(), key=lambda x: -x[1]):
            print(f"  {tag!r:30s}  {count:>5} occurrences")
            for ex in unknown_tag_examples[tag]:
                print(f"      e.g. {ex}")
    else:
        print("  (none)")

    section("synonym: lines not matched by parser regex")
    if unmatched_synonyms:
        for line in unmatched_synonyms[:20]:
            print(f"  {line}")
        if len(unmatched_synonyms) > 20:
            print(f"  ... and {len(unmatched_synonyms) - 20} more")
    else:
        print("  (none)")

    section("Malformed xref: lines (don't match key \"value\" format)")
    if malformed_xrefs:
        for line in malformed_xrefs[:20]:
            print(f"  {line}")
    else:
        print("  (none)")

    section("Unknown scalar xref keys (not spec_N_* and not in _SCALAR_XREFS)")
    if unknown_xref_keys:
        for key, count in sorted(unknown_xref_keys.items(), key=lambda x: -x[1]):
            print(f"  {key!r:40s}  {count:>5} occurrences")
            for ex in unknown_xref_examples[key]:
                print(f"      e.g. {ex}")
    else:
        print("  (none)")

    section("Unknown spec_N_* sub-fields (not in handled set)")
    if unknown_spec_fields:
        for field, count in sorted(unknown_spec_fields.items(), key=lambda x: -x[1]):
            print(f"  {field!r:40s}  {count:>5} occurrences")
            for ex in unknown_spec_examples[field]:
                print(f"      e.g. {ex}")
    else:
        print("  (none)")

    section("Unknown spec_N_neutral_loss_M_* sub-fields")
    if unknown_nl_fields:
        for field, count in sorted(unknown_nl_fields.items(), key=lambda x: -x[1]):
            print(f"  {field!r:40s}  {count:>5} occurrences")
            for ex in unknown_nl_examples[field]:
                print(f"      e.g. {ex}")
    else:
        print("  (none)")


if __name__ == "__main__":
    obo_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent.parent / "UNIMOD.obo"
    if not obo_path.exists():
        print(f"File not found: {obo_path}", file=sys.stderr)
        sys.exit(1)
    print(f"Auditing: {obo_path}")
    audit(obo_path)
