"""Button for a new random fortune."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import FortunesEntity
from .manager import FortuneManager, FortunesConfigEntry


async def async_setup_entry(
    hass: HomeAssistant, entry: FortunesConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([NewFortuneButton(entry.runtime_data)])


class NewFortuneButton(FortunesEntity, ButtonEntity):
    _attr_translation_key = "new_fortune"
    _attr_icon = "mdi:dice-multiple"

    def __init__(self, manager: FortuneManager) -> None:
        super().__init__(manager, "new_fortune")

    async def async_press(self) -> None:
        await self.manager.async_show_random()
