"""Undo the backslash escapes OBO uses inside an xref value.

OBO escapes ``:``, ``,`` and whitespace as ``\\:``, ``\\,`` and ``\\ `` inside an xref value, so
UNIMOD stores a citation URL as ``URL:http\\://www.unimod.org/...``. One rule, shared by
``search(include_references=True)`` and by the server's reference parser: do not write a second
copy of it.
"""

from __future__ import annotations

import re

_OBO_ESCAPE = re.compile(r"\\([:,\s])")


def unescape_obo(text: str) -> str:
    """Return ``text`` with OBO's backslash escapes removed."""
    return _OBO_ESCAPE.sub(r"\1", text)
