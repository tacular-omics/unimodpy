"""End-to-end MCP + REST shape tests for the unimodpy server.

The MCP tests deliberately *don't* enter ``TestClient`` as a context manager,
so no ASGI lifespan events fire.  This mirrors how Vercel's serverless
runtime invokes the app — every request is a cold ASGI call — and catches
regressions in our per-request session lifecycle handling alongside
structural guarantees about the new typed responses.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("mcp")

from fastapi.testclient import TestClient  # noqa: E402

from unimodpy.server.app import app  # noqa: E402
from unimodpy.server.models import UnimodEntry, UnimodSummary  # noqa: E402
from unimodpy.server.references import parse_definition_ref  # noqa: E402

_MCP_HEADERS = {"accept": "application/json, text/event-stream"}
_INIT_PARAMS = {
    "protocolVersion": "2025-06-18",
    "capabilities": {},
    "clientInfo": {"name": "pytest", "version": "0"},
}


def _parse_sse(body: str) -> dict[str, Any]:
    """Pull the JSON-RPC payload out of an SSE response."""
    for line in body.splitlines():
        if line.startswith("data:"):
            return json.loads(line[5:].strip())
    raise AssertionError(f"no data: line in SSE body: {body!r}")


def _mcp(client: TestClient, method: str, params: dict | None = None, *, req_id: int = 1) -> dict[str, Any]:
    payload = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params or {}}
    r = client.post("/mcp", json=payload, headers=_MCP_HEADERS)
    assert r.status_code == 200, f"{method} returned {r.status_code}: {r.text}"
    return _parse_sse(r.text)


@pytest.fixture
def mcp_client() -> TestClient:
    """A TestClient *not* entered as context manager — no lifespan events."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# References parser
# ---------------------------------------------------------------------------


def test_parse_definition_ref_handles_comma_separated_tokens() -> None:
    refs = parse_definition_ref("RESID:AA0048, PMID:11999733, URL:http\\://example.org/x")
    assert [(r.type, r.accession, r.value) for r in refs] == [
        ("RESID", "AA0048", None),
        ("PMID", "11999733", None),
        ("URL", None, "http://example.org/x"),
    ]


def test_parse_definition_ref_empty_returns_empty_list() -> None:
    assert parse_definition_ref("") == []
    assert parse_definition_ref(None) == []


def test_parse_definition_ref_no_colon_falls_back_to_misc() -> None:
    refs = parse_definition_ref("loose-token")
    assert len(refs) == 1
    assert refs[0].type == "Misc"
    assert refs[0].value == "loose-token"


def test_parse_definition_ref_strips_trailing_commas() -> None:
    refs = parse_definition_ref("PMID:1234,")
    assert [(r.type, r.accession) for r in refs] == [("PMID", "1234")]


# ---------------------------------------------------------------------------
# tools/list — outputSchema is emitted for every tool
# ---------------------------------------------------------------------------


def test_tools_list_includes_output_schema(mcp_client: TestClient) -> None:
    _mcp(mcp_client, "initialize", _INIT_PARAMS)
    resp = _mcp(mcp_client, "tools/list", req_id=2)
    tools = {t["name"]: t for t in resp["result"]["tools"]}
    assert set(tools) == {"get_by_id", "get_by_name", "search"}
    for name, tool in tools.items():
        assert tool.get("outputSchema"), f"{name} is missing outputSchema"


# ---------------------------------------------------------------------------
# tools/call — both content and structuredContent
# ---------------------------------------------------------------------------


def test_get_by_id_returns_structured_content(mcp_client: TestClient) -> None:
    _mcp(mcp_client, "initialize", _INIT_PARAMS)
    resp = _mcp(
        mcp_client,
        "tools/call",
        {"name": "get_by_id", "arguments": {"id": "1"}},
        req_id=2,
    )
    result = resp["result"]
    assert result["content"], "text fallback content missing"
    assert result["content"][0]["type"] == "text"
    sc = result["structuredContent"]
    # Optional return type → wrapped in {"result": ...}
    entry = sc["result"]
    assert entry is not None
    UnimodEntry.model_validate(entry)
    assert entry["accession"] == "UNIMOD:1"
    assert "is_a" not in entry, "old is_a key leaked into response"
    assert "record_id" not in entry, "internal record_id leaked into response"
    assert "date_time_posted" not in entry
    assert isinstance(entry["references"], list)
    assert entry["references"], "UNIMOD:1 should have parsed references"
    assert {"type"} <= set(entry["references"][0])


def test_get_by_id_missing_returns_null_result(mcp_client: TestClient) -> None:
    _mcp(mcp_client, "initialize", _INIT_PARAMS)
    resp = _mcp(
        mcp_client,
        "tools/call",
        {"name": "get_by_id", "arguments": {"id": "999999"}},
        req_id=2,
    )
    sc = resp["result"]["structuredContent"]
    assert sc == {"result": None}


def test_get_by_id_hidden_filter_default_excludes_hidden(mcp_client: TestClient) -> None:
    _mcp(mcp_client, "initialize", _INIT_PARAMS)
    default = _mcp(
        mcp_client,
        "tools/call",
        {"name": "get_by_id", "arguments": {"id": "1"}},
        req_id=2,
    )["result"]["structuredContent"]["result"]
    full = _mcp(
        mcp_client,
        "tools/call",
        {"name": "get_by_id", "arguments": {"id": "1", "include_hidden": True}},
        req_id=3,
    )["result"]["structuredContent"]["result"]

    assert len(default["specificities"]) <= len(full["specificities"])
    assert all(not s["hidden"] for s in default["specificities"])


def test_search_returns_summaries_not_full_entries(mcp_client: TestClient) -> None:
    _mcp(mcp_client, "initialize", _INIT_PARAMS)
    resp = _mcp(
        mcp_client,
        "tools/call",
        {"name": "search", "arguments": {"query": "acetyl", "limit": 3}},
        req_id=2,
    )
    items = resp["result"]["structuredContent"]["result"]
    assert isinstance(items, list)
    assert items, "search should return at least one match for 'acetyl'"
    for item in items:
        UnimodSummary.model_validate(item)
        assert "specificities" not in item
        assert "definition" not in item
        assert "references" not in item


# ---------------------------------------------------------------------------
# REST shape
# ---------------------------------------------------------------------------


def test_rest_get_entry_shape_matches_pydantic() -> None:
    with TestClient(app) as client:
        r = client.get("/api/entries/1")
        assert r.status_code == 200
        UnimodEntry.model_validate(r.json())


def test_rest_search_returns_summaries() -> None:
    with TestClient(app) as client:
        r = client.get("/api/search", params={"q": "acetyl", "limit": 2})
        assert r.status_code == 200
        body = r.json()
        assert {"query", "total", "limit", "items"} <= set(body)
        for item in body["items"]:
            UnimodSummary.model_validate(item)
