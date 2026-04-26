"""Serializers turning UnimodEntry dataclasses into JSON-friendly dicts."""

from __future__ import annotations

from typing import Any

from unimodpy.models import NeutralLoss, Specificity, UnimodEntry


def serialize_neutral_loss(nl: NeutralLoss) -> dict[str, Any]:
    return {
        "key": nl.key,
        "mono_mass": nl.mono_mass,
        "avge_mass": nl.avge_mass,
        "flag": nl.flag,
        "composition": nl.composition,
        "proforma_formula": nl.proforma_formula,
    }


def serialize_specificity(spec: Specificity) -> dict[str, Any]:
    return {
        "spec_num": spec.spec_num,
        "group": spec.group,
        "hidden": spec.hidden,
        "site": str(spec.site),
        "position": str(spec.position),
        "classification": str(spec.classification),
        "misc_notes": spec.misc_notes,
        "neutral_losses": [serialize_neutral_loss(nl) for nl in spec.neutral_losses],
    }


def serialize_entry(entry: UnimodEntry) -> dict[str, Any]:
    return {
        "id": entry.id,
        "accession": f"UNIMOD:{entry.id}",
        "name": entry.name,
        "definition": entry.definition,
        "definition_ref": entry.definition_ref,
        "synonyms": list(entry.synonyms),
        "comment": entry.comment,
        "record_id": entry.record_id,
        "delta_mono_mass": entry.delta_mono_mass,
        "delta_avge_mass": entry.delta_avge_mass,
        "delta_composition": entry.delta_composition,
        "proforma_formula": entry.proforma_formula,
        "dict_composition": entry.dict_composition,
        "approved": entry.approved,
        "is_a": entry.is_a,
        "date_time_posted": entry.date_time_posted.isoformat() if entry.date_time_posted else None,
        "date_time_modified": entry.date_time_modified.isoformat() if entry.date_time_modified else None,
        "specificities": [serialize_specificity(s) for s in entry.specificities],
    }
