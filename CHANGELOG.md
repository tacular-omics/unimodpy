# Changelog

## [Unreleased]

### Breaking

Shared 1.0 API with psimodpy and uniprotptmpy.

- `download(dest=None, *, force=False)` returns an existing `dest` without downloading; pass `force=True` to re-fetch. `load(refresh=True)` forces. The download goes to a temporary file first, so a failure leaves no truncated cache file.
- `UnimodEntry.definition_ref` defaults to `""` instead of the fake `"UNIMOD:0"`, and a `def:` line with empty brackets (`[]`) parses to `""`. The stored string is bracketless, as before.
- A duplicate id raises `UnimodError` in `UnimodDatabase(...)` and `parse_obo`. It used to keep both entries in `len`/iteration while `get_by_id` returned the last.
- A duplicate name (case-insensitive) is resolved first-wins in `get_by_name`/`db[name]`; it used to be last-wins.
- A `[Term]` block without `id` or `name` is skipped with a `UserWarning`; it used to raise a bare `ValueError` and abort the load.
- Malformed values (bad id, mass, date, integer, incomplete neutral loss) raise `UnimodParseError` naming the file, line and entry, instead of bare `ValueError`/`KeyError`. `UnimodParseError` subclasses `ValueError`, so `except ValueError` still works.
- `Specificity.site`/`position`/`classification` are typed `Site | str`, `Position | str`, `Classification | str`: a value this version does not know is kept as the raw string with a `UserWarning` instead of aborting `load(refresh=True)` with `ValueError`.
- `get_by_id(True)`/`get_by_id(False)` return `None` (they used to return UNIMOD:1 / UNIMOD:0), so `True in db` is `False` and `db[True]` raises `KeyError`.
- `NeutralLoss.dict_composition` is typed `dict[str, int]` and `NeutralLoss.proforma_formula` `str` (never `None`); the server's `NeutralLoss.proforma_formula` is `str`.
- Server wire model `UnimodEntry` exposes the parent as `is_a`, like psimodpy. `parent_id` is still sent as a deprecated duplicate (pydantic `deprecated`) and will be removed in 2.0.
- MCP `search` validates `query` (non-empty) and `limit` (1-500), like the REST `/api/search`; out-of-range arguments return a tool error instead of an unbounded list.

Migration: read `entry.is_a` instead of `parent_id` from the server; call `download(force=True)` where you relied on `download()` always fetching; compare `spec.site == "K"` (works for enum members and raw strings) rather than `isinstance(spec.site, Site)`; catch `UnimodError` for duplicate ids; treat `definition_ref == ""` as "no citations".

### Added

- `unimodpy.errors`: `UnimodError(Exception)` and `UnimodParseError(UnimodError, ValueError)`, exported from `unimodpy`.
- `/api/health` returns a typed `HealthResponse`; `dashboard_entries()` returns `DashboardEntry` TypedDicts.
- Classifier `Development Status :: 5 - Production/Stable`.

- `UnimodDatabase.get(key, default=None)`: returns `db[key]` or `default`, never raises, as in psimodpy and uniprotptmpy.
- Tests recompute every entry's and every neutral loss's monoisotopic and average mass from its parsed composition against a frozen NIST table (pyteomics 5.0.1; generator in `tests/reference/`), plus Hypothesis property tests for the lookups. All 1551 compositions agree.

### Fixed

- `proforma_formula` sorts an isotope next to its element: UNIMOD:214 is now `C4[13C3]H12N[15N]O`, was `C4[13C3]H12NO[15N]` (23 entries).
- `db[key]` raises `KeyError` for a non-int/str key: `db[1.0]` used to return UNIMOD:1 while `1.0 in db` was False, and `db[[1]]` raised `TypeError`. `get_by_id` returns None for such keys. Id strings may have surrounding whitespace (`" UNIMOD:1 "`).
- `key in db` now accepts every key `db[key]` accepts (integer ID, `"UNIMOD:1"`, `"1"`, case-insensitive name) and returns `False` for unknown keys. It used to iterate entries, so `"Acetyl" in db` was `False`. Membership of a `UnimodEntry` object still works.
- The composition token `Water` (neutral loss of UNIMOD:1010) expands to `H2O` in `dict_composition` and `proforma_formula`; it used to be kept as a literal `Water` key.

## [0.2.2] (2026-09-23)

### Fixed

- Zero-mass neutral losses (UNIMOD composition `"0"`) now give an empty `dict_composition` (`{}`) and `proforma_formula` (`""`) instead of `{"0": 1}` and `"0"`.
- `proforma_formula` brackets isotopes as ProForma 2.0 requires (`C-6[13C6]N-2[15N2]`, was `C-613C6N-215N2`). `dict_composition` keys are unchanged.
- The server parses the bundled OBO file once at import instead of twice; `dashboard_entries()` takes an optional database.
- `scripts/print_entries.py` and `scripts/audit_obo.py` default to the bundled `src/unimodpy/data/UNIMOD.obo`.
- `just lint` and `just format` cover `tests` as CI does. Removed the unused `requirements.txt`.

## [0.2.1] (2026-09-23)

### Added

- Releases are archived on Zenodo (`.zenodo.json`); no code changes.

## [0.2.0] (2026-09-23)

### Added

- `write_tsv` and `write_obo` writers; the OBO header round-trips, and entries keep `definition_ref` and `header_lines`.
- Online UNIMOD browser (GitHub Pages) with search, sort, filter and a full detail view.
- FastAPI REST API and MCP server (`server` extra), deployable to Vercel, which also serves the browser dashboard at the root.

### Changed

- **Breaking for the `server` extra:** the MCP server was ported from FastMCP (mcp 1.x) to `MCPServer` (mcp 2.x); it now requires mcp 2.
- MCP tools return typed responses (`structuredContent` with an `outputSchema`).
- Releases publish to PyPI by trusted publishing; the version lives only in `unimodpy.__version__`, with `CITATION.cff` kept in sync.

### Fixed

- The dashboard HTML is read as UTF-8, so it loads on Windows.
- The MCP session manager is created per request, fixing session reuse errors on Vercel.

## [0.1.2] (2026-03-27)

- Packaging and build fixes.

## [0.1.1] (2026-03-27)

- Packaging fixes; development dependencies moved to dependency groups.

## [0.1.0] (2026-03-26)

First release.

* Parse UNIMOD OBO files into typed, frozen dataclasses (`UnimodEntry`, `Specificity`, `NeutralLoss`).
* `UnimodDatabase` with lookup by integer ID, UNIMOD accession string, case-insensitive name, and full-text search.
* `Site`, `Position`, and `Classification` `StrEnum` types for type-safe specificity filtering.
* Elemental composition parsing and Hill-notation ProForma formula generation, including monosaccharide abbreviation expansion and isotope label support.
* `load()` convenience function that reads the bundled OBO with no configuration.
* `download()` to fetch the latest OBO from unimod.org.
* Zero third-party dependencies; requires Python 3.12+.
