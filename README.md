# unimodpy

[![CI](https://github.com/tacular-omics/unimodpy/actions/workflows/ci.yml/badge.svg)](https://github.com/tacular-omics/unimodpy/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/unimodpy)](https://pypi.org/project/unimodpy/)
[![Python](https://img.shields.io/pypi/pyversions/unimodpy)](https://pypi.org/project/unimodpy/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22926362.svg)](https://doi.org/10.5281/zenodo.22926362)

unimodpy wraps the [UNIMOD](http://www.unimod.org/) mass-spectrometry
modifications database in a typed Python API, so proteomics tooling can look
up modifications by ID, name, mass, or specificity without writing an OBO
parser or re-deriving elemental formulas by hand. It ships with the full
database bundled in, so it works fully offline.

## Highlights

- **Bundled, offline data** — 1,561 UNIMOD terms shipped with the package; no network calls needed
- **Zero core dependencies** — pure Python, `pip install` and go
- **Typed, immutable models** with `py.typed` (PEP 561) for IDE autocomplete and static checking
- **Rich lookups** — by numeric ID, `UNIMOD:N` accession, exact name, or free-text search across names, definitions, and synonyms
- **Full specificity data** — site, position, and classification rules (with neutral losses) for every modification
- **Formula and mass helpers** computed for you (elemental composition dicts, ProForma-style formula strings)
- **Round-trip export** to TSV/CSV and back to OBO
- **[Online browser](https://tacular-omics.github.io/unimodpy/)** — search, sort, and inspect every term, no install required
- **Optional local FastAPI + [MCP](https://modelcontextprotocol.io) server** (`pip install unimodpy[server]`) to expose the database over HTTP or to LLM tools

## Install

```bash
pip install unimodpy
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add unimodpy
```

Requires Python 3.12+. No third-party dependencies for the core package.

## Quick Example

```python
import unimodpy

db = unimodpy.load()          # bundled UNIMOD database, no download needed
print(len(db))                # 1561

# Lookup by integer ID, "UNIMOD:N" accession, or subscript
acetyl = db.get_by_id(1)
print(acetyl.id, acetyl.name, acetyl.delta_mono_mass, acetyl.proforma_formula)
# 1 Acetyl 42.010565 C2H2O

# Lookup by exact name (case-insensitive)
phospho = db.get_by_name("Phospho")

# Full-text search across name, definition, and synonyms
hits = db.search("glycosyl")
print(len(hits))              # 6

# Entries whose delta_mono_mass is within 0.01 Da of 79.966, on S, T or Y
for entry, error in db.search_mass(79.966, site="STY"):
    print(entry.name, round(error, 4))   # Phospho -0.0003, Sulfo 0.0092
db.search_mass(79.966331, tolerance=0.005)  # [(Phospho, ~0.0)]: Sulfo is 9.5 mDa away

# Per-site specificity rules (position, classification, neutral losses)
entry = db.get_by_name("Carbamidomethyl")
print(entry.dict_composition)       # {'H': 3, 'C': 2, 'N': 1, 'O': 1}
for spec in entry.specificities[:1]:
    print(spec.site, spec.position, spec.classification)
    # C Anywhere Chemical derivative
```

## More

<details>
<summary>Refreshing from unimod.org, filtering, TSV/CSV export, OBO round-trip</summary>

```python
# Download the latest OBO and use it immediately
db = unimodpy.load(refresh=True)

# Or just download the file
path = unimodpy.download()                     # ~/.cache/unimodpy/UNIMOD.obo (reused if present)
path = unimodpy.download("/my/dir/UNIMOD.obo")  # custom destination
path = unimodpy.download(force=True)           # always re-download

# Write every entry to TSV (or CSV)
db.write_tsv("unimod.tsv")
db.write_tsv("unimod.csv", delimiter=",")

# Round-trip back to UNIMOD OBO format
db.write_obo("out/UNIMOD.obo")
db2 = unimodpy.parse_obo("out/UNIMOD.obo")  # identical entry count and fields
```

</details>

<details>
<summary>Local HTTP API and MCP server (<code>pip install unimodpy[server]</code>)</summary>

```bash
pip install unimodpy[server]
uvicorn unimodpy.server.app:app --reload
```

This starts a FastAPI app exposing the database as both a JSON REST API
(`GET /api/entries/{id}`, `/api/search`, `/api/entries/by-name/{name}`, …)
and an [MCP](https://modelcontextprotocol.io) endpoint at `POST /mcp` with
`get_by_id`, `get_by_name`, and `search` tools, for pointing LLM clients
directly at UNIMOD:

```bash
claude mcp add unimod http://localhost:8000/mcp --transport http
```

</details>

<details>
<summary>Full API reference</summary>

| Symbol | Description |
|--------|-------------|
| `load(source=None, *, refresh=False, cache=False)` | Load the database. No args → bundled file. `refresh=True` → download first (not together with `source`: `ValueError`). `cache=True` → parse the bundled file once and return the same (read-only) database on later calls. |
| `download(dest=None, *, force=False)` | Download latest OBO from unimod.org; returns `Path`. An existing file is reused unless `force=True`. |
| `parse_obo(path)` | Low-level: parse any OBO file at `path`. |
| `write_tsv(entries, path, *, delimiter)` | Write entries to a TSV (or CSV) file. |
| `write_obo(entries, path, *, header_lines)` | Write entries back to UNIMOD OBO format. |
| `UnimodDatabase` | Iterable collection with `get_by_id`, `get_by_name`, `search`, `get_by_site`, `search_mass`, `write_tsv()`, `write_obo()`, `__getitem__`. Also exposes `header_lines`. |
| `UnimodDatabase.search_mass(delta, *, tolerance=0.01, tolerance_unit="da", site=None, position=None)` | `(entry, delta - delta_mono_mass)` pairs within `tolerance` Da (edges inclusive), closest first. `site` may list several residues (`"STY"`); `get_by_site(site)` takes exactly one. |
| `UnimodEntry` | Frozen dataclass for one modification term. Includes `definition_ref` (bracketless, `""` if none), the `accession` property (`"UNIMOD:21"`), and `get_mass(*, monoisotopic=True)` (`delta_mono_mass`, or `delta_avge_mass` with `monoisotopic=False`). |
| `Specificity` | Frozen dataclass for one site/position rule. |
| `NeutralLoss` | Frozen dataclass for one neutral loss. |
| `Site` | `StrEnum` of amino acid residues and termini. |
| `Position` | `StrEnum` of sequence position constraints. |
| `Classification` | `StrEnum` of modification classes. |
| `UnimodError`, `UnimodParseError`, `UnimodKeyError` | Package exceptions; `UnimodParseError` is also a `ValueError`, `UnimodKeyError` (raised by `db[key]` on a miss) is also a `KeyError`. |

</details>

See [`CHANGELOG.md`](https://github.com/tacular-omics/unimodpy/blob/main/CHANGELOG.md)
for release history.

## Data Source

Term data comes from the [UNIMOD](http://www.unimod.org/) protein
modification database (Creasy & Cottrell, *Proteomics* 2004). See unimod.org
for the database's own license and citation guidance.

## Related Projects

Part of the `tacular-omics` family of proteomics PTM-vocabulary packages:

| Package | Description |
|---------|-------------|
| [psimodpy](https://github.com/tacular-omics/psimodpy) | Parse and query the PSI-MOD protein modification ontology |
| [uniprotptmpy](https://github.com/tacular-omics/uniprotptmpy) | Parse and query the UniProt PTM controlled vocabulary |
| [tacular](https://github.com/tacular-omics/tacular) | Broader MS-proteomics lookup library (amino acids, elements, fragment-ion masses) that bundles its own copies of UNIMOD alongside PSI-MOD, RESID, XLMOD, GNOme, and UniProt-PTM; the base library for peptacular and paftacular |

## Citation

If unimodpy is useful in your research, please cite it — see
[`CITATION.cff`](https://github.com/tacular-omics/unimodpy/blob/main/CITATION.cff)
or use the "Cite this repository" button on GitHub. Releases are archived on
Zenodo (DOI badge above).

## License

[MIT](LICENSE)
