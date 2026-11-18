"""Undo the backslash escapes OBO defines inside a tag name or value.

The governing table is OBO Flat File Format 1.4, section "Escape characters", read
2026-11-17 from <https://owlcollab.github.io/oboformat/doc/GO.format.obo-1_4.html>:
"Tag names and values may contain the following escape characters:", followed by the
fifteen rows transcribed in ``_ESCAPES`` below.

That same section then says: "OBO parser implementations may support only these escape
characters, or they may assume that any character following a backslash is an escaped
character. Parsers that choose the latter approach will translate ``\\a`` and ``\\?`` to
"a" and "?" respectively."

This module takes the **first** of those two permitted options: it decodes exactly the
rows of the table and returns any other backslash sequence unchanged. So a sequence the
table does not define, such as ``\\'``, is passed through byte for byte rather than
guessed at. Choosing the second option instead is a decision about data, not a bug fix.
"""

from __future__ import annotations

import re

# OBO Flat File Format 1.4, "Escape characters", read 2026-11-17 from
# https://owlcollab.github.io/oboformat/doc/GO.format.obo-1_4.html
# Keys are the character after the backslash; values are the literal the table gives.
# The table's "@ -> at (language tag)" row is not a backslash sequence, so it is not an
# unescaping rule and is deliberately absent.
_ESCAPES: dict[str, str] = {
    "n": "\n",  # newline
    "W": " ",  # single space
    "t": "\t",  # tab
    ":": ":",  # colon
    ",": ",",  # comma
    '"': '"',  # double quote
    "\\": "\\",  # backslash
    "(": "(",  # open parenthesis
    ")": ")",  # close parenthesis
    "[": "[",  # open bracket
    "]": "]",  # close bracket
    "{": "{",  # open brace
    "}": "}",  # close brace
    "\n": "",  # "\<newline>" -> <no value>
}

# ``re.DOTALL`` so that ``.`` also matches the newline of the ``\<newline>`` row.
_ESCAPE_RE = re.compile(r"\\(.)", re.DOTALL)


def unescape_obo(text: str) -> str:
    """Return ``text`` with OBO 1.4's backslash escapes decoded.

    One left-to-right pass, so an escaped backslash is not reconsidered: ``"a\\\\:b"``
    (backslash, backslash, colon) decodes to ``"a\\:b"`` (backslash, colon), not to
    ``"a:b"``.

    A backslash sequence the 1.4 table does not define is returned unchanged, including
    the backslash. ``unescape_obo("Schiff\\\\'s")`` is ``"Schiff\\'s"``.
    """
    return _ESCAPE_RE.sub(lambda m: _ESCAPES.get(m.group(1), m.group(0)), text)
