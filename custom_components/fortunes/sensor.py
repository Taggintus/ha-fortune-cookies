"""Sensor with the current fortune."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import FortunesEntity
from .manager import FortuneManager, FortunesConfigEntry


async def async_setup_entry(
    hass: HomeAssistant, entry: FortunesConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([FortuneSensor(entry.runtime_data)])


class FortuneSensor(FortunesEntity, SensorEntity):
    _attr_translation_key = "fortune"
    _attr_icon = "mdi:cookie"

    def __init__(self, manager: FortuneManager) -> None:
        super().__init__(manager, "fortune")

    @property
    def native_value(self) -> str | None:
        """State is limited to 255 chars; the full text is in the 'fortune' attribute."""
        if self.manager.fortune is None:
            return None
        text = " ".join(self.manager.fortune.split())
        return text if len(text) <= 255 else text[:254] + "…"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        m = self.manager
        return {
            "fortune": m.fortune,
            "language": m.language,
            "mode": m.mode,
            "updated": m.updated.isoformat() if m.updated else None,
            "fortune_count": m.count,
        }
