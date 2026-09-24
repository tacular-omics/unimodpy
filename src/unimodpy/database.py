"""Lookup class for UNIMOD entries."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from pathlib import Path

from unimodpy.errors import UnimodError, UnimodKeyError
from unimodpy.models import UnimodEntry

# Joins the lowercased search fields of one entry. A query without this character can
# only match inside one field, so one substring test replaces one test per field.
_SEP = "\x00"


def _fields(entry: UnimodEntry) -> list[str]:
    """Return the lowercased name, definition and synonyms of ``entry``: the fields search() looks in."""
    return [entry.name.lower(), entry.definition.lower(), *(s.lower() for s in entry.synonyms)]


def _haystack(entry: UnimodEntry) -> str:
    """Return ``_fields(entry)`` joined by ``_SEP``."""
    return _SEP.join(_fields(entry))


class UnimodDatabase:
    """In-memory lookup table for UNIMOD entries.

    Supports lookup by integer ID, "UNIMOD:N" string, bare numeric string,
    or case-insensitive name.

    Raises:
        UnimodError: two entries share an id.
    """

    def __init__(self, entries: Iterable[UnimodEntry], *, header_lines: tuple[str, ...] = ()) -> None:
        self._entries: list[UnimodEntry] = []
        self._by_id: dict[int, UnimodEntry] = {}
        self._by_name_lower: dict[str, UnimodEntry] = {}
        self.header_lines: tuple[str, ...] = header_lines

        for entry in entries:
            if entry.id in self._by_id:
                raise UnimodError(f"duplicate id UNIMOD:{entry.id} ({self._by_id[entry.id].name!r} and {entry.name!r})")
            self._entries.append(entry)
            self._by_id[entry.id] = entry
            # Duplicate names: the first entry keeps the name (see get_by_name).
            self._by_name_lower.setdefault(entry.name.lower(), entry)

        # (entry, lowercased name/definition/synonyms joined by _SEP), in file order, for search().
        self._haystacks: list[tuple[UnimodEntry, str]] = [(e, _haystack(e)) for e in self._entries]

    def get_by_id(self, id: int | str) -> UnimodEntry | None:
        """Return the entry for the given ID, or None if not found.

        Accepts an integer, a bare numeric string ("1"), or a full
        UNIMOD identifier string ("UNIMOD:1", case-insensitive). Anything
        else, including an unparseable string and ``bool``, returns None.
        """
        if isinstance(id, bool):
            return None
        if isinstance(id, str):
            cleaned = id.strip().upper().removeprefix("UNIMOD:")
            # Plain ASCII digits only: int() would also accept "1_0", "+1" and non-ASCII digits.
            if not (cleaned.isascii() and cleaned.isdigit()):
                return None
            n = int(cleaned)
        elif isinstance(id, int):
            n = id
        else:
            return None
        return self._by_id.get(n)

    def get_by_name(self, name: str) -> UnimodEntry | None:
        """Return the entry whose name matches (case-insensitive), or None.

        If several entries share a name, the first one in file order wins.
        A non-``str`` argument returns None.
        """
        if not isinstance(name, str):
            return None
        return self._by_name_lower.get(name.lower())

    def search(self, query: str) -> list[UnimodEntry]:
        """Return all entries where query appears in name, definition, or any synonym.

        Comparison is case-insensitive substring matching. A non-``str`` query returns ``[]``.
        """
        if not isinstance(query, str):
            return []
        q = query.lower()
        if _SEP in q:
            # Rare: the query could span two joined fields, so test each field.
            return [e for e in self._entries if any(q in f for f in _fields(e))]
        return [entry for entry, haystack in self._haystacks if q in haystack]

    def get(self, key: object, default: UnimodEntry | None = None) -> UnimodEntry | None:
        """Return ``db[key]``, or ``default`` if it would raise. Never raises."""
        try:
            return self[key]
        except KeyError:
            return default

    def __getitem__(self, key: object) -> UnimodEntry:
        """Return the entry by id (1, "1", "UNIMOD:1") or, failing that, by name
        (case-insensitive). Raise UnimodKeyError (a KeyError) for a missing or non-int/str key."""
        entry = None
        if isinstance(key, int | str):
            entry = self.get_by_id(key)
            if entry is None and isinstance(key, str):
                entry = self.get_by_name(key)
        if entry is None:
            raise UnimodKeyError(key)
        return entry

    def __contains__(self, key: object) -> bool:
        """Return True if ``db[key]`` would succeed, or if key is an entry in this database."""
        if isinstance(key, UnimodEntry):
            return self._by_id.get(key.id) == key
        return self.get(key) is not None

    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self) -> Iterator[UnimodEntry]:
        return iter(self._entries)

    def write_tsv(self, path: Path | str, *, delimiter: str = "\t") -> Path:
        """Serialize all entries to a tab-separated file. Pass ``delimiter=','`` for CSV."""
        from unimodpy._tabular import write_tsv

        return write_tsv(self._entries, path, delimiter=delimiter)

    def write_obo(self, path: Path | str) -> Path:
        """Serialize all entries to UNIMOD OBO format."""
        from unimodpy._obo_writer import write_obo

        return write_obo(self._entries, path, header_lines=self.header_lines)
