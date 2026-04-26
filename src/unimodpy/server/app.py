"""FastAPI app exposing the unimodpy database as REST and MCP."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

import unimodpy
from unimodpy.server.schemas import serialize_entry

_db = unimodpy.load()
_PACKAGE = "unimodpy"


# ---------------------------------------------------------------------------
# MCP server (mounted at /, exposes its own /mcp route)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# REST API
# ---------------------------------------------------------------------------


# Vercel doesn't fire ASGI lifespan events, so we start the session manager per request.
class _MCPWrapper:
    def __init__(self, mcp: FastMCP) -> None:
        self._inner = mcp.streamable_http_app()
        self._mcp = mcp

    async def __call__(self, scope, receive, send) -> None:
        async with self._mcp.session_manager.run():
            await self._inner(scope, receive, send)


app = FastAPI(
    title="unimodpy API",
    description="REST + MCP interface to the UNIMOD modifications database.",
    version=unimodpy.__version__,
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
app.mount("/", _MCPWrapper(mcp))
