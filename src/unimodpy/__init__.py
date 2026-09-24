"""Python library for parsing and querying the UNIMOD mass spectrometry modifications database."""

from unimodpy._download import download
from unimodpy._obo_writer import write_obo
from unimodpy._tabular import write_tsv
from unimodpy.database import UnimodDatabase
from unimodpy.errors import UnimodError, UnimodKeyError, UnimodParseError
from unimodpy.models import Classification, NeutralLoss, Position, Site, Specificity, UnimodEntry
from unimodpy.parser import load, parse_obo

__version__ = "1.0.0"

__all__ = [
    "__version__",
    "Classification",
    "NeutralLoss",
    "Position",
    "Site",
    "Specificity",
    "UnimodEntry",
    "UnimodDatabase",
    "UnimodError",
    "UnimodKeyError",
    "UnimodParseError",
    "download",
    "load",
    "parse_obo",
    "write_obo",
    "write_tsv",
]
