"""Property tests: `[]`, `get` and `in` agree for every key form, and never crash."""

from __future__ import annotations

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

import unimodpy

_DB = unimodpy.load()
_IDS = sorted(e.id for e in _DB)
_NAMES = [e.name for e in _DB]
_SETTINGS = settings(max_examples=300, deadline=None, suppress_health_check=[HealthCheck.too_slow])


def _id_forms(n: int) -> st.SearchStrategy[object]:
    return st.sampled_from([n, str(n), f"{n:04d}", f"UNIMOD:{n}", f"unimod:{n}", f" UNIMOD:{n} "])


_existing = st.sampled_from(_IDS).flatmap(_id_forms)
_names = st.sampled_from(_NAMES).flatmap(lambda s: st.sampled_from([s, s.upper(), s.lower()]))
_junk = st.one_of(
    st.integers(min_value=-(10**6), max_value=10**6).flatmap(_id_forms),
    st.text(max_size=20),
    st.text(max_size=8).map(lambda s: f"UNIMOD:{s}"),
    st.none(),
    st.floats(allow_nan=False),
    st.tuples(st.integers()),
)
_keys = st.one_of(_existing, _names, _junk)


def _getitem(key: object):
    try:
        return _DB[key]
    except KeyError:
        return None


@_SETTINGS
@given(_keys)
def test_contains_getitem_and_get_agree(key):
    entry = _DB.get(key)  # never raises
    assert _getitem(key) is entry
    assert (key in _DB) is (entry is not None)


def test_every_entry_resolves_to_itself_by_every_key():
    """Every key form of every entry returns that same entry, not just some entry.

    Catches a name or id index that maps a key to the wrong entry: a name that
    case-folds onto another entry's name, a name that parses as an id, an id form
    ("0021", " UNIMOD:21 ") that misparses, or a site index missing an entry.
    """
    failures = []
    by_site: dict[str, set[int]] = {}
    for entry in _DB:
        n = entry.id
        keys = [n, str(n), f"{n:04d}", f"UNIMOD:{n}", f"unimod:{n}", f" UNIMOD:{n} "]
        keys += [entry.name, entry.name.upper(), entry.name.lower()]
        failures += [(n, k) for k in keys if _DB.get(k) is not entry]
        if _DB.get_by_id(n) is not entry or _DB.get_by_name(entry.name) is not entry or entry not in _DB:
            failures.append((n, "get_by_id/get_by_name/in"))
        for site in {str(s.site) for s in entry.specificities}:
            if site not in by_site:
                by_site[site] = {id(e) for e in _DB.get_by_site(site)}
            if id(entry) not in by_site[site]:
                failures.append((n, f"get_by_site({site!r})"))
    assert not failures, f"{len(failures)} lookups returned another entry: {failures[:20]}"


@_SETTINGS
@given(st.text(max_size=30))
def test_search_never_crashes(query):
    results = _DB.search(query)
    assert isinstance(results, list)
    assert all(r in _DB for r in results)


def test_len_matches_iteration():
    assert len(_DB) == len(list(_DB)) == len(set(_IDS))
