"""Exceptions raised by unimodpy."""

from __future__ import annotations


class UnimodError(Exception):
    """Base class for every error unimodpy raises on purpose."""


class UnimodParseError(UnimodError, ValueError):
    """An OBO file could not be parsed. The message names the line and entry."""


class UnimodKeyError(UnimodError, KeyError):
    """``db[key]`` found no entry. Also a ``KeyError`` (not a ``ValueError``); ``args[0]`` is the key looked up."""
