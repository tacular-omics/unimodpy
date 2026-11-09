"""The helper scripts default to the bundled OBO file."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).parent.parent / "scripts"


@pytest.mark.parametrize("name", ["print_entries", "audit_obo", "export_json"])
def test_script_default_obo_path_exists(name: str) -> None:
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.OBO_PATH.is_file()


def test_export_json_writes_beside_repo(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location("export_json", _SCRIPTS / "export_json.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    monkeypatch.chdir(tmp_path)
    module.export()

    assert not (tmp_path / "docs").exists()
    assert module.OUT_PATH.is_file()
    assert module.META_PATH.is_file()


def _release_version():
    spec = importlib.util.spec_from_file_location("release_version", _SCRIPTS / "release_version.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("has_date", [True, False])
def test_sync_set_updates_citation_date_released(tmp_path: Path, has_date: bool) -> None:
    import datetime
    import shutil

    rv = _release_version()
    root = _SCRIPTS.parent
    for rel in ("pyproject.toml", "CHANGELOG.md", "CITATION.cff", str(rv.SOURCE)):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(root / rel, tmp_path / rel)
    citation = tmp_path / "CITATION.cff"
    text = "\n".join(line for line in citation.read_text().splitlines() if not line.startswith("date-released"))
    if has_date:
        text = text.replace('version: "', 'date-released: "2000-01-01"\nversion: "', 1)
    citation.write_text(text + "\n")

    rv.sync(tmp_path, "9.9.9")

    out = citation.read_text()
    assert f'date-released: "{datetime.date.today().isoformat()}"' in out
    assert out.count("date-released:") == 1
    assert 'version: "9.9.9"' in out
