"""Lookup class for UNIMOD entries."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
from pathlib import Path
from typing import Literal

from unimodpy.models import Classification, Position, UnimodEntry

MassType = Literal["mono", "avg"]


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
        """Return the entry for the given ID, or None if not found."""
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
        """Return all entries where query appears in name, definition, or any synonym."""
        q = query.lower()
        return [
            entry
            for entry in self._entries
            if q in entry.name.lower() or q in entry.definition.lower() or any(q in s.lower() for s in entry.synonyms)
        ]

    def find(
        self,
        *,
        text: str | None = None,
        mass_min: float | None = None,
        mass_max: float | None = None,
        mass_type: MassType = "mono",
        residues: Sequence[str] | None = None,
        position: str | None = None,
        classification: str | None = None,
        has_neutral_loss: bool | None = None,
        include_hidden: bool = False,
        limit: int | None = None,
    ) -> list[UnimodEntry]:
        """Fine-grained AND-combined search across multiple fields.

        All filters are optional; ``None`` values are skipped.  ``residues``
        matches a specificity site (case-sensitive single-letter, or terminus
        strings like ``"N-term"``).  ``position`` and ``classification`` accept
        the UNIMOD enum string values (e.g. ``"Anywhere"``,
        ``"N-linked glycosylation"``).  ``has_neutral_loss=True`` requires at
        least one specificity carrying a non-empty neutral_losses tuple.
        Hidden specificities are ignored unless ``include_hidden=True``.
        """
        text_q = text.lower() if text is not None else None
        residue_set = set(residues) if residues else None

        pos_value: Position | None = None
        if position is not None:
            try:
                pos_value = Position(position)
            except ValueError:
                return []

        cls_value: Classification | None = None
        if classification is not None:
            try:
                cls_value = Classification(classification)
            except ValueError:
                return []

        results: list[UnimodEntry] = []
        for entry in self._entries:
            if text_q is not None and not (
                text_q in entry.name.lower()
                or text_q in entry.definition.lower()
                or any(text_q in s.lower() for s in entry.synonyms)
            ):
                continue

            if mass_min is not None or mass_max is not None:
                mass = entry.delta_mono_mass if mass_type == "mono" else entry.delta_avge_mass
                if mass is None:
                    continue
                if mass_min is not None and mass < mass_min:
                    continue
                if mass_max is not None and mass > mass_max:
                    continue

            specs = entry.specificities if include_hidden else tuple(s for s in entry.specificities if not s.hidden)

            if residue_set is not None:
                if not any(str(s.site) in residue_set for s in specs):
                    continue

            if pos_value is not None and not any(s.position == pos_value for s in specs):
                continue

            if cls_value is not None and not any(s.classification == cls_value for s in specs):
                continue

            if has_neutral_loss is not None:
                has_nl = any(bool(s.neutral_losses) for s in specs)
                if has_nl != has_neutral_loss:
                    continue

            results.append(entry)
            if limit is not None and len(results) >= limit:
                break

        return results

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
