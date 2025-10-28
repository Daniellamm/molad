"""The Molad integration."""
from datetime import datetime
import logging
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE, CONF_TIME_ZONE, Platform
from homeassistant.helpers import config_validation as cv

from .const import (
    DEFAULT_DIASPORA,
    DOMAIN,
    SENSOR_IS_SHABBOS_MEVOCHIM,
    SENSOR_IS_UPCOMING_SHABBOS_MEVOCHIM,
    SENSOR_MOLAD,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Optional("diaspora", default=DEFAULT_DIASPORA): cv.boolean,
    },
    extra=vol.ALLOW_EXTRA,
)

PLATFORMS = [Platform.SENSOR]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Molad from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "diaspora": entry.options.get("diaspora", DEFAULT_DIASPORA),
    }

    # Forward the setup to the sensor platform.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok