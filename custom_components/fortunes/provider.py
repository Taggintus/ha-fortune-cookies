"""Find local fortunes or download them if missing."""
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .downloader import FortuneDownloadError, async_fetch_deb, install_deb
from .fortune_files import load_fortunes

_LOGGER = logging.getLogger(__name__)

__all__ = ["FortuneDownloadError", "async_ensure_fortunes"]


async def async_ensure_fortunes(
    hass: HomeAssistant, language: str, *, allow_download: bool = True
) -> list[str]:
    """Return all fortunes for a language.

    Local files always win. Only if there are none (and allow_download is set) the
    Debian package is downloaded into <config>/fortunes/<language>/.
    Raises FortuneDownloadError if that download fails.
    """
    config_dir = hass.config.path()
    fortunes = await hass.async_add_executor_job(load_fortunes, config_dir, language)
    if fortunes or not allow_download:
        return fortunes

    _LOGGER.info("No local fortune files for '%s', downloading from the Debian archive", language)
    deb = await async_fetch_deb(async_get_clientsession(hass), language)
    target = Path(config_dir, "fortunes", language)
    count = await hass.async_add_executor_job(install_deb, deb, target, language)
    _LOGGER.info("Unpacked %s fortune files for '%s' into %s", count, language, target)
    return await hass.async_add_executor_job(load_fortunes, config_dir, language)
