# Changelog

## [Unreleased]

## [1.1.1] (2026-09-25)

### Added

- Browser site (`docs/index.html`): mass search. Enter a signed delta mass, a tolerance in Da or ppm (ppm is relative to a precursor mass you enter) and monoisotopic or average mass; it combines with the text search, adds a sortable Δ error column (closest first) and keeps its state in the URL (`?mass=42.0106&tol=0.01&unit=da`). Same matching rule as `search_mass()`. `scripts/test_mass_search.py` checks it headless against `search_mass()` (needs Playwright).

### Changed

- Browser site restyled to the shared tacular-omics style (plain academic layout, labelled units, light and dark themes); the footer shows the package version the data came from.
- The source distribution now contains only the source, tests and the README, changelog, citation and license files: no paper, docs, lockfile or repository tooling.

## [1.1.0] (2026-09-24)

Additive only: nothing that worked in 1.0 changes behaviour.

### Added

- `load(cache=True)`: parse the bundled OBO once per process and return that same database on later `load(cache=True)` calls. The database is shared by every such caller: do not modify it. Combining `cache=True` with `source` or `refresh=True` raises `ValueError`. The default (`cache=False`) still parses anew on each call.
- `UnimodKeyError(UnimodError, KeyError)`, exported: `db[key]` raises it on a miss. It is still a `KeyError`, not a `ValueError` (so `except KeyError` and `db.get` work as before) and `args[0]` is still the key.
- `search_mass(delta, *, tolerance=0.01, tolerance_unit="da", site=None, position=None) -> list[tuple[entry, float]]`: entries whose `delta_mono_mass` is within `tolerance` of `delta`, as `(entry, error)` pairs with `error = delta - mass`, closest first (ties in mass, then file order). `tolerance_unit` accepts only `"da"` (exact, lowercase): ppm is not offered because a ppm window on a delta mass is ill-defined, and the keyword keeps the call shape of `tacular.tolerance` so units can be added later. Both window edges are inclusive. Entries without a mass are skipped. `site` is one or more residue letters (`"S"`, `"STY"`, any case; any of them matches, while `get_by_site` takes exactly one) or `"N-term"`/`"C-term"`, matched against the entry's specificities (hidden ones included), `site` letters and `N-term`/`C-term`. `position` is where the residue was observed: `"anywhere"`, `"peptide n-term"`, `"peptide c-term"`, `"protein n-term"`, `"protein c-term"` (case-insensitive; `"Any N-term"`/`"Any C-term"` are aliases for the peptide ones); it is matched against each specificity's `position` (Anywhere, Any N-term, Any C-term, Protein N-term, Protein C-term): `"protein n-term"` also matches Any N-term rules, `"peptide n-term"` does not match Protein N-term rules. A modification of the terminus itself matches any residue at that terminus. A sorted mass index is built on the first call, and each search is a bisect. A bad `site`, `position`, `tolerance_unit`, `delta` or `tolerance` raises `UnimodError`.
- `get_by_site(site)`: entries with a specificity on residue `site` or on `"N-term"`/`"C-term"` (case-insensitive), in file order. It takes exactly one residue (`search_mass(site=)` takes several). Unknown or non-string input returns `[]`.
- `UnimodEntry.get_mass(*, monoisotopic=True) -> float | None`: the mass difference in Da, `delta_mono_mass` (default) or `delta_avge_mass` (`monoisotopic=False`), with the same keyword as tacular 2.0's `get_mass`. The old attributes stay. `search_mass` uses it.

### Changed

- `search()` is several times faster: each entry's lowercased name, definition and synonyms are joined once when the database is built, so a query is one substring test per entry instead of lowercasing every field on every call. Results and their order are unchanged (tested against the 1.0 algorithm).
- `import unimodpy` no longer imports `urllib.request` (and with it `http.client`, `ssl`, `email`): it is imported when `download()` runs, saving about 30 ms at import.

## [1.0.0] (2026-09-23)

First stable release: the public API now follows semantic versioning (breaking changes only in a new major version).

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
- `NeutralLoss.dict_composition` is typed `dict[str, int] | None` and `NeutralLoss.proforma_formula` `str | None`: a zero loss is `{}` / `""`, and `None` (with a `UserWarning` naming the bad token) means the composition could not be parsed. The server's `NeutralLoss.proforma_formula` is `str | None`, and the warning there names the parent `UNIMOD:<id>`.
- Server wire model `UnimodEntry` exposes the parent as `is_a`, like psimodpy. The old `parent_id` field is removed from REST and MCP responses.
- `load(source, refresh=True)` raises `ValueError("pass either source or refresh=True, not both")`, as in uniprotptmpy; `refresh` used to be silently ignored.
- `parse_delta_composition` raises `UnimodParseError` for a malformed token (`"H(2"`, `"H(x)"`) or a token that is neither an element symbol nor a known monosaccharide (`"Foo(2)"`). Unknown tokens used to be kept verbatim as dict keys and malformed counts raised a bare `ValueError`. `UnimodEntry.dict_composition` and `proforma_formula` catch it: they return `None` with a `UserWarning` naming the entry, so a new upstream monosaccharide never breaks loading, the server or `/data.json`. `NeutralLoss` does the same.
- MCP `search` validates `query` (non-empty) and `limit` (1-500), like the REST `/api/search`; out-of-range arguments return a tool error instead of an unbounded list.

Migration: read `entry.is_a` instead of `parent_id` from the server; call `download(force=True)` where you relied on `download()` always fetching; compare `spec.site == "K"` (works for enum members and raw strings) rather than `isinstance(spec.site, Site)`; catch `UnimodError` for duplicate ids; pass only one of `source` / `refresh=True` to `load`; treat `definition_ref == ""` as "no citations".

### Added

- `unimodpy.errors`: `UnimodError(Exception)` and `UnimodParseError(UnimodError, ValueError)`, exported from `unimodpy`.
- `/api/health` returns a typed `HealthResponse`; `dashboard_entries()` returns `DashboardEntry` TypedDicts.
- Classifiers `Development Status :: 5 - Production/Stable` and `Programming Language :: Python :: 3.14`; `Documentation` project URL. `SECURITY.md` and `CONTRIBUTING.md`.
- `UnimodEntry.accession` property: `"UNIMOD:21"`, the same string as the server's `accession` field.
- `UnimodDatabase.get(key, default=None)`: returns `db[key]` or `default`, never raises, as in psimodpy and uniprotptmpy.
- Tests recompute every entry's and every neutral loss's monoisotopic and average mass from its parsed composition against a frozen NIST table (pyteomics 5.0.1; generator in `tests/reference/`), plus Hypothesis property tests for the lookups. All 1560 compositions agree.

### Changed

- Bundled `UNIMOD.obo` refreshed to the 2026-02-17 upstream release: 1,561 terms (was 1,552). Loads without warnings.

### Fixed

- `get_by_id` (and `db[...]`, `in`, REST `/api/entries/{id}`, MCP `get_by_id`) accepts only plain ASCII digits after the optional `UNIMOD:` prefix. `int()` also took `"1_0"` (-> UNIMOD:10), `"+1"` and non-ASCII digits such as `"\u0661"`; those now return `None` / 404.
- `get_by_name` returns `None` and `search` returns `[]` for a non-`str` argument (`None`, `1`) instead of raising `AttributeError`.
- `download()` fetches over `https://www.unimod.org` (was `http`).
- `scripts/release_version.py sync --set X.Y.Z` also sets CITATION.cff `date-released` to today; CITATION.cff gains `date-released`.
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
