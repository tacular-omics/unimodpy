import unimodpy
from unimodpy import UnimodDatabase, parse_obo


def test_imports() -> None:
    assert callable(parse_obo)
    assert UnimodDatabase is not None


def test_version() -> None:
    assert isinstance(unimodpy.__version__, str)
    assert unimodpy.__version__
