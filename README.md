# unimodpy

[![CI](https://github.com/tacular-omics/unimodpy/actions/workflows/ci.yml/badge.svg)](https://github.com/tacular-omics/unimodpy/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/unimodpy)](https://pypi.org/project/unimodpy/)
[![Python](https://img.shields.io/pypi/pyversions/unimodpy)](https://pypi.org/project/unimodpy/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Python library for parsing and querying the [UNIMOD](http://www.unimod.org/) mass spectrometry modifications database.

- Zero core dependencies
- Bundled UNIMOD data (1,552 entries) — works offline out of the box
- Typed, immutable data models (`py.typed` / PEP 561)
- TSV/CSV export and round-trip OBO writer
- Optional FastAPI / [Model Context Protocol](https://modelcontextprotocol.io) server (`pip install unimodpy[server]`)


## Online Viewer
#### [Click Me!](https://tacular-omics.github.io/unimodpy/)

The same database is also reachable as a hosted REST + MCP service — see
[HTTP API and MCP Server](#http-api-and-mcp-server) below.

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

### Exporting to TSV/CSV

```python
# Write all entries to a tab-separated file
db.write_tsv("unimod.tsv")

# Or CSV
db.write_tsv("unimod.csv", delimiter=",")

# Standalone function
from unimodpy import write_tsv
write_tsv(db, "unimod.tsv")
```

The TSV includes one row per entry. Specificities are serialized as a compact
`site:position:classification` summary (e.g. `K:Anywhere:Post-translational`).

### Writing back to OBO format

```python
# Round-trip: write entries back to UNIMOD OBO format
db.write_obo("out/UNIMOD.obo")

# Re-parse — identical entry count and field values (including citations)
db2 = unimodpy.parse_obo("out/UNIMOD.obo")

# Standalone function; pass the original header lines for a faithful round-trip
from unimodpy import write_obo
write_obo(db, "out/UNIMOD.obo", header_lines=db.header_lines)
```

## HTTP API and MCP Server

The optional `[server]` extra ships a FastAPI app that exposes the same
database over a JSON REST API *and* over the
[Model Context Protocol](https://modelcontextprotocol.io) so language-model
tools can query UNIMOD directly.

```bash
pip install unimodpy[server]
uvicorn unimodpy.server.app:app --reload
```

### REST endpoints

| Method & path | Returns |
|---------------|---------|
| `GET /api/health` | Service metadata and entry count. |
| `GET /api/entries?limit=&offset=&include_hidden=` | Paginated full entries. |
| `GET /api/entries/{id}` | One full entry by ID (`1` or `UNIMOD:1`). |
| `GET /api/entries/by-name/{name}` | One full entry by exact name. |
| `GET /api/search?q=&limit=` | Search hits as lightweight summaries. |

Hidden specificities (UNIMOD's `hidden=true` sites) are filtered out by
default; pass `?include_hidden=true` to keep them.

Full entry payloads include `references` parsed from `definition_ref` into
`{type, accession, value}` objects and `parent_id` (the entry's UNIMOD
hierarchy parent). Search responses contain just `{id, accession, name,
delta_mono_mass, proforma_formula}` to keep token cost low; call
`/api/entries/{id}` on any hit for the full record.

### MCP server

The same FastAPI app mounts an MCP endpoint at `POST /mcp` with three tools:

| Tool | Purpose |
|------|---------|
| `get_by_id(id, include_hidden=False)` | Look up a single entry. |
| `get_by_name(name, include_hidden=False)` | Exact name lookup. |
| `search(query, limit=25)` | Full-text search returning summaries. |

Tool responses use MCP's structured-output mechanism: the server emits an
`outputSchema` per tool in `tools/list` and returns both `structuredContent`
(typed Pydantic instance) and `content` (text fallback) on `tools/call`, so
LLM clients can parse the response without re-reading the JSON string.

Configure your MCP-aware client to point at `http://localhost:8000/mcp`
(or wherever you deploy the app). Example with the Anthropic CLI:

```bash
claude mcp add unimod http://localhost:8000/mcp --transport http
```

## API Overview

| Symbol | Description |
|--------|-------------|
| `load(source=None, *, refresh=False)` | Load the database. No args -> bundled file. `refresh=True` -> download first. |
| `download(dest=None)` | Download latest OBO from unimod.org; returns `Path`. |
| `parse_obo(path)` | Low-level: parse any OBO file at `path`. |
| `write_tsv(entries, path, *, delimiter)` | Write entries to a TSV (or CSV) file. |
| `write_obo(entries, path, *, header_lines)` | Write entries back to UNIMOD OBO format. |
| `UnimodDatabase` | Iterable collection with `get_by_id`, `get_by_name`, `search`, `write_tsv()`, `write_obo()`, `__getitem__`. Also exposes `header_lines`. |
| `UnimodEntry` | Frozen dataclass for one modification term. Includes `definition_ref`. |
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
