"""Config flow for Fortunes."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import CONF_LANGUAGE, DEFAULT_LANGUAGE, DOMAIN, LANGUAGES
from .provider import FortuneDownloadError, async_ensure_fortunes

_LOGGER = logging.getLogger(__name__)


class FortunesConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        errors: dict[str, str] = {}
        if user_input is not None:
            language = user_input[CONF_LANGUAGE]
            try:
                fortunes = await async_ensure_fortunes(self.hass, language)
            except FortuneDownloadError as err:
                _LOGGER.warning("Could not download fortunes for '%s': %s", language, err)
                errors["base"] = "download_failed"
            else:
                if fortunes:
                    return self.async_create_entry(
                        title="Fortunes", data={CONF_LANGUAGE: language}
                    )
                errors["base"] = "no_fortunes"

        default = self.hass.config.language[:2]
        if default not in LANGUAGES:
            default = DEFAULT_LANGUAGE
        default = (user_input or {}).get(CONF_LANGUAGE, default)

        schema = vol.Schema(
            {
                vol.Required(CONF_LANGUAGE, default=default): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            SelectOptionDict(value=code, label=name)
                            for code, name in LANGUAGES.items()
                        ],
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                )
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders={"path": self.hass.config.path("fortunes")},
        )
