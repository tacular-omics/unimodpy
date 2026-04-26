"""FastAPI app exposing the unimodpy database as REST and MCP."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, Response
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

import unimodpy
from unimodpy.server.dashboard import dashboard_entries
from unimodpy.server.schemas import serialize_entry

_db = unimodpy.load()
_PACKAGE = "unimodpy"


# Render dashboard payload once at import time.
_DATA_JSON = json.dumps(dashboard_entries(), separators=(",", ":")).encode()


# Locate the static dashboard. On Vercel the function bundle includes ``docs/``
# (see vercel.json includeFiles); locally it lives at the repo root.
def _load_dashboard_html() -> str | None:
    for candidate in (
        Path.cwd() / "docs" / "index.html",
        Path(__file__).resolve().parents[3] / "docs" / "index.html",
    ):
        try:
            if candidate.is_file():
                return candidate.read_text()
        except OSError:
            continue
    return None


_DASHBOARD_HTML = _load_dashboard_html()


# ---------------------------------------------------------------------------
# MCP server (mounted at /, exposes its own /mcp route)
# ---------------------------------------------------------------------------


def _build_mcp() -> FastMCP:
    mcp = FastMCP(
        _PACKAGE,
        instructions="Query the UNIMOD mass spectrometry modifications database.",
        stateless_http=True,
        # Public deployment (Vercel): host changes per request; disable Host-header
        # validation. Authentication, if needed, should be added separately.
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )

    @mcp.tool()
    def get_by_id(id: str) -> dict | None:
        """Look up a UNIMOD entry by ID. Accepts ``"1"`` or ``"UNIMOD:1"``."""
        entry = _db.get_by_id(id)
        return serialize_entry(entry) if entry else None

    @mcp.tool()
    def get_by_name(name: str) -> dict | None:
        """Look up a UNIMOD entry by exact name (case-insensitive)."""
        entry = _db.get_by_name(name)
        return serialize_entry(entry) if entry else None

    @mcp.tool()
    def search(query: str, limit: int = 25) -> list[dict]:
        """Full-text search over name, definition, and synonyms. Returns up to ``limit`` results."""
        return [serialize_entry(e) for e in _db.search(query)[:limit]]

    return mcp


# Module-level instance for inspection / re-export.
mcp = _build_mcp()


# ---------------------------------------------------------------------------
# REST API
# ---------------------------------------------------------------------------


# Vercel doesn't fire ASGI lifespan events, and StreamableHTTPSessionManager.run()
# can only be called once per instance, so we build a fresh FastMCP per request.
class _MCPWrapper:
    async def __call__(self, scope, receive, send) -> None:
        m = _build_mcp()
        http_app = m.streamable_http_app()
        async with m.session_manager.run():
            await http_app(scope, receive, send)


app = FastAPI(
    title="unimodpy API",
    description="REST + MCP interface to the UNIMOD modifications database.",
    version=unimodpy.__version__,
)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def dashboard() -> str:
    if _DASHBOARD_HTML is None:
        raise HTTPException(status_code=404, detail="Dashboard not bundled with deployment")
    return _DASHBOARD_HTML


@app.get("/data.json", include_in_schema=False)
def dashboard_data() -> Response:
    return Response(
        content=_DATA_JSON,
        media_type="application/json",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@app.get("/api/health")
def health() -> dict:
    return {
        "ok": True,
        "package": _PACKAGE,
        "version": unimodpy.__version__,
        "count": len(_db),
    }


@app.get("/api/entries")
def list_entries(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict:
    entries = list(_db)
    page = entries[offset : offset + limit]
    return {
        "total": len(entries),
        "limit": limit,
        "offset": offset,
        "items": [serialize_entry(e) for e in page],
    }


@app.get("/api/entries/{id}")
def get_entry(id: str) -> dict:
    entry = _db.get_by_id(id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"No entry for id={id!r}")
    return serialize_entry(entry)


@app.get("/api/entries/by-name/{name}")
def get_entry_by_name(name: str) -> dict:
    entry = _db.get_by_name(name)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"No entry for name={name!r}")
    return serialize_entry(entry)


@app.get("/api/search")
def search_entries(
    q: str = Query(..., min_length=1),
    limit: int = Query(50, ge=1, le=500),
) -> dict:
    results = _db.search(q)
    return {
        "query": q,
        "total": len(results),
        "limit": limit,
        "items": [serialize_entry(e) for e in results[:limit]],
    }


# Mount MCP at the root; its inner app exposes /mcp.
app.mount("/", _MCPWrapper())
