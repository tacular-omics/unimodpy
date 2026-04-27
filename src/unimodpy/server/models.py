"""Pydantic response models for the unimodpy REST + MCP server.

These models are the single source of truth for the wire shape returned by
both transports.  Keeping the models here (rather than inline in ``app.py``)
lets tests import them and lets FastMCP derive ``outputSchema`` automatically.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from unimodpy.models import NeutralLoss as _NeutralLoss
from unimodpy.models import Specificity as _Specificity
from unimodpy.models import UnimodEntry as _UnimodEntry


class Reference(BaseModel):
    """A single citation parsed from ``definition_ref``."""

    type: str
    accession: str | None = None
    value: str | None = None


class NeutralLoss(BaseModel):
    key: int
    mono_mass: float
    avge_mass: float
    flag: bool
    composition: str
    proforma_formula: str | None


class Specificity(BaseModel):
    spec_num: int
    group: int
    hidden: bool
    site: str
    position: str
    classification: str
    misc_notes: str | None
    neutral_losses: list[NeutralLoss]


class UnimodEntry(BaseModel):
    """Full UNIMOD modification entry."""

    id: int
    accession: str
    name: str
    definition: str | None
    references: list[Reference]
    synonyms: list[str]
    comment: str | None
    parent_id: int | None
    delta_mono_mass: float | None
    delta_avge_mass: float | None
    delta_composition: str | None
    proforma_formula: str | None
    dict_composition: dict[str, int] | None
    approved: bool | None
    specificities: list[Specificity]


class UnimodSummary(BaseModel):
    """Compact entry shape returned by ``search`` and similar list endpoints."""

    id: int
    accession: str
    name: str
    delta_mono_mass: float | None
    proforma_formula: str | None


class EntryListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[UnimodEntry]


class SearchResponse(BaseModel):
    query: str
    total: int
    limit: int
    items: list[UnimodSummary] = Field(
        description="Lightweight summaries; call get_by_id for the full record.",
    )


# ---------------------------------------------------------------------------
# Converters from domain dataclasses to Pydantic models
# ---------------------------------------------------------------------------


def _neutral_loss(nl: _NeutralLoss) -> NeutralLoss:
    return NeutralLoss(
        key=nl.key,
        mono_mass=nl.mono_mass,
        avge_mass=nl.avge_mass,
        flag=nl.flag,
        composition=nl.composition,
        proforma_formula=nl.proforma_formula,
    )


def _specificity(spec: _Specificity) -> Specificity:
    return Specificity(
        spec_num=spec.spec_num,
        group=spec.group,
        hidden=spec.hidden,
        site=str(spec.site),
        position=str(spec.position),
        classification=str(spec.classification),
        misc_notes=spec.misc_notes,
        neutral_losses=[_neutral_loss(nl) for nl in spec.neutral_losses],
    )


def to_unimod_entry(entry: _UnimodEntry, *, include_hidden: bool = False) -> UnimodEntry:
    """Build a Pydantic UnimodEntry from a parsed dataclass entry.

    Hidden specificities are filtered out unless ``include_hidden=True``.
    UNIMOD marks rarely-used or deprecated sites as ``hidden=true`` so they
    don't clutter default UI listings; we honour that for LLM consumers too.
    """
    # Local import to avoid a server-package import cycle if references.py
    # ever grows to import models.py at module scope itself.
    from unimodpy.server.references import parse_definition_ref

    specs = entry.specificities
    if not include_hidden:
        specs = tuple(s for s in specs if not s.hidden)

    return UnimodEntry(
        id=entry.id,
        accession=f"UNIMOD:{entry.id}",
        name=entry.name,
        definition=entry.definition or None,
        references=parse_definition_ref(entry.definition_ref),
        synonyms=list(entry.synonyms),
        comment=entry.comment,
        parent_id=entry.is_a,
        delta_mono_mass=entry.delta_mono_mass,
        delta_avge_mass=entry.delta_avge_mass,
        delta_composition=entry.delta_composition,
        proforma_formula=entry.proforma_formula,
        dict_composition=entry.dict_composition,
        approved=entry.approved,
        specificities=[_specificity(s) for s in specs],
    )


def to_unimod_summary(entry: _UnimodEntry) -> UnimodSummary:
    return UnimodSummary(
        id=entry.id,
        accession=f"UNIMOD:{entry.id}",
        name=entry.name,
        delta_mono_mass=entry.delta_mono_mass,
        proforma_formula=entry.proforma_formula,
    )
