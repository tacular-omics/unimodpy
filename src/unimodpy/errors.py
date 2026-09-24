"""Exceptions raised by unimodpy."""

from __future__ import annotations


class UnimodError(ValueError):
    """Base class for every error unimodpy raises on purpose.

    Also a ``ValueError`` (since 1.1), so ``except ValueError`` catches every unimodpy error.
    """


class UnimodParseError(UnimodError, ValueError):
    """An OBO file could not be parsed. The message names the line and entry."""


class UnimodKeyError(UnimodError, KeyError):
    """``db[key]`` found no entry. Also a ``KeyError``; ``args[0]`` is the key looked up."""
