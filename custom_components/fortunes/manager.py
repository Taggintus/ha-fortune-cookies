"""Central state for the Fortunes integration."""
from __future__ import annotations

import logging
import random
from datetime import datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.util import dt as dt_util

from .const import CONF_LANGUAGE, DOMAIN, MODE_DAILY, MODE_RANDOM
from .provider import FortuneDownloadError, async_ensure_fortunes

_LOGGER = logging.getLogger(__name__)


class FortuneManager:
    """Holds the current fortune and the selected language."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.language: str = entry.options.get(CONF_LANGUAGE, entry.data[CONF_LANGUAGE])
        self.fortune: str | None = None
        self.mode: str = MODE_DAILY
        self.updated: datetime | None = None
        self.count: int = 0
        self.last_error: str | None = None
        self._cache: dict[str, list[str]] = {}
        self._download_failed: set[str] = set()

    @property
    def signal(self) -> str:
        return f"{DOMAIN}_update_{self.entry.entry_id}"

    def _no_fortunes_message(self, language: str) -> str:
        message = (
            f"No fortunes available for '{language}'. "
            f"Put fortune files into {self.hass.config.path('fortunes', language)}"
        )
        if self.last_error:
            message += f" (download failed: {self.last_error})"
        return message

    async def _async_load(self, language: str, *, retry: bool = False) -> list[str]:
        """Load fortunes; download them if missing. A failed download is not retried
        automatically (only on restart or when the language is selected again)."""
        if (cached := self._cache.get(language)) is not None:
            return cached
        allow_download = retry or language not in self._download_failed
        self.last_error = None
        try:
            fortunes = await async_ensure_fortunes(
                self.hass, language, allow_download=allow_download
            )
        except FortuneDownloadError as err:
            self.last_error = str(err)
            _LOGGER.warning("Could not download fortunes for '%s': %s", language, err)
            fortunes = []
        if fortunes:
            self._cache[language] = fortunes
            self._download_failed.discard(language)
        elif allow_download:
            self._download_failed.add(language)
        return fortunes

    @callback
    def _publish(self, fortune: str | None, mode: str) -> None:
        self.fortune = fortune
        self.mode = mode
        self.updated = dt_util.now()
        async_dispatcher_send(self.hass, self.signal)

    async def async_show_daily(self) -> None:
        """Show the fortune of the day (same all day, per language)."""
        fortunes = await self._async_load(self.language)
        self.count = len(fortunes)
        if not fortunes:
            _LOGGER.warning(
                "No fortunes for '%s'. Put fortune files into %s",
                self.language,
                self.hass.config.path("fortunes", self.language),
            )
            self._publish(None, MODE_DAILY)
            return
        rng = random.Random(f"{self.language}:{dt_util.now().date().isoformat()}")
        self._publish(rng.choice(fortunes), MODE_DAILY)

    async def async_show_random(self) -> None:
        """Show a random fortune (button press)."""
        fortunes = await self._async_load(self.language)
        self.count = len(fortunes)
        if not fortunes:
            raise ServiceValidationError(self._no_fortunes_message(self.language))
        choice = fortunes[0]
        for _ in range(5):  # avoid showing the same one twice in a row
            choice = random.choice(fortunes)
            if choice != self.fortune:
                break
        self._publish(choice, MODE_RANDOM)

    async def async_set_language(self, language: str) -> None:
        """Switch the language (downloads missing fortunes) and persist it."""
        fortunes = await self._async_load(language, retry=True)
        if not fortunes:
            raise ServiceValidationError(self._no_fortunes_message(language))
        self.language = language
        self.hass.config_entries.async_update_entry(
            self.entry, options={**self.entry.options, CONF_LANGUAGE: language}
        )
        await self.async_show_daily()

    async def async_midnight(self, _now: datetime) -> None:
        await self.async_show_daily()


FortunesConfigEntry = ConfigEntry[FortuneManager]
