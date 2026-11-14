"""Fortunes: a fortune cookie of the day from classic Unix fortune files."""
from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_change

from .manager import FortuneManager, FortunesConfigEntry

PLATFORMS = [Platform.SENSOR, Platform.BUTTON, Platform.SELECT]


async def async_setup_entry(hass: HomeAssistant, entry: FortunesConfigEntry) -> bool:
    manager = FortuneManager(hass, entry)
    await manager.async_show_daily()
    entry.runtime_data = manager
    # New fortune of the day shortly after midnight (Home Assistant time zone)
    entry.async_on_unload(
        async_track_time_change(hass, manager.async_midnight, hour=0, minute=0, second=10)
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: FortunesConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
