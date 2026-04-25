"""Python library for parsing and querying the UNIMOD mass spectrometry modifications database."""

from importlib.metadata import version

from unimodpy._download import download
from unimodpy._obo_writer import write_obo
from unimodpy._tabular import write_tsv
from unimodpy.database import UnimodDatabase
from unimodpy.models import Classification, NeutralLoss, Position, Site, Specificity, UnimodEntry
from unimodpy.parser import load, parse_obo

__version__ = version("unimodpy")

__all__ = [
    "__version__",
    "Classification",
    "NeutralLoss",
    "Position",
    "Site",
    "Specificity",
    "UnimodEntry",
    "UnimodDatabase",
    "download",
    "load",
    "parse_obo",
    "write_obo",
    "write_tsv",
]
