"""Read classic Unix fortune files (entries separated by a line containing only '%').

This module has no Home Assistant imports so it can be tested on its own.
"""
from __future__ import annotations

import logging
import re
from collections.abc import Iterator
from pathlib import Path

_LOGGER = logging.getLogger(__name__)

SYSTEM_FORTUNE_DIR = Path("/usr/share/games/fortunes")
SKIP_DIRS = {"off"}  # "offensive" databases
SKIP_SUFFIXES = {".dat", ".u8", ".md"}
_SEPARATOR = re.compile(r"^%[ \t]*$", re.MULTILINE)


def _iter_files(directory: Path, recursive: bool) -> Iterator[Path]:
    try:
        items = sorted(directory.iterdir())
    except OSError:
        return
    for item in items:
        if item.is_dir():
            if recursive and item.name.lower() not in SKIP_DIRS:
                yield from _iter_files(item, True)
        elif item.is_file() and item.suffix.lower() not in SKIP_SUFFIXES:
            yield item


def parse_fortune_file(path: Path) -> list[str]:
    """Return all entries of one fortune file."""
    try:
        raw = path.read_bytes()
    except OSError as err:
        _LOGGER.warning("Cannot read %s: %s", path, err)
        return []
    if b"\x00" in raw[:2048]:
        return []  # binary file, e.g. a strfile index
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")  # many old fortune files are ISO-8859-1
    text = text.replace("\r\n", "\n")
    entries = []
    for chunk in _SEPARATOR.split(text):
        entry = chunk.strip("\n").rstrip()
        if entry.strip():
            entries.append(entry)
    return entries


def find_fortune_files(config_dir: str, language: str) -> list[Path]:
    """Find fortune files for a language. The first directory with files wins.

    1. <config>/fortunes/<language>/   (recursive)
    2. /usr/share/games/fortunes/<language>/   (recursive, Debian/Ubuntu)
    3. for English only: /usr/share/games/fortunes/   (top level only)
    """
    candidates: list[tuple[Path, bool]] = [
        (Path(config_dir) / "fortunes" / language, True),
        (SYSTEM_FORTUNE_DIR / language, True),
    ]
    if language == "en":
        candidates.append((SYSTEM_FORTUNE_DIR, False))
    for directory, recursive in candidates:
        files = list(_iter_files(directory, recursive))
        if files:
            return files
    return []


def load_fortunes(config_dir: str, language: str) -> list[str]:
    """Load all unique fortunes for a language (blocking, run in executor)."""
    seen: set[str] = set()
    result: list[str] = []
    for path in find_fortune_files(config_dir, language):
        for entry in parse_fortune_file(path):
            if entry not in seen:
                seen.add(entry)
                result.append(entry)
    return result
