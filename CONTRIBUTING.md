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

`just install` runs `uv sync --all-extras`, which installs the dev group and the optional
`server` extra (`fastapi`, `uvicorn`, `mcp`, `pydantic`). The extra is what the tests covering
the REST API and the MCP endpoint need, and a plain `uv sync` leaves it out. Those tests then
do not run, at two different scopes:

- `tests/test_server.py` calls `pytest.importorskip` at **module** scope, so none of its
  tests are collected and the module reports as a **single** skip, however many it hides.
- `tests/test_prerelease_fixes.py` calls it **inside** individual tests, so those are
  collected and then skipped.

So if you ever install without the extra, neither the collected total nor the skip count
tells you what ran: the total omits the module-scope tests entirely, and one skip line stands
for a whole module. Read the **passed** count, which is the only one that moves by the number
of tests you gained, and `uv pip list` to see what is actually installed.

Install the commit hooks once per clone with `uvx pre-commit install`. On every
commit they run `ruff check`, `ruff format --check` and a few file checks
(`uvx pre-commit run --all-files` runs them on everything). Type checks and
tests are not in the hooks. Run `just check` for those.

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
- Do not change the version number. The maintainers set it when releasing.
- CI must pass: lint, type check, tests on Python 3.12 to 3.14, and the wheel build.

## CLAUDE.md and AI agents

`CLAUDE.md` is the maintained developer guide: commands, architecture,
conventions and known gotchas. `AGENTS.md` points other coding agents to it.
Read it before a larger change, and update it in the same pull request when your
change makes part of it wrong. AI-assisted contributions are welcome. You are
responsible for reviewing and testing what you submit.
