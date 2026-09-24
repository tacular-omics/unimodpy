# unimodpy: Claude Code guide

## Project overview

unimodpy parses and queries the [UNIMOD](http://www.unimod.org/) mass-spectrometry
modifications database. It bundles `src/unimodpy/data/UNIMOD.obo` (1,561 terms,
including the root node `UNIMOD:0`), parses it into frozen dataclasses, and exposes
an in-memory `UnimodDatabase` with lookup by ID, name and free-text search. The core
package has **no runtime dependencies** and works offline.

An optional `server` extra (`fastapi`, `uvicorn`, `mcp>=2.1.1,<3`) adds a FastAPI
REST API plus an MCP endpoint. The same app is deployed on Vercel at
<https://unimod.tacular.dev> and also serves the browser dashboard. A static copy of
the dashboard is published to GitHub Pages (<https://tacular-omics.github.io/unimodpy/>).

Place in the tacular-omics graph: tier 0, no sibling dependencies. Siblings
`psimodpy` and `uniprotptmpy` are the same design for PSI-MOD and UniProt PTM.
`tacular` bundles its **own** UNIMOD copy and does not import unimodpy. Downstream
users outside the workspace: `peff_digest`, `peff_uniprot_fetcher`.

## Commands

```bash
just test            # uv run pytest tests            (~220 tests, ~8 s)
just lint            # uv run ruff check src tests
just ty              # uv run ty check src
just check           # lint + ty + test  (the recipe comment says "type checking"; it runs all three)
just format          # ruff isort --fix + ruff format on src and tests  (rewrites files)
just build           # uv build, then list the *.obo files inside the wheel
just check-version   # python scripts/release_version.py check
just --list          # everything, including set-version / sync-version (overseer only)
```

`just` with no recipe runs `default: lint format check test`, which **rewrites files**
(format). CI also runs `ruff format --check src tests` (the justfile only formats),
`ty check src`, `release_version.py check`, pytest on
3.12/3.13/3.14 plus macOS and Windows, a `--resolution lowest-direct` job, and a wheel
check that `UNIMOD.obo` is packaged. Before pushing, also run
`uv run ruff format --check src tests`.

Server, locally:

```bash
uv run uvicorn unimodpy.server.app:app --reload        # http://127.0.0.1:8000, /docs for OpenAPI
uv run python -c "from unimodpy.server import mcp; mcp.run()"   # MCP over stdio (no console script)
uv run python scripts/export_json.py                   # writes docs/data.json for the Pages site
```

## Architecture

```
src/unimodpy/
  __init__.py      public re-exports + __version__ (the version source)
  models.py        Site / Position / Classification StrEnums; NeutralLoss, Specificity,
                   UnimodEntry frozen slots dataclasses (dict_composition, proforma_formula)
  parser.py        parse_obo(path) -> UnimodDatabase (streams [Term] blocks); load()
  database.py      UnimodDatabase: id/name indexes, search, __getitem__, write_tsv/write_obo
  errors.py        UnimodError, UnimodParseError, UnimodKeyError(UnimodError, KeyError)
  _formula.py      delta_composition parsing (monosaccharide expansion, isotopes) + Hill formula
  _download.py     download() from https://www.unimod.org/obo/unimod.obo to ~/.cache/unimodpy/
  _tabular.py      write_tsv (TSV/CSV, one row per entry, specificities joined with "; ")
  _obo_writer.py   write_obo (round-trips: parse_obo(write_obo(db)) == db, header included)
  data/UNIMOD.obo  bundled database, shipped in the wheel
  server/
    __init__.py    re-exports app, mcp; docstring lists endpoints
    app.py         FastAPI app, REST routes, MCPServer + per-request _MCPWrapper mounted at "/"
    models.py      pydantic wire models + to_unimod_entry / to_unimod_summary converters
    references.py  parse_definition_ref: "RESID:AA0036, URL:http\://..." -> list[Reference]
    dashboard.py   dashboard_entries(db=None): payload for /data.json and docs/data.json (skips id 0)
api/index.py       Vercel entry point, just `from unimodpy.server.app import app`
docs/index.html    static dashboard; fetches data.json relative to itself
scripts/           export_json.py (Pages data), audit_obo.py (unparsed OBO fields),
                   print_entries.py, release_version.py (shared release tool, do not hand-edit)
vercel.json        installCommand `uv pip install '.[server]'`; one Python function
                   (api/index.py, maxDuration 10 s, includeFiles docs/**). No rewrites:
                   the Vercel Python runtime routes every path to the FastAPI app itself
```

Data flow: `load()` -> `importlib.resources` path to `data/UNIMOD.obo` -> `parse_obo`
-> `_build_entry` per `[Term]` block (xrefs split into scalar fields, `spec_N_*` and
`spec_N_neutral_loss_M_*`) -> `UnimodDatabase`. The server builds one database at
import time and converts dataclasses to pydantic models per response.

### Server routes (`server/app.py`)

| route | purpose |
|---|---|
| `GET /` | dashboard HTML (`docs/index.html`; 404 if not bundled) |
| `GET /data.json` | dashboard payload, 1,560 entries, `Cache-Control: max-age=3600` |
| `GET /api/health` | `{ok, package, version, count}` |
| `GET /api/entries?limit=50&offset=0&include_hidden=false` | paged full entries (limit 1-500); includes root node id 0 |
| `GET /api/entries/{id}?include_hidden=false` | `21` or `UNIMOD:21`; 404 if missing |
| `GET /api/entries/by-name/{name}?include_hidden=false` | exact, case-insensitive; 404 if missing |
| `GET /api/search?q=...&limit=50` | substring search -> `{query,total,limit,items:[UnimodSummary]}`; `q` required |
| `POST /mcp` | MCP streamable HTTP, stateless, JSON-RPC; accept `application/json, text/event-stream` |
| `GET /docs`, `/redoc`, `/openapi.json` | FastAPI defaults |

MCP tools (server name `unimodpy`): `get_by_id(id, include_hidden=False)`,
`get_by_name(name, include_hidden=False)`, `search(query, limit=25)` (query non-empty,
limit 1-500). All return typed
pydantic output (`structuredContent` + `outputSchema`). Hidden specificities are
dropped unless `include_hidden=True` (Phospho: 2 visible, 8 total).

Connecting a client: `claude mcp add unimod https://unimod.tacular.dev/mcp --transport http`
(or `http://localhost:8000/mcp` for a local uvicorn).

## Public API

From `unimodpy/__init__.py`:

- Mass search (1.1): `db.search_mass(delta, *, tolerance=0.01, tolerance_unit="da", site=None, position=None)` over `delta_mono_mass`, returns `(entry, delta - mass)` closest first; `db.get_by_site(site)`. The index and site/position rules live in `_mass.py`, identical in psimodpy, unimodpy and uniprotptmpy: keep the three copies in sync.
- `entry.get_mass(*, monoisotopic=True)` (1.1) returns `delta_mono_mass`/`delta_avge_mass`; `search_mass` indexes `get_mass()`.
- Loading: `load(source=None, *, refresh=False, cache=False)`, `parse_obo(path)`, `download(dest=None, *, force=False)`
- Writing: `write_tsv(entries, path, *, delimiter="\t")`, `write_obo(entries, path, *, header_lines=())`
- Database: `UnimodDatabase` (`get_by_id`, `get_by_name`, `search`, `db[...]`, `len`, iteration,
  `write_tsv`, `write_obo`, `header_lines`)
- Models: `UnimodEntry`, `Specificity`, `NeutralLoss`
- Enums: `Site` (23), `Position` (5), `Classification` (14); unknown upstream values stay raw `str` (warning)
- Errors: `UnimodError`, `UnimodParseError(UnimodError, ValueError)`, `UnimodKeyError(UnimodError, KeyError)` (`errors.py`)
- `__version__`

`unimodpy.server` (extra): `app`, `mcp`; `unimodpy.server.models` holds the wire models.

## Conventions

- Python >= 3.12, ruff line length 120, rules E W F I B UP. `ty check src` must pass.
- Models are `@dataclass(frozen=True, slots=True)`; collections are tuples. Keep them immutable.
- Lookups return `None` when missing; only `db[...]` raises (`UnimodKeyError`, a `KeyError`).
- Short Google-style docstrings; type hints carry the types.
- The server's wire shape is defined once in `server/models.py`, shared by REST and MCP.
  Change it there, not in `app.py`.
- Tests: `tests/`, session-scoped `db` fixture in `conftest.py`. `test_server.py`
  `importorskip`s fastapi/mcp and deliberately calls `TestClient` **without** a context
  manager so no ASGI lifespan fires, like Vercel.

## Gotchas

- **Vercel does not run ASGI lifespan**, and a `StreamableHTTPSessionManager` can only be
  `run()` once. That is why `_MCPWrapper` builds a fresh `MCPServer` per request. Do not
  "simplify" it into a single mounted `streamable_http_app()`.
- DNS-rebinding protection is disabled on the MCP transport because the Vercel host
  changes per request. There is no auth; the endpoint is public and read-only.
- The MCP app is mounted at `/`, so it catches every path the FastAPI routes do not.
  Add new REST routes **before** `app.mount("/", ...)`.
- `GET /mcp` opens an SSE stream and blocks; in tests use `POST`.
- The dashboard HTML is looked up at `Path.cwd()/docs/index.html` then at the repo root
  relative to `app.py`. From an installed wheel neither exists and `/` returns 404.
- `id` 0 is the UNIMOD root node: every xref-derived field is `None`. `/data.json`
  excludes it; `/api/entries` and `len(db)` include it.
- `db[key]` tries the ID first, then the name. `get_by_id("Acetyl")` returns `None`.
- `load(source, refresh=True)` raises `ValueError` (pass one or the other).
- `NeutralLoss.composition` is UNIMOD's raw string. Zero-loss entries use `"0"`, which
  `_formula` treats as no atoms: `dict_composition` is `{}` and `proforma_formula` is `""`.
  One loss (UNIMOD:1010) uses `"Water"`, which `MONOSACCHARIDE_FORMULAS` expands to `H2O`.
- `_formula.MONOSACCHARIDE_FORMULAS` holds residue (minus water) formulas; any other token
  must be an element symbol (optionally isotope-prefixed, `13C`), else `parse_delta_composition`
  raises `UnimodParseError`; `UnimodEntry` and `NeutralLoss` `dict_composition`/`proforma_formula` turn
  that into `None` + `UserWarning` (via `models._lenient_composition`; the server names the
  parent `UNIMOD:<id>` for a loss). A new upstream monosaccharide must be added there.
- Changing the MCP major version is breaking for the `server` extra (0.2.0 moved from
  FastMCP/mcp 1.x to `MCPServer`/mcp 2.x).
- Vercel: without `installCommand` the runtime installs from `pyproject.toml`/`uv.lock`
  with no extras and every request fails with `ModuleNotFoundError: fastapi`. A
  catch-all rewrite to `/api/index` makes every request 404. Keep both as they are.

## Releasing

Only the tacular-omics overseer bumps versions or publishes. See `just --list`
(`set-version`, `sync-version`, `check-version`). The version lives only in
`src/unimodpy/__init__.py` (`__version__`, read by `[tool.hatch.version]`);
`scripts/release_version.py sync` copies it to `CITATION.cff`. `.zenodo.json` carries no
version. `CHANGELOG.md` uses `## [X.Y.Z] (YYYY-MM-DD)` sections under `## [Unreleased]`.
PyPI upload runs from `.github/workflows/publish.yml` on a published GitHub release.
The Vercel project (unimod.tacular.dev) builds from this repo via `vercel.json`
(`installCommand`); check the Vercel dashboard before assuming which branch it tracks.

## Workspace note

This repo is also developed inside the tacular-omics uv workspace
(`~/Repos/tacular-omics/packages/unimodpy`); there `uv run` uses the shared `.venv` and
the root `uv.lock`, not this repo's. See the workspace CLAUDE.md.
