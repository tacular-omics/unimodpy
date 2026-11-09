"""Execute every docstring example in the package."""

from __future__ import annotations

import doctest
import importlib
import importlib.util
import pkgutil
from types import ModuleType

import unimodpy

# Measured 2026-11-08 on main 895c799. Raise these when you add modules or examples; never
# lower them without saying why in the commit message.
MIN_MODULES = 10
MIN_EXAMPLES = 0

# MIN_MODULES is the count that holds with no extras installed: unimodpy plus the nine core
# modules. With the "server" extra it is 15, and the check below enforces that whenever the
# extra is present, which is every CI job and the workspace venv.
#
# These five are the only modules allowed to be absent, and only without that extra. Naming
# all five matters: when ``unimodpy.server`` cannot import, pkgutil cannot recurse into it,
# so its four submodules are never yielded at all rather than failing one by one.
_SERVER_MODULES = (
    "unimodpy.server",
    "unimodpy.server.app",
    "unimodpy.server.dashboard",
    "unimodpy.server.models",
    "unimodpy.server.references",
)

# server/app.py imports fastapi, mcp AND pydantic at module scope, so the subtree needs all
# three present, not one chosen name: with fastapi installed and mcp absent, keying the skip
# to fastapi alone lets the walk attempt the import and fail on "No module named 'mcp'". An
# optional extra arrives with its whole dependency set, so the question is whether the extra
# is installed. uvicorn is in the extra too but no module imports it, so it is deliberately
# not in this predicate: its absence cannot stop the subtree importing.
_SERVER_REQUIRES = ("fastapi", "mcp", "pydantic")


def _installed(module: str) -> bool:
    """Return True if ``module`` can be located, without importing it."""
    try:
        return importlib.util.find_spec(module) is not None
    except ModuleNotFoundError:
        return False


_HAVE_SERVER_EXTRA = all(_installed(dep) for dep in _SERVER_REQUIRES)


def _optional(name: str) -> bool:
    """True for a module that may be missing here: a ``server`` module without its extra."""
    return name in _SERVER_MODULES and not _HAVE_SERVER_EXTRA


def _walk_error(name: str) -> None:
    """Re-raise what pkgutil would otherwise swallow while walking into a subpackage."""
    if _optional(name):
        return
    raise  # noqa: PLE0704 - re-raises the ImportError pkgutil is handling


def _all_modules() -> list[ModuleType]:
    mods = [unimodpy]
    for _finder, name, _ispkg in pkgutil.walk_packages(
        unimodpy.__path__, prefix=f"{unimodpy.__name__}.", onerror=_walk_error
    ):
        try:
            mods.append(importlib.import_module(name))
        except ImportError:
            if _optional(name):
                continue
            raise
    return mods


def test_docstring_examples() -> None:
    mods = _all_modules()
    assert len(mods) >= MIN_MODULES, f"module walk found only {len(mods)}"
    if _HAVE_SERVER_EXTRA:
        found = {mod.__name__ for mod in mods}
        missing = [name for name in _SERVER_MODULES if name not in found]
        assert not missing, f"the server extra is installed but the walk missed {missing}"
    attempted = failed = 0
    for mod in mods:
        result = doctest.testmod(mod, verbose=False)
        attempted += result.attempted
        failed += result.failed
    assert failed == 0, f"{failed} of {attempted} docstring examples failed"
    assert attempted >= MIN_EXAMPLES, f"only {attempted} examples ran, expected >= {MIN_EXAMPLES}"
