"""FastAPI app exposing the unimodpy database as REST and MCP."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, Response
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

import unimodpy
from unimodpy.database import MassType
from unimodpy.server.dashboard import dashboard_entries
from unimodpy.server.models import (
    EntryListResponse,
    SearchResponse,
    UnimodEntry,
    UnimodSummary,
    to_unimod_entry,
    to_unimod_summary,
)

_db = unimodpy.load()
_PACKAGE = "unimodpy"

_DATA_JSON = json.dumps(dashboard_entries(), separators=(",", ":")).encode()


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


def _split_residues(residues: str | None) -> list[str] | None:
    if residues is None:
        return None
    parts = [r.strip() for r in residues.split(",") if r.strip()]
    return parts or None


# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------


def _build_mcp() -> FastMCP:
    mcp = FastMCP(
        _PACKAGE,
        instructions="Query the UNIMOD mass spectrometry modifications database.",
        stateless_http=True,
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )

    @mcp.tool()
    def get_by_id(id: str, include_hidden: bool = False) -> UnimodEntry | None:
        """Look up a UNIMOD entry by ID. Accepts ``"1"`` or ``"UNIMOD:1"``."""
        entry = _db.get_by_id(id)
        if entry is None:
            return None
        return to_unimod_entry(entry, include_hidden=include_hidden)

    @mcp.tool()
    def get_by_name(name: str, include_hidden: bool = False) -> UnimodEntry | None:
        """Look up a UNIMOD entry by exact name (case-insensitive)."""
        entry = _db.get_by_name(name)
        if entry is None:
            return None
        return to_unimod_entry(entry, include_hidden=include_hidden)

    @mcp.tool()
    def search(query: str, limit: int = 25) -> list[UnimodSummary]:
        """Full-text search over name, definition, and synonyms."""
        return [to_unimod_summary(e) for e in _db.search(query)[:limit]]

    @mcp.tool()
    def find(
        text: str | None = None,
        mass_min: float | None = None,
        mass_max: float | None = None,
        mass_type: str = "mono",
        residues: list[str] | None = None,
        position: str | None = None,
        classification: str | None = None,
        has_neutral_loss: bool | None = None,
        include_hidden: bool = False,
        limit: int = 25,
    ) -> list[UnimodSummary]:
        """Fine-grained AND-combined search.

        Filters: ``text`` (substring over name/def/synonyms), delta mass range
        on ``mono`` or ``avg`` mass, ``residues`` against specificity sites
        (e.g. ``[\"S\", \"T\", \"Y\"]`` or ``[\"N-term\"]``), ``position``
        (e.g. ``\"Anywhere\"``, ``\"Any N-term\"``), ``classification`` (e.g.
        ``\"N-linked glycosylation\"``), and ``has_neutral_loss``.
        """
        mt: MassType = "mono" if mass_type != "avg" else "avg"
        results = _db.find(
            text=text,
            mass_min=mass_min,
            mass_max=mass_max,
            mass_type=mt,
            residues=residues,
            position=position,
            classification=classification,
            has_neutral_loss=has_neutral_loss,
            include_hidden=include_hidden,
            limit=limit,
        )
        return [to_unimod_summary(e) for e in results]

    return mcp


mcp = _build_mcp()


# ---------------------------------------------------------------------------
# REST API
# ---------------------------------------------------------------------------


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


@app.get("/api/entries/by-name/{name}", response_model=UnimodEntry)
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


@app.get("/api/find", response_model=list[UnimodSummary])
def find_entries(
    text: str | None = Query(None),
    mass_min: float | None = Query(None),
    mass_max: float | None = Query(None),
    mass_type: str = Query("mono", pattern="^(mono|avg)$"),
    residues: str | None = Query(None, description="Comma-separated residue codes"),
    position: str | None = Query(None),
    classification: str | None = Query(None),
    has_neutral_loss: bool | None = Query(None),
    include_hidden: bool = Query(False),
    limit: int = Query(50, ge=1, le=500),
) -> list[UnimodSummary]:
    results = _db.find(
        text=text,
        mass_min=mass_min,
        mass_max=mass_max,
        mass_type=cast(MassType, mass_type),
        residues=_split_residues(residues),
        position=position,
        classification=classification,
        has_neutral_loss=has_neutral_loss,
        include_hidden=include_hidden,
        limit=limit,
    )
    return [to_unimod_summary(e) for e in results]


app.mount("/", _MCPWrapper())
