import pytest

from unimodpy import UnimodDatabase, load


@pytest.fixture(scope="session")
def db() -> UnimodDatabase:
    return load()
