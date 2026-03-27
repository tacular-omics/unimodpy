from unimodpy import UnimodDatabase, parse_obo


def test_imports() -> None:
    assert callable(parse_obo)
    assert UnimodDatabase is not None
