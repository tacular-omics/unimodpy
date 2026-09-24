"""Download the latest UNIMOD OBO file from unimod.org."""

import os
import tempfile
import urllib.request
from pathlib import Path

UNIMOD_OBO_URL = "https://www.unimod.org/obo/unimod.obo"
_DEFAULT_DEST = Path.home() / ".cache" / "unimodpy" / "UNIMOD.obo"


def download(dest: Path | str | None = None, *, force: bool = False) -> Path:
    """Download the latest UNIMOD OBO from unimod.org and cache it locally.

    Args:
        dest: Destination path. Defaults to ~/.cache/unimodpy/UNIMOD.obo.
        force: Re-download even if *dest* already exists. Without it an existing
            file is returned as is.

    Returns:
        Path to the downloaded (or cached) file.
    """
    dest = Path(dest) if dest is not None else _DEFAULT_DEST
    if dest.exists() and not force:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    # Download next to dest, then rename: a failed download never leaves a truncated cache file.
    fd, tmp_name = tempfile.mkstemp(dir=dest.parent, prefix=f".{dest.name}.", suffix=".part")
    os.close(fd)
    try:
        urllib.request.urlretrieve(UNIMOD_OBO_URL, tmp_name)
        os.replace(tmp_name, dest)
    finally:
        Path(tmp_name).unlink(missing_ok=True)
    return dest
