"""Parse UNIMOD ``definition_ref`` strings into structured citation lists.

UNIMOD encodes citations inline in the OBO ``def:`` line as a comma-separated
list of ``PREFIX:ACCESSION`` tokens, plus URL tokens with OBO-escaped colons
(``URL:http\\://...``).  This parser turns that blob into typed
:class:`unimodpy.server.models.Reference` instances so LLM consumers don't
have to.
"""

from __future__ import annotations

import re

from unimodpy.server.models import Reference

# OBO escapes ``:`` as ``\:`` inside xref values.  We undo that so URLs are
# usable strings.
_OBO_ESCAPE = re.compile(r"\\([:,\s])")
_URL_PREFIXES = ("URL", "UNIMODURL", "FindModURL", "MISCURL")


def _unescape(s: str) -> str:
    return _OBO_ESCAPE.sub(r"\1", s)


def parse_definition_ref(raw: str | None) -> list[Reference]:
    """Split a definition_ref blob into typed Reference objects.

    Tokens like ``RESID:AA0048`` become ``Reference(type="RESID",
    accession="AA0048")``.  URL-bearing tokens (``URL:...`` and friends)
    become ``Reference(type=<prefix>, value=<unescaped-url>)`` since their
    suffix is not a stable accession.  Bare tokens with no colon fall
    through to ``Reference(type="Misc", value=token)``.

    The input may be empty, a single value, or a comma-separated list, and
    may contain OBO-escaped colons (``\\:``) inside URLs.
    """
    if not raw:
        return []
    refs: list[Reference] = []
    for raw_token in raw.split(","):
        token = raw_token.strip()
        if not token:
            continue
        prefix, sep, suffix = token.partition(":")
        if not sep:
            refs.append(Reference(type="Misc", value=_unescape(token)))
            continue
        if prefix in _URL_PREFIXES:
            refs.append(Reference(type=prefix, value=_unescape(suffix)))
        else:
            refs.append(Reference(type=prefix, accession=_unescape(suffix)))
    return refs
