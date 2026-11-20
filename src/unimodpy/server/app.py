"""FastAPI app exposing the unimodpy database as REST and MCP."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.routing import APIRoute
from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import Field

import unimodpy
from unimodpy.server.dashboard import dashboard_entries
from unimodpy.server.models import (
    EntryListResponse,
    HealthResponse,
    SearchResponse,
    UnimodEntry,
    UnimodSummary,
    to_unimod_entry,
    to_unimod_summary,
)

_db = unimodpy.load()
_PACKAGE = "unimodpy"


# Render dashboard payload once at import time.
_DATA_JSON = json.dumps(dashboard_entries(_db), separators=(",", ":")).encode()


# Locate the static dashboard. On Vercel the function bundle includes ``docs/``
# (see vercel.json includeFiles); locally it lives at the repo root.
def _load_dashboard_html() -> str | None:
    for candidate in (
        Path.cwd() / "docs" / "index.html",
        Path(__file__).resolve().parents[3] / "docs" / "index.html",
    ):
        try:
            if candidate.is_file():
                return candidate.read_text(encoding="utf-8")
        except OSError:
            continue
    return None


_DASHBOARD_HTML = _load_dashboard_html()


# ---------------------------------------------------------------------------
# MCP server (mounted at /, exposes its own /mcp route)
# ---------------------------------------------------------------------------


def _build_mcp() -> MCPServer:
    mcp = MCPServer(
        _PACKAGE,
        instructions="Query the UNIMOD mass spectrometry modifications database.",
    )

    @mcp.tool()
    def get_by_id(id: str, include_hidden: bool = False) -> UnimodEntry | None:
        """Look up a UNIMOD entry by ID. Accepts ``"1"`` or ``"UNIMOD:1"``.

        Hidden specificities (rarely-used or deprecated sites flagged in
        UNIMOD with ``hidden=true``) are excluded by default. Pass
        ``include_hidden=True`` to see every site.
        """
        entry = _db.get_by_id(id)
        if entry is None:
            return None
        return to_unimod_entry(entry, include_hidden=include_hidden)

    @mcp.tool()
    def get_by_name(name: str, include_hidden: bool = False) -> UnimodEntry | None:
        """Look up a UNIMOD entry by exact name (case-insensitive).

        See ``get_by_id`` for the meaning of ``include_hidden``.
        """
        entry = _db.get_by_name(name)
        if entry is None:
            return None
        return to_unimod_entry(entry, include_hidden=include_hidden)

    @mcp.tool()
    def search(
        query: Annotated[str, Field(min_length=1)], limit: Annotated[int, Field(ge=1, le=500)] = 25
    ) -> list[UnimodSummary]:
        """Full-text search over name, definition, and synonyms.

        ``query`` must be non-empty. Returns up to ``limit`` (1-500) lightweight
        summaries.  Call ``get_by_id`` on any returned ``id`` to fetch the full entry.
        """
        return [to_unimod_summary(e) for e in _db.search(query)[:limit]]

    return mcp


# Module-level instance for inspection / re-export.
mcp = _build_mcp()


# ---------------------------------------------------------------------------
# REST API
# ---------------------------------------------------------------------------


# Vercel doesn't fire ASGI lifespan events, and StreamableHTTPSessionManager.run()
# can only be called once per instance, so we build a fresh MCPServer per request.
class _MCPWrapper:
    async def __call__(self, scope, receive, send) -> None:
        m = _build_mcp()
        http_app = m.streamable_http_app(
            stateless_http=True,
            # Public deployment (Vercel): host changes per request; disable Host-header
            # validation. Authentication, if needed, should be added separately.
            transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
        )
        async with m.session_manager.run():
            await http_app(scope, receive, send)


def _declared_query_params(route: APIRoute) -> frozenset[str]:
    """The query-parameter names ``route`` itself declares.

    Read from the route's own parsed signature rather than from a list kept here, so a
    route added later is covered without touching this function and a renamed parameter
    cannot drift from the check.
    """
    return frozenset(field.alias for field in route.dependant.query_params)


# The dashboard page and its payload are opened in a browser, where a shared link may
# carry a tracking parameter; answering 422 would hide the page over a harmless extra.
# The API routes are machine-facing, where silently ignoring a parameter is the worse
# failure: a client asking for ``include_hiden=true`` got every hidden specificity
# dropped, the same body as the default, and no hint that the name was not read.
_UNVALIDATED_QUERY_PATHS = frozenset({"/", "/data.json"})


def _reject_unknown_query_params(request: Request) -> None:
    """422 for a query parameter the matched route does not declare.

    Registered once as an app-wide dependency, so every API route gets it and no route
    carries its own copy. Mounted sub-applications (``/mcp``) do not run app
    dependencies and are unaffected.
    """
    route = request.scope.get("route")
    if not isinstance(route, APIRoute) or route.path in _UNVALIDATED_QUERY_PATHS:
        return
    accepted = _declared_query_params(route)
    unknown = sorted(set(request.query_params) - accepted)
    if not unknown:
        return
    names = ", ".join(repr(name) for name in unknown)
    allowed = ", ".join(sorted(accepted)) if accepted else "no query parameters"
    raise HTTPException(
        status_code=422,
        detail=f"unknown query parameter{'s' if len(unknown) > 1 else ''} {names}; {route.path} accepts: {allowed}",
    )


app = FastAPI(
    title="unimodpy API",
    description="REST + MCP interface to the UNIMOD modifications database.",
    version=unimodpy.__version__,
    dependencies=[Depends(_reject_unknown_query_params)],
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


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(ok=True, package=_PACKAGE, version=unimodpy.__version__, count=len(_db))


@app.get("/api/entries", response_model=EntryListResponse)
def list_entries(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    include_hidden: bool = Query(False),
) -> EntryListResponse:
    entries = list(_db)
    page = entries[offset : offset + limit]
    return EntryListResponse(
        total=len(entries),
        limit=limit,
        offset=offset,
        items=[to_unimod_entry(e, include_hidden=include_hidden) for e in page],
    )


@app.get("/api/entries/{id}", response_model=UnimodEntry)
def get_entry(id: str, include_hidden: bool = Query(False)) -> UnimodEntry:
    entry = _db.get_by_id(id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"No entry for id={id!r}")
    return to_unimod_entry(entry, include_hidden=include_hidden)


@app.get("/api/entries/by-name/{name:path}", response_model=UnimodEntry)
def get_entry_by_name(name: str, include_hidden: bool = Query(False)) -> UnimodEntry:
    entry = _db.get_by_name(name)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"No entry for name={name!r}")
    return to_unimod_entry(entry, include_hidden=include_hidden)


@app.get("/api/search", response_model=SearchResponse)
def search_entries(
    q: str = Query(..., min_length=1),
    limit: int = Query(50, ge=1, le=500),
) -> SearchResponse:
    results = _db.search(q)
    return SearchResponse(
        query=q,
        total=len(results),
        limit=limit,
        items=[to_unimod_summary(e) for e in results[:limit]],
    )


# Mount MCP at the root; its inner app exposes /mcp.
app.mount("/", _MCPWrapper())
