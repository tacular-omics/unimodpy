"""The helper scripts default to the bundled OBO file."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).parent.parent / "scripts"


@pytest.mark.parametrize("name", ["print_entries", "audit_obo"])
def test_script_default_obo_path_exists(name: str) -> None:
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.OBO_PATH.is_file()
