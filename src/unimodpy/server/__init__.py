"""HTTP API and MCP server for unimodpy.

Optional install: ``pip install unimodpy[server]``.

Run locally::

    uvicorn unimodpy.server.app:app --reload

Endpoints:
    GET  /api/health
    GET  /api/entries
    GET  /api/entries/{id}
    GET  /api/entries/by-name/{name}
    GET  /api/search?q=...
    POST /mcp                          (Model Context Protocol)
"""

from unimodpy.server.app import app, mcp

__all__ = ["app", "mcp"]
