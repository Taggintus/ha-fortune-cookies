"""Constants for the Fortunes integration."""

DOMAIN = "fortunes"

CONF_LANGUAGE = "language"

# Language code -> display name. Add more here if you have fortune files for them.
LANGUAGES: dict[str, str] = {
    "de": "Deutsch",
    "en": "English",
    "fr": "Français",
    "es": "Español",
    "it": "Italiano",
}
DEFAULT_LANGUAGE = "en"

MODE_DAILY = "daily"
MODE_RANDOM = "random"
