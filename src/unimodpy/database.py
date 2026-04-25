"""Lookup class for UNIMOD entries."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from pathlib import Path

from unimodpy.models import UnimodEntry


class UnimodDatabase:
    """In-memory lookup table for UNIMOD entries.

    Supports lookup by integer ID, "UNIMOD:N" string, bare numeric string,
    or case-insensitive name.
    """

    def __init__(self, entries: Iterable[UnimodEntry], *, header_lines: tuple[str, ...] = ()) -> None:
        self._entries: list[UnimodEntry] = []
        self._by_id: dict[int, UnimodEntry] = {}
        self._by_name_lower: dict[str, UnimodEntry] = {}
        self.header_lines: tuple[str, ...] = header_lines

        for entry in entries:
            self._entries.append(entry)
            self._by_id[entry.id] = entry
            self._by_name_lower[entry.name.lower()] = entry

    def get_by_id(self, id: int | str) -> UnimodEntry | None:
        """Return the entry for the given ID, or None if not found.

        Accepts an integer, a bare numeric string ("1"), or a full
        UNIMOD identifier string ("UNIMOD:1", case-insensitive).
        """
        if isinstance(id, str):
            cleaned = id.upper().removeprefix("UNIMOD:")
            try:
                n = int(cleaned)
            except ValueError:
                return None
        else:
            n = id
        return self._by_id.get(n)

    def get_by_name(self, name: str) -> UnimodEntry | None:
        """Return the entry whose name matches (case-insensitive), or None."""
        return self._by_name_lower.get(name.lower())

    def search(self, query: str) -> list[UnimodEntry]:
        """Return all entries where query appears in name, definition, or any synonym.

        Comparison is case-insensitive substring matching.
        """
        q = query.lower()
        return [
            entry
            for entry in self._entries
            if q in entry.name.lower() or q in entry.definition.lower() or any(q in s.lower() for s in entry.synonyms)
        ]

    def __getitem__(self, id: int | str) -> UnimodEntry:
        entry = self.get_by_id(id)
        if entry is None:
            entry = self.get_by_name(str(id))
        if entry is None:
            raise KeyError(id)
        return entry

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
