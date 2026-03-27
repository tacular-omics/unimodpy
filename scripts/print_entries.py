"""Parse UNIMOD.obo and print every entry."""

from __future__ import annotations

import sys
from pathlib import Path

from unimodpy import parse_obo

OBO_PATH = Path(__file__).parent.parent / "UNIMOD.obo"


def print_entry(entry) -> None:
    print(f"UNIMOD:{entry.id}  {entry.name}")
    print(f"  definition    : {entry.definition}")

    if entry.synonyms:
        print(f"  synonyms      : {', '.join(entry.synonyms)}")
    if entry.comment:
        print(f"  comment       : {entry.comment}")

    if entry.delta_composition is not None:
        print(f"  delta_comp    : {entry.delta_composition}")
        print(f"  formula       : {entry.proforma_formula}")
        print(f"  dict_comp     : {entry.dict_composition}")
        print(f"  mono_mass     : {entry.delta_mono_mass}")
        print(f"  avge_mass     : {entry.delta_avge_mass}")

    if entry.approved is not None:
        print(f"  approved      : {entry.approved}")

    for spec in entry.specificities:
        nl_summary = (
            f"  neutral_losses={[nl.key for nl in spec.neutral_losses]}"
            if spec.neutral_losses
            else ""
        )
        notes = f"  notes={spec.misc_notes!r}" if spec.misc_notes else ""
        print(
            f"  spec {spec.spec_num:>2}: site={spec.site:<8} pos={spec.position:<20}"
            f" class={spec.classification}{nl_summary}{notes}"
        )

    print()


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else OBO_PATH
    db = parse_obo(path)
    print(f"Parsed {len(db)} entries from {path}\n")
    for entry in db:
        print_entry(entry)


if __name__ == "__main__":
    main()
