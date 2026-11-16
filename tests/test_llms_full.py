"""Keep llms-full.txt, the usage guide for LLM tools, in step with the code."""

import dataclasses
import re
from pathlib import Path

import pytest

import unimodpy
from unimodpy._tabular import _COLUMNS
from unimodpy.models import UnimodEntry

GUIDE = Path(__file__).parent.parent / "llms-full.txt"


@pytest.fixture(scope="module")
def guide() -> str:
    return GUIDE.read_text(encoding="utf-8")


def _section(text: str, heading: str) -> str:
    """Body of the ``###`` section whose heading starts with ``heading``."""
    match = re.search(rf"^### {re.escape(heading)}.*?\n(.*?)(?=^#{{2,3}} |\Z)", text, re.M | re.S)
    assert match, f"no '### {heading}' section in llms-full.txt"
    return match.group(1)


def test_declared_version_matches_package(guide: str) -> None:
    match = re.search(r"usage guide for unimodpy (\d+)\.(\d+|x)", guide)
    assert match, "llms-full.txt does not say which unimodpy version it covers"
    major, minor = match.groups()
    version = unimodpy.__version__.split(".")
    assert major == version[0]
    assert minor in ("x", version[1])


def test_write_tsv_lists_every_column(guide: str) -> None:
    section = _section(guide, "Writing")
    start = section.index("`write_tsv(")
    paragraph = section[start:].split("\n\n", 1)[0]
    missing = [c for c in _COLUMNS if f"`{c}`" not in paragraph]
    assert not missing


def test_unimod_entry_table_lists_every_field(guide: str) -> None:
    section = _section(guide, "UnimodEntry")
    missing = [f.name for f in dataclasses.fields(UnimodEntry) if f"`{f.name}`" not in section]
    assert not missing


def test_phospho_example_matches_database(guide: str) -> None:
    section = _section(guide, "Sites and neutral losses")
    phospho = unimodpy.load()["Phospho"]
    site = re.search(r"\(<Site\.\w+: '(\w+)'>", section)
    assert site, "Phospho site example not found"
    assert site.group(1) == phospho.specificities[0].site.value
    count = re.search(r"# (\d+) of (\d+) visible", section)
    assert count, "Phospho visible-specificity count not found"
    visible = sum(not s.hidden for s in phospho.specificities)
    assert (int(count.group(1)), int(count.group(2))) == (
        visible,
        len(phospho.specificities),
    )
