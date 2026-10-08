"""UNIMOD reuses a spec number for several sites; every specificity block must survive parsing."""

import re
from collections import Counter
from importlib.resources import files

from unimodpy import Classification, Position, Site, UnimodDatabase, parse_obo, write_obo

_OBO_TEXT = (files("unimodpy") / "data" / "UNIMOD.obo").read_text(encoding="utf-8")


def _all_specs(db: UnimodDatabase):
    return [s for e in db for s in e.specificities]


def test_specificity_count_matches_site_lines(db: UnimodDatabase) -> None:
    raw = len(re.findall(r'^xref: spec_\d+_site "', _OBO_TEXT, flags=re.MULTILINE))
    assert len(_all_specs(db)) == raw


def test_neutral_loss_count_matches_raw(db: UnimodDatabase) -> None:
    raw = len(re.findall(r'^xref: spec_\d+_neutral_loss_\d+_mono_mass "', _OBO_TEXT, flags=re.MULTILINE))
    assert sum(len(s.neutral_losses) for s in _all_specs(db)) == raw


def test_phospho_sites(db: UnimodDatabase) -> None:
    sites = {str(s.site) for s in db[21].specificities}
    assert {"S", "T", "Y"} <= sites


def test_reused_spec_number_keeps_both_blocks(db: UnimodDatabase) -> None:
    spec1 = [s for s in db[21].specificities if s.spec_num == 1]
    assert {str(s.site) for s in spec1} == {"S", "T"}
    # Each block keeps its own neutral losses (both carry the H3PO4 loss).
    for s in spec1:
        assert any(abs(nl.mono_mass - 97.976896) < 1e-6 for nl in s.neutral_losses)


def test_oxidation_w_and_deamidated_q(db: UnimodDatabase) -> None:
    assert "W" in {str(s.site) for s in db[35].specificities}
    assert "Q" in {str(s.site) for s in db[7].specificities}


def test_search_mass_phospho_on_t(db: UnimodDatabase) -> None:
    hits = db.search_mass(79.966331, site="T")
    assert 21 in {entry.id for entry, _ in hits}


def test_round_trip_preserves_all_specificities(db: UnimodDatabase, tmp_path) -> None:
    out = tmp_path / "out.obo"
    write_obo(db, out, header_lines=db.header_lines)
    db2 = parse_obo(out)
    for entry in db:
        assert db2[entry.id].specificities == entry.specificities, entry.id


_TERM_ID_RE = re.compile(r"^id: UNIMOD:(\d+)$", flags=re.MULTILINE)
_SPEC_FIELD_RE = re.compile(
    r'^xref: spec_(\d+)_(site|position|classification|hidden|group) "(.*)"$', flags=re.MULTILINE
)
_NL_MONO_RE = re.compile(r'^xref: spec_(\d+)_neutral_loss_\d+_mono_mass "(.*)"$', flags=re.MULTILINE)


def test_every_entry_specificity_fields_match_raw_obo(db: UnimodDatabase) -> None:
    """For every entry, each specificity field value sits on the same entry and spec number as in the OBO.

    The global count tests above pass if a value lands on the wrong entry or spec
    number, or one value is dropped while another is duplicated. This compares, per
    entry, the multiset of (spec number, field, value) read straight from the raw
    xref lines with the parsed specificities, and checks that every site, position
    and classification parsed to a known enum member rather than a raw string.
    """
    raw: dict[int, Counter] = {}
    for block in _OBO_TEXT.split("[Term]")[1:]:
        m = _TERM_ID_RE.search(block)
        assert m is not None, block[:80]
        fields = Counter((int(n), f, v) for n, f, v in _SPEC_FIELD_RE.findall(block))
        fields.update((int(n), "nl_mono", float(v)) for n, v in _NL_MONO_RE.findall(block))
        raw[int(m.group(1))] = fields

    failures = []
    for entry in db:
        parsed = Counter()
        for s in entry.specificities:
            if not (isinstance(s.site, Site) and isinstance(s.position, Position)):
                failures.append((entry.id, "unknown enum", s))
            if not isinstance(s.classification, Classification):
                failures.append((entry.id, "unknown enum", s))
            parsed.update(
                [
                    (s.spec_num, "site", str(s.site)),
                    (s.spec_num, "position", str(s.position)),
                    (s.spec_num, "classification", str(s.classification)),
                    (s.spec_num, "hidden", "1" if s.hidden else "0"),
                    (s.spec_num, "group", str(s.group)),
                ]
            )
            parsed.update((s.spec_num, "nl_mono", nl.mono_mass) for nl in s.neutral_losses)
        expected = raw.pop(entry.id, Counter())
        if parsed != expected:
            failures.append((entry.id, "missing", dict(expected - parsed), "extra", dict(parsed - expected)))
    failures += [(i, "entry in OBO but not parsed") for i in raw]
    assert not failures, f"{len(failures)} entries differ from the raw OBO: {failures[:10]}"
