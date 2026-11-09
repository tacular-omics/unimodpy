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


def test_server_gate_agrees_with_importing_the_subtree() -> None:
    """Check the skip's verdict against importing the gated subtree, not against a count.

    ``MIN_MODULES`` is the lean count, so a key that wrongly reads "absent" where the extra
    is installed walks exactly those 10 modules, meets the floor, and skips the conditional
    check in the test above: the five server modules' examples would stop running with no
    assertion failing anywhere. A count a correct skip also produces cannot separate a
    correct verdict from a stuck one; importing the subtree can.

    Agreeing is not enough either. When the verdict is "absent" and the import does fail,
    the name that was missing has to be one the key names: a server module that acquires an
    import of some fourth root fails for a reason the key knows nothing about, the verdict
    is "absent" for the right reason by accident, and the skip swallows a broken module as
    an absent extra. That is mzmlpy's base-install defect with the verdict inverted - there
    the gate said "present" so it came out loud, and here it would be silent.
    """
    missing = ""
    try:
        importlib.import_module(_SERVER_MODULES[0])
    except ImportError as exc:
        importable, why = False, f": {exc}"
        missing = (getattr(exc, "name", "") or "").split(".")[0]
    else:
        importable, why = True, ""
    assert importable == _HAVE_SERVER_EXTRA, (
        f"the skip says the server extra is {'present' if _HAVE_SERVER_EXTRA else 'absent'} but "
        f"{_SERVER_MODULES[0]} is {'importable' if importable else 'not importable'}{why}"
    )
    if not importable:
        assert missing in _SERVER_REQUIRES, (
            f"{_SERVER_MODULES[0]} is missing {missing!r}, which the gate's key does not name, so this is a "
            f"broken module and not an absent extra; the key names {_SERVER_REQUIRES}"
        )
