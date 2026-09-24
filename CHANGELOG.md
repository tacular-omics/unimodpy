# Changelog

## [Unreleased]

### Added

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
