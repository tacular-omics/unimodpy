"""Dataclasses representing UNIMOD OBO entries."""

from __future__ import annotations

import datetime
import warnings
from dataclasses import dataclass
from enum import StrEnum

from unimodpy._formula import parse_delta_composition, to_proforma_formula
from unimodpy.errors import UnimodParseError


def _lenient_composition(composition: str, where: str) -> dict[str, int] | None:
    """``parse_delta_composition``, or None plus one ``UserWarning`` naming *where* if it cannot be parsed."""
    try:
        return parse_delta_composition(composition)
    except UnimodParseError as exc:
        warnings.warn(f"{where}: composition not parsed, returning None ({exc})", UserWarning, stacklevel=3)
        return None


class Site(StrEnum):
    """Amino acid residue or terminus to which a modification can be applied."""

    A = "A"
    C = "C"
    C_TERM = "C-term"
    D = "D"
    E = "E"
    F = "F"
    G = "G"
    H = "H"
    I = "I"  # noqa: E741
    K = "K"
    L = "L"
    M = "M"
    N = "N"
    N_TERM = "N-term"
    P = "P"
    Q = "Q"
    R = "R"
    S = "S"
    T = "T"
    U = "U"
    V = "V"
    W = "W"
    Y = "Y"


class Position(StrEnum):
    """Sequence position constraint for a modification specificity."""

    ANYWHERE = "Anywhere"
    ANY_N_TERM = "Any N-term"
    ANY_C_TERM = "Any C-term"
    PROTEIN_N_TERM = "Protein N-term"
    PROTEIN_C_TERM = "Protein C-term"


class Classification(StrEnum):
    """Biological/chemical classification of a modification."""

    AA_SUBSTITUTION = "AA substitution"
    ARTEFACT = "Artefact"
    CHEMICAL_DERIVATIVE = "Chemical derivative"
    CO_TRANSLATIONAL = "Co-translational"
    ISOTOPIC_LABEL = "Isotopic label"
    MULTIPLE = "Multiple"
    N_LINKED_GLYCOSYLATION = "N-linked glycosylation"
    NON_STANDARD_RESIDUE = "Non-standard residue"
    O_LINKED_GLYCOSYLATION = "O-linked glycosylation"
    OTHER = "Other"
    OTHER_GLYCOSYLATION = "Other glycosylation"
    POST_TRANSLATIONAL = "Post-translational"
    PRE_TRANSLATIONAL = "Pre-translational"
    SYNTH_PEP_PROTECT_GP = "Synth. pep. protect. gp."


@dataclass(frozen=True, slots=True)
class NeutralLoss:
    """A neutral loss associated with a modification specificity.

    The key is the numeric M component from spec_N_neutral_loss_M_* xrefs,
    which corresponds to the nominal neutral loss mass (e.g. 0 for zero-loss,
    106 for ~105 Da loss).
    """

    key: int
    mono_mass: float
    avge_mass: float
    flag: bool
    composition: str

    def __repr__(self) -> str:
        return f"NeutralLoss(key={self.key}, mono_mass={self.mono_mass}, composition={self.composition!r})"

    def __str__(self) -> str:
        return f"NL[{self.key}] {self.mono_mass:+.6f} Da  {self.composition}"

    @property
    def dict_composition(self) -> dict[str, int] | None:
        """Expanded elemental composition of the lost group as {element: count}.

        Monosaccharide abbreviations are expanded to atoms and isotope-labelled
        elements are kept as distinct keys ("13C", "2H"). The zero-loss
        composition ``"0"`` gives ``{}``. A composition this version cannot parse
        (e.g. a new upstream monosaccharide) gives None and a ``UserWarning``.
        """
        return _lenient_composition(self.composition, f"neutral loss {self.key}")

    @property
    def proforma_formula(self) -> str | None:
        """Hill-notation formula string of the lost group, e.g. ``HO3P``; ``""`` for a zero loss,
        None if the composition cannot be parsed (see ``dict_composition``)."""
        comp = self.dict_composition
        return None if comp is None else to_proforma_formula(comp)


