import urllib.request
from pathlib import Path

UNIMOD_OBO_URL = "http://www.unimod.org/obo/unimod.obo"
_DEFAULT_DEST = Path.home() / ".cache" / "unimodpy" / "UNIMOD.obo"


def download(dest: Path | str | None = None) -> Path:
    """Download the latest UNIMOD OBO from unimod.org.

    Args:
        dest: Destination path. Defaults to ~/.cache/unimodpy/UNIMOD.obo.

    Returns:
        Path to the downloaded file.
    """
    dest = Path(dest) if dest is not None else _DEFAULT_DEST
    dest.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(UNIMOD_OBO_URL, dest)
    return dest
