"""``str()`` and ``repr()`` of every public model, over the field combinations the data allows.

A ``__str__`` that raises breaks f-strings, logging and debuggers, so these assert the
contract (a string comes back) for each model rather than checking one example's text.
"""

from __future__ import annotations

import dataclasses
import datetime

import pytest

from unimodpy import NeutralLoss, Specificity, UnimodDatabase, UnimodEntry
from unimodpy.models import Classification, Position, Site

_ZERO_LOSS = NeutralLoss(key=0, mono_mass=0.0, avge_mass=0.0, flag=False, composition="0")
_WATER_LOSS = NeutralLoss(key=18, mono_mass=18.010565, avge_mass=18.0153, flag=True, composition="H2O")

_SPEC = Specificity(
    spec_num=1,
    group=1,
    hidden=False,
    site=Site.S,
    position=Position.ANYWHERE,
    classification=Classification.POST_TRANSLATIONAL,
    misc_notes=None,
    neutral_losses=(),
)


def _entry(**kwargs: object) -> UnimodEntry:
    base: dict[str, object] = {"id": 1, "name": "Example", "definition": "An example entry.", "synonyms": ()}
    return UnimodEntry(**(base | kwargs))  # type: ignore[arg-type]


# One case per field combination that changes which branch of __str__/__repr__ runs.
MODELS: list[tuple[str, object]] = [
    ("neutral_loss_zero", _ZERO_LOSS),
    ("neutral_loss_water", _WATER_LOSS),
    ("neutral_loss_negative", NeutralLoss(key=1, mono_mass=-1.5, avge_mass=-1.5, flag=False, composition="H-1")),
    ("specificity_plain", _SPEC),
    ("specificity_with_notes", dataclasses.replace(_SPEC, misc_notes="a note")),
    ("specificity_with_losses", dataclasses.replace(_SPEC, neutral_losses=(_ZERO_LOSS, _WATER_LOSS))),
    ("specificity_raw_vocabulary", dataclasses.replace(_SPEC, site="Z", position="Somewhere new")),
    ("entry_minimal", _entry()),
    ("entry_both_masses", _entry(delta_mono_mass=42.010565, delta_avge_mass=42.0367, delta_composition="H(2) C(2) O")),
    ("entry_mono_mass_only", _entry(delta_mono_mass=42.010565)),
    ("entry_avge_mass_only", _entry(delta_avge_mass=42.0367)),
    ("entry_no_masses_with_composition", _entry(delta_composition="H(2) C(2) O")),
    (
        "entry_full",
        _entry(
            synonyms=("one", "two"),
            comment="a comment",
            record_id=1,
            delta_mono_mass=42.010565,
            delta_avge_mass=42.0367,
            delta_composition="H(2) C(2) O",
            username_of_poster="someone",
            group_of_poster="admin",
            date_time_posted=datetime.datetime(2026, 1, 1, 12, 0, 0),
            date_time_modified=datetime.datetime(2026, 1, 2, 12, 0, 0),
            approved=True,
            is_a=0,
            specificities=(_SPEC,),
        ),
    ),
]


@pytest.mark.parametrize("model", [m for _, m in MODELS], ids=[name for name, _ in MODELS])
def test_str_returns_a_string(model: object) -> None:
    text = str(model)
    assert isinstance(text, str)
    assert text


@pytest.mark.parametrize("model", [m for _, m in MODELS], ids=[name for name, _ in MODELS])
def test_repr_returns_a_string(model: object) -> None:
    text = repr(model)
    assert isinstance(text, str)
    assert text


@pytest.mark.parametrize("model", [m for _, m in MODELS], ids=[name for name, _ in MODELS])
def test_fstring_interpolation(model: object) -> None:
    """f-strings and logging go through ``__format__``, which falls back to ``__str__``."""
    assert f"{model}" == str(model)


def test_one_mass_without_the_other_still_prints_it() -> None:
    """A mass line with only one of the two masses: it used to raise ``TypeError``."""
    mono = str(_entry(delta_mono_mass=42.010565))
    avge = str(_entry(delta_avge_mass=42.0367))
    assert "+42.010565 Da (mono)" in mono
    assert "(avg)" not in mono
    assert "+42.0367 Da (avg)" in avge
    assert "(mono)" not in avge


def test_both_masses_on_one_line() -> None:
    line = next(line for line in str(MODELS[8][1]).splitlines() if "Mass" in line)
    assert line == "  Mass     : +42.010565 Da (mono)  +42.0367 Da (avg)"


def test_every_database_model_stringifies(db: UnimodDatabase) -> None:
    """The same contract over the bundled database: every entry, specificity and neutral loss."""
    failures = []
    for entry in db:
        models: list[object] = [entry]
        for spec in entry.specificities:
            models.append(spec)
            models.extend(spec.neutral_losses)
        for model in models:
            for name, call in (("str", str), ("repr", repr)):
                try:
                    assert call(model)
                except Exception as exc:  # noqa: BLE001 - the point is that nothing escapes
                    failures.append((entry.id, type(model).__name__, name, type(exc).__name__, str(exc)))
    assert not failures, f"{len(failures)} models failed: {failures[:10]}"
