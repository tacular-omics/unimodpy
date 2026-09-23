# Copilot instructions

The canonical guide is [`CLAUDE.md`](../CLAUDE.md) at the repo root. Read it first.

Key rules:

1. Use `just` recipes (`just test`, `just lint`, `just ty`, `just check`) or `uv run`;
   never `pip install`. CI also runs `ruff check src tests` and `ruff format --check src tests`.
2. The core package has zero runtime dependencies. FastAPI, uvicorn and mcp belong to the
   `server` extra only; never import them outside `src/unimodpy/server/`.
3. Models are frozen `slots=True` dataclasses with tuple fields; keep them immutable.
   Lookups return `None` when missing.
4. Do not simplify the per-request `_MCPWrapper` in `server/app.py`: Vercel runs no ASGI
   lifespan. Add REST routes before `app.mount("/", ...)`.
5. Never edit `src/unimodpy/data/UNIMOD.obo` by hand, and never bump versions: only the
   tacular-omics overseer releases.
