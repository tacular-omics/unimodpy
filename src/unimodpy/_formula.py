"""Helpers for parsing UNIMOD delta_composition strings and formatting formulas.

The delta_composition field uses space-separated tokens like:
  "H(2) C(2) O"           – elements with optional counts in parens
  "Hex(5) HexNAc(2)"      – monosaccharide abbreviations
  "H(3) C(2) N S Hex(2)"  – mixed
  "2H(8) 13C(3)"          – stable-isotope labelled elements
  "H(-2) C(-1)"           – negative counts (mass shifts)
"""

from __future__ import annotations

import re
from collections import defaultdict

# ---------------------------------------------------------------------------
# Monosaccharide residue formulas (as elemental formula strings).
# Each formula is the residue form (i.e. the monosaccharide minus water),
# which is how UNIMOD encodes glycan mass shifts.
# ---------------------------------------------------------------------------
MONOSACCHARIDE_FORMULAS: dict[str, str] = {
    "Hex": "C6H10O5",
    "HexNAc": "C8H13NO5",
    "HexA": "C6H8O6",
    "dHex": "C6H10O4",
    "NeuAc": "C11H17NO8",
    "Pent": "C5H8O4",
    "HexN": "C6H11NO4",
    "NeuGc": "C11H17NO9",
    "Sulf": "O3S",
    "sulfate": "O3S",
    "Ac": "C2H2O",
    "Me": "CH2",
    "Kdn": "C9H14O8",
    "Su": "C4H4O4",
    "Hep": "C7H12O6",
}

# Tokenises a standard elemental formula string like "C6H10O5" or "CH2".
# Group 1: optional isotope mass number (e.g. "13" in "13C").
# Group 2: element symbol (1–2 chars, capital + optional lowercase).
# Group 3: optional signed count after the symbol.
_FORMULA_TOKEN_RE = re.compile(r"(\d+)?([A-Z][a-z]?)(-?\d+)?")


def _parse_formula_str(formula: str) -> dict[str, int]:
    """Parse an elemental formula string into {element_key: count}.

    Handles isotope prefixes: "13C2" → {"13C": 2}, "CH2" → {"C": 1, "H": 2}.
    """
    counts: dict[str, int] = defaultdict(int)
    for m in _FORMULA_TOKEN_RE.finditer(formula):
        iso, sym, count_str = m.group(1), m.group(2), m.group(3)
        if not sym:
            continue
        key = f"{iso}{sym}" if iso else sym
        counts[key] += int(count_str) if count_str else 1
    return dict(counts)


def parse_delta_composition(delta_composition: str) -> dict[str, int]:
    """Parse a UNIMOD delta_composition string into element counts.

    Monosaccharide abbreviations are expanded to their constituent atoms.
    Elements with a zero net count are excluded from the result.

    Returns {element_key: count} where element_key is a symbol like
    "C", "H", "O", "13C", "2H", etc.
    """
    counts: dict[str, int] = defaultdict(int)

    for token in delta_composition.split():
        if "(" in token:
            key, tail = token.split("(", 1)
            count = int(tail.rstrip(")"))
        else:
            key = token
            count = 1

        if count == 0:
            continue

        if key in MONOSACCHARIDE_FORMULAS:
            expanded = _parse_formula_str(MONOSACCHARIDE_FORMULAS[key])
            for elem, elem_count in expanded.items():
                counts[elem] += elem_count * count
        else:
            # Single element token, possibly isotope-prefixed (e.g. "2H", "13C").
            counts[key] += count

    return {k: v for k, v in counts.items() if v != 0}


def _hill_sort_key(sym: str) -> tuple[int, int, str]:
    """Hill ordering: C < isotopes-of-C < H < isotopes-of-H < rest (alphabetical).

    Keeps isotopes of the same element grouped immediately after the natural
    isotope, e.g. C, 13C, H, 2H, N, O, S.
    """
    m = re.match(r"^(\d+)?([A-Z].*)$", sym)
    iso_num = int(m.group(1)) if m and m.group(1) else 0
    base = m.group(2) if m else sym
    match base:
        case "C":
            return (0, iso_num, sym)
        case "H":
            return (1, iso_num, sym)
        case _:
            return (2, iso_num, base)


def to_proforma_formula(composition: dict[str, int]) -> str:
    """Convert an element-count dict to a Hill-notation formula string.

    Suitable for use in ProForma modification annotations, e.g. inside
    ``[Formula:C2H2O]``.  Count of 1 is omitted; negative counts are written
    with a ``-`` sign directly after the symbol (e.g. ``H-1``).
    """
    parts: list[str] = []
    for sym, count in sorted(composition.items(), key=lambda x: _hill_sort_key(x[0])):
        if count == 0:
            continue
        count_str = "" if count == 1 else str(count)
        parts.append(f"{sym}{count_str}")
    return "".join(parts)
