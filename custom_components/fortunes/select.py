"""Select for the fortune language."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import LANGUAGES
from .entity import FortunesEntity
from .manager import FortuneManager, FortunesConfigEntry


async def async_setup_entry(
    hass: HomeAssistant, entry: FortunesConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([LanguageSelect(entry.runtime_data)])


class LanguageSelect(FortunesEntity, SelectEntity):
    _attr_translation_key = "language"
    _attr_icon = "mdi:translate"
    _attr_options = list(LANGUAGES)

    def __init__(self, manager: FortuneManager) -> None:
        super().__init__(manager, "language")

    @property
    def current_option(self) -> str:
        return self.manager.language

    async def async_select_option(self, option: str) -> None:
        await self.manager.async_set_language(option)