@dataclass(frozen=True, slots=True)
class Specificity:
    """A single site/position specificity for a UNIMOD modification.

    ``site``, ``position`` and ``classification`` are enum members. A value that
    this version does not know (new upstream vocabulary) is kept as the raw
    string, and the parser emits a warning.
    """

    spec_num: int
    group: int
    hidden: bool
    site: Site | str
    position: Position | str
    classification: Classification | str
    misc_notes: str | None
    neutral_losses: tuple[NeutralLoss, ...]

    def __repr__(self) -> str:
        return (
            f"Specificity(spec_num={self.spec_num}, site={self.site!r}, "
            f"position={self.position!r}, classification={self.classification!r})"
        )

    def __str__(self) -> str:
        parts = [f"Spec {self.spec_num}: {self.site} @ {self.position} [{self.classification}]"]
        if self.misc_notes:
            parts.append(f"  # {self.misc_notes}")
        if self.neutral_losses:
            nl_str = ", ".join(str(nl) for nl in self.neutral_losses)
            parts.append(f"  neutral losses: {nl_str}")
        return "\n".join(parts)


@dataclass(frozen=True, slots=True)
class UnimodEntry:
    """A single [Term] entry from the UNIMOD OBO file.

    xref-derived fields (record_id, delta_*, username_*, etc.) are None for
    the root node UNIMOD:0, which carries no xref lines.

    ``definition_ref`` is the citation list from the ``def:`` line without the
    surrounding brackets (``"RESID:AA0048, PMID:11999733"``); ``""`` when absent.
    """

    id: int
    name: str
    definition: str
    synonyms: tuple[str, ...]
    definition_ref: str = ""
    comment: str | None = None
    record_id: int | None = None
    delta_mono_mass: float | None = None
    delta_avge_mass: float | None = None
    delta_composition: str | None = None
    username_of_poster: str | None = None
    group_of_poster: str | None = None
    date_time_posted: datetime.datetime | None = None
    date_time_modified: datetime.datetime | None = None
    approved: bool | None = None
    is_a: int | None = None
    specificities: tuple[Specificity, ...] = ()

    @property
    def accession(self) -> str:
        """The CURIE ``"UNIMOD:<id>"``, as sent on the server wire."""
        return f"UNIMOD:{self.id}"

    def get_mass(self, *, monoisotopic: bool = True) -> float | None:
        """The delta mass in Da: ``delta_mono_mass`` (default) or, with ``monoisotopic=False``, ``delta_avge_mass``.

        ``None`` when Unimod gives no such mass for this entry.
        """
        return self.delta_mono_mass if monoisotopic else self.delta_avge_mass

    def __repr__(self) -> str:
        return (
            f"UnimodEntry(id={self.id}, name={self.name!r}, "
            f"formula={self.proforma_formula!r}, mono_mass={self.delta_mono_mass})"
        )

    def __str__(self) -> str:
        lines = [f"UNIMOD:{self.id}  {self.name}"]
        lines.append(f"  {self.definition}")
        if self.synonyms:
            lines.append(f"  Synonyms : {', '.join(self.synonyms)}")
        if self.comment:
            lines.append(f"  Comment  : {self.comment}")
        if self.proforma_formula:
            lines.append(f"  Formula  : {self.proforma_formula}")
        if self.delta_mono_mass is not None:
            lines.append(f"  Mass     : {self.delta_mono_mass:+.6f} Da (mono)  {self.delta_avge_mass:+.4f} Da (avg)")
        if self.specificities:
            lines.append(f"  Sites ({len(self.specificities)}):")
            for spec in self.specificities:
                nl = f"  NL={[nl.key for nl in spec.neutral_losses]}" if spec.neutral_losses else ""
                lines.append(f"    {spec.spec_num}: {spec.site} @ {spec.position} [{spec.classification}]{nl}")
        return "\n".join(lines)

    @property
    def dict_composition(self) -> dict[str, int] | None:
        """Expanded elemental composition as {element: count}.

        Monosaccharide abbreviations (Hex, HexNAc, dHex, NeuAc, etc.) in
        delta_composition are expanded to their constituent atoms.  Isotope-
        labelled elements (2H, 13C) are kept as distinct keys.  Counts can be
        negative for modifications that remove atoms.

        Returns None when delta_composition is absent (e.g. the root node), or
        when it cannot be parsed (a token this version does not know, such as a
        new upstream monosaccharide); the latter also emits a ``UserWarning``.
        """
        if self.delta_composition is None:
            return None
        return _lenient_composition(self.delta_composition, self.accession)

    @property
    def proforma_formula(self) -> str | None:
        """Hill-notation formula string for use in ProForma modification annotations.

        Produces a string like ``C2H2O`` or ``H-1NO-1`` that can be wrapped in
        ``[Formula:...]`` for a full ProForma term.  Monosaccharide abbreviations
        are expanded to atoms; isotope labels are bracketed (e.g. ``[13C2]H5[2H]``).

        Returns None when delta_composition is absent or cannot be parsed (see
        ``dict_composition``, which also warns).
        """
        comp = self.dict_composition
        if comp is None:
            return None
        return to_proforma_formula(comp)
