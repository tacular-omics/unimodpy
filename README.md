# unimodpy

[![CI](https://github.com/tacular-omics/unimodpy/actions/workflows/ci.yml/badge.svg)](https://github.com/tacular-omics/unimodpy/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/unimodpy)](https://pypi.org/project/unimodpy/)
[![Python](https://img.shields.io/pypi/pyversions/unimodpy)](https://pypi.org/project/unimodpy/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Python library for parsing and querying the [UNIMOD](http://www.unimod.org/) mass spectrometry modifications database.

- Zero dependencies
- Bundled UNIMOD data (1,552 entries) — works offline out of the box
- Typed, immutable data models (`py.typed` / PEP 561)

## Installation

```bash
pip install unimodpy
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add unimodpy
```

Requires Python 3.12+. No third-party dependencies.

## Quick Start

```python
import unimodpy

# Load the bundled UNIMOD database (no file path needed)
db = unimodpy.load()

# Look up by ID
acetyl = db.get_by_id(1)          # integer
acetyl = db.get_by_id("UNIMOD:1") # UNIMOD accession string
acetyl = db["UNIMOD:1"]           # subscript notation

# Look up by name (case-insensitive)
phospho = db.get_by_name("Phospho")

# Full-text search across name, definition, and synonyms
hits = db.search("glycosyl")

print(acetyl)
# UNIMOD:1  Acetyl
#   Acetylation.
#   Formula  : C2H2O
#   Mass     : +42.010565 Da (mono)  +42.0373 Da (avg)
#   Sites (9):
#     1: K @ Anywhere [Post-translational]
#     ...
```

### Refreshing from unimod.org

```python
# Download the latest OBO and use it immediately
db = unimodpy.load(refresh=True)

# Or just download the file
path = unimodpy.download()                        # ~/.cache/unimodpy/UNIMOD.obo
path = unimodpy.download("/my/dir/UNIMOD.obo")    # custom destination
```

### Loading a Custom File

```python
db = unimodpy.load("/path/to/UNIMOD.obo")
# or low-level:
db = unimodpy.parse_obo("/path/to/UNIMOD.obo")
```

### Working with Entries

Each `UnimodEntry` is a frozen dataclass:

```python
entry = db.get_by_name("Carbamidomethyl")

entry.id                  # int — UNIMOD accession number
entry.name                # str
entry.delta_mono_mass     # float — monoisotopic mass shift in Da
entry.delta_avge_mass     # float — average mass shift in Da
entry.proforma_formula    # str — Hill-notation formula, e.g. "C3H5NO"
entry.dict_composition    # dict[str, int] — {"C": 3, "H": 5, "N": 1, "O": 1}
entry.synonyms            # tuple[str, ...] — alternative names
entry.specificities       # tuple[Specificity, ...] — site/position rules

for spec in entry.specificities:
    print(spec.site)            # Site enum, e.g. Site.C ("C")
    print(spec.position)        # Position enum, e.g. Position.ANYWHERE
    print(spec.classification)  # Classification enum
    for nl in spec.neutral_losses:
        print(nl.mono_mass, nl.proforma_formula)
```

### Enums

Site, position, and classification values are typed `StrEnum` members:

```python
from unimodpy import Site, Position, Classification

ptm_sites = [
    spec for spec in entry.specificities
    if spec.classification == Classification.POST_TRANSLATIONAL
    and spec.position == Position.ANYWHERE
]
```

## API Overview

| Symbol | Description |
|--------|-------------|
| `load(source=None, *, refresh=False)` | Load the database. No args -> bundled file. `refresh=True` -> download first. |
| `download(dest=None)` | Download latest OBO from unimod.org; returns `Path`. |
| `parse_obo(path)` | Low-level: parse any OBO file at `path`. |
| `UnimodDatabase` | Iterable collection with `get_by_id`, `get_by_name`, `search`, `__getitem__`. |
| `UnimodEntry` | Frozen dataclass for one modification term. |
| `Specificity` | Frozen dataclass for one site/position rule. |
| `NeutralLoss` | Frozen dataclass for one neutral loss. |
| `Site` | `StrEnum` of amino acid residues and termini. |
| `Position` | `StrEnum` of sequence position constraints. |
| `Classification` | `StrEnum` of modification classes. |

## Development

```bash
just install   # install dependencies with uv
just lint      # ruff check
just format    # ruff format
just ty        # ty type check
just test      # pytest
just check     # lint + type check + test
```

## Related Projects

| Package | Description |
|---------|-------------|
| [uniprotptmpy](https://github.com/tacular-omics/uniprotptmpy) | Parse and query the UniProt PTM controlled vocabulary |
| [psimodpy](https://github.com/tacular-omics/psimodpy) | Parse and query the PSI-MOD protein modification ontology |

## License

[MIT](LICENSE)
