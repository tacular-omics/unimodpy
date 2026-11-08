# Contributing to unimodpy

Bug reports, fixes and new features are welcome. Use the
[issue tracker](https://github.com/tacular-omics/unimodpy/issues) for bugs and
questions, with a minimal example and the unimodpy and Python versions. Report
security problems privately as described in [SECURITY.md](SECURITY.md).

## Development setup

You need Python 3.12 or newer, [uv](https://docs.astral.sh/uv/) and
[just](https://just.systems/).

```bash
git clone https://github.com/tacular-omics/unimodpy.git
cd unimodpy
just install
```

`just --list` shows the other recipes.

`just install` runs `uv sync`, which installs the dev group but **not** the optional
`server` extra. Two test modules reach for it at two different scopes, and each scope
hides in a different number, so it takes both to see what a plain install leaves out:

| install | collected | result |
|---|---|---|
| `uv sync` | 344 | 342 passed, 3 skipped |
| `uv sync --all-extras` | 363 | 363 passed |

`tests/test_server.py` calls `pytest.importorskip` at **module** scope, so its 19 tests are
never collected at all and the whole module reports as one skip line. The two `fastapi`
tests in `tests/test_prerelease_fixes.py` skip at **function** scope, so they are collected
and then skipped. 21 tests are therefore blocked by a plain install - a number neither the
collected totals (19) nor the skip count (3 lines) gives on its own, and a green 344 says
nothing about the REST or MCP endpoints. For the whole suite:

```bash
uv sync --all-extras
```

Install the commit hooks once per clone with `uvx pre-commit install`. On every
commit they run `ruff check`, `ruff format --check` and a few file checks
(`uvx pre-commit run --all-files` runs them on everything). Type checks and
tests are not in the hooks; run `just check` for those.

## Running checks

CI runs these on every pull request. Run them before you push:

```bash
uv run ruff check src tests
uv run ruff format --check src tests
uv run ty check src
uv run pytest tests
python scripts/release_version.py check
```

## Pull requests

- Branch from `main` and keep each pull request to one change.
- Add tests for new behaviour and fixed bugs.
- Add a line under `## [Unreleased]` in `CHANGELOG.md` for user-visible changes.
- Do not change the version number; the maintainers set it when releasing.
- CI must pass: lint, type check, tests on Python 3.12 to 3.14, and the wheel build.

## CLAUDE.md and AI agents

`CLAUDE.md` is the maintained developer guide: commands, architecture,
conventions and known gotchas. `AGENTS.md` points other coding agents to it.
Read it before a larger change, and update it in the same pull request when your
change makes part of it wrong. AI-assisted contributions are welcome; you are
responsible for reviewing and testing what you submit.
