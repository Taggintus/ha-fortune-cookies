"""Download fortune files from the Debian archive.

The integration ships no fortune data. If a language has no local files, the matching
Debian package is downloaded to the user's own Home Assistant instance and only the
fortune files are unpacked. No Home Assistant imports here, so it can be tested alone.
"""
from __future__ import annotations

import asyncio
import io
import logging
import lzma
import re
import tarfile
import zlib
from pathlib import Path, PurePosixPath
from urllib.parse import unquote

import aiohttp

from .fortune_files import SKIP_DIRS, SKIP_SUFFIXES

_LOGGER = logging.getLogger(__name__)

# Tried in this order until one works
MIRRORS = (
    "https://deb.debian.org/debian",
    "https://ftp.de.debian.org/debian",
    "https://mirrors.mit.edu/debian",
)

# language -> [(source directory in the pool, binary package)]; the first working entry wins
SOURCES: dict[str, list[tuple[str, str]]] = {
    "de": [("fortunes-de", "fortunes-de")],
    "en": [("fortune-mod", "fortunes"), ("fortune-mod", "fortunes-min")],
    "fr": [("fortunes-fr", "fortunes-fr")],
    "es": [("fortunes-es", "fortunes-es")],
    "it": [("fortunes-it", "fortunes-it")],
}

# Files that are not unpacked (matched by file name, if present in a package)
EXCLUDE_FILES: dict[str, set[str]] = {
    "en": {"songs-poems", "ethnic", "art", "ascii-art"},
}

DATA_PREFIX = ("usr", "share", "games", "fortunes")
MAX_DOWNLOAD_BYTES = 30 * 1024 * 1024
MAX_FILE_BYTES = 20 * 1024 * 1024
REQUEST_TIMEOUT = 20  # seconds per request
TOTAL_TIMEOUT = 90  # seconds for the whole download
HEADERS = {"User-Agent": "ha-fortunes (Home Assistant custom integration)"}


class FortuneDownloadError(Exception):
    """Download or unpacking failed."""


def _version_key(version: str) -> tuple:
    """Rough Debian-style version ordering (numbers numerically, newest last)."""
    return tuple(
        (1, int(tok)) if tok.isdigit() else (0, tok)
        for tok in re.findall(r"\d+|[A-Za-z]+", unquote(version))
    )


def pick_latest_deb(listing: str, package: str) -> str | None:
    """Return the file name of the newest <package>_<version>_all.deb in a directory index."""
    pattern = re.compile(rf"^{re.escape(package)}_(?P<ver>[^_/]+)_all\.deb$")
    best: tuple[str, str] | None = None
    for href in re.findall(r"""href=["']([^"']+)["']""", listing):
        name = href.rsplit("/", 1)[-1]
        match = pattern.match(unquote(name))
        if match and (best is None or _version_key(match["ver"]) > _version_key(best[0])):
            best = (match["ver"], name)
    return best[1] if best else None


async def _async_get(session, url: str) -> bytes:
    try:
        async with session.get(
            url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
        ) as resp:
            resp.raise_for_status()
            data = await resp.read()
    except (aiohttp.ClientError, TimeoutError) as err:
        raise FortuneDownloadError(f"{url}: {err}") from err
    if len(data) > MAX_DOWNLOAD_BYTES:
        raise FortuneDownloadError(f"{url}: response too large")
    return data


async def async_fetch_deb(session, language: str) -> bytes:
    """Download the newest Debian package with fortunes for a language."""
    candidates = SOURCES.get(language)
    if not candidates:
        raise FortuneDownloadError(f"No download source for language '{language}'")
    errors: list[str] = []
    try:
        async with asyncio.timeout(TOTAL_TIMEOUT):
            for source_dir, package in candidates:
                for mirror in MIRRORS:
                    base = f"{mirror}/pool/main/{source_dir[0]}/{source_dir}/"
                    try:
                        listing = (await _async_get(session, base)).decode("utf-8", "replace")
                        name = pick_latest_deb(listing, package)
                        if name is None:
                            raise FortuneDownloadError(f"{base}: no '{package}' package listed")
                        _LOGGER.debug("Downloading %s%s", base, name)
                        return await _async_get(session, base + name)
                    except FortuneDownloadError as err:
                        errors.append(str(err))
    except TimeoutError as err:
        errors.append(f"timeout after {TOTAL_TIMEOUT}s")
        raise FortuneDownloadError("; ".join(errors[-3:])) from err
    raise FortuneDownloadError("; ".join(errors[-3:]) or "download failed")


def _read_ar_member(deb: bytes, prefix: str) -> tuple[str, bytes]:
    """Return (name, content) of the first member of an ar archive starting with prefix."""
    if not deb.startswith(b"!<arch>\n"):
        raise FortuneDownloadError("Not a Debian package (ar archive expected)")
    pos = 8
    while pos + 60 <= len(deb):
        header = deb[pos : pos + 60]
        name = header[:16].decode("ascii", "replace").strip().rstrip("/")
        try:
            size = int(header[48:58])
        except ValueError as err:
            raise FortuneDownloadError("Corrupt Debian package") from err
        start = pos + 60
        if name.startswith(prefix):
            return name, deb[start : start + size]
        pos = start + size + (size % 2)
    raise FortuneDownloadError("Debian package contains no data archive")


def install_deb(deb: bytes, target_dir: Path, language: str) -> int:
    """Unpack the fortune files of a Debian package into target_dir (blocking).

    Only regular files below usr/share/games/fortunes/ are written. Index files,
    'off' folders and excluded files are skipped. Returns the number of files written.
    """
    name, data = _read_ar_member(deb, "data.tar")
    if name.endswith(".zst"):
        raise FortuneDownloadError("zstd-compressed packages are not supported")
    exclude = EXCLUDE_FILES.get(language, set())
    written = 0
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as tar:
            for member in tar:
                if not member.isreg() or member.size > MAX_FILE_BYTES:
                    continue
                parts = [p for p in PurePosixPath(member.name).parts if p not in (".", "/")]
                if tuple(parts[:4]) != DATA_PREFIX or len(parts) <= 4:
                    continue
                rel = parts[4:]
                if ".." in rel or any(p.lower() in SKIP_DIRS for p in rel[:-1]):
                    continue
                filename = rel[-1]
                if Path(filename).suffix.lower() in SKIP_SUFFIXES:
                    continue
                if filename in exclude or Path(filename).stem in exclude:
                    continue
                source = tar.extractfile(member)
                if source is None:
                    continue
                dest = target_dir.joinpath(*rel)
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(source.read())
                written += 1
    except (tarfile.TarError, EOFError, lzma.LZMAError, zlib.error, OSError) as err:
        raise FortuneDownloadError(f"Could not unpack package: {err}") from err
    if written == 0:
        raise FortuneDownloadError("Package contained no fortune files")
    return written
