"""HeatpumpIR integration for Home Assistant.

Provides a climate entity that controls heat pumps via an infrared emitter,
using the protocol implementations ported from the arduino-heatpumpir library
(https://github.com/ToniA/arduino-heatpumpir).
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_DEVICE_TYPE, DEVICE_TYPE_FAN


def _platforms_for_entry(entry: ConfigEntry) -> list[Platform]:
    """Return the platform this entry drives (climate by default, or fan)."""
    if entry.data.get(CONF_DEVICE_TYPE) == DEVICE_TYPE_FAN:
        return [Platform.FAN]
    return [Platform.CLIMATE]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HeatpumpIR from a config entry."""
    await hass.config_entries.async_forward_entry_setups(
        entry, _platforms_for_entry(entry)
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a HeatpumpIR config entry."""
    return await hass.config_entries.async_unload_platforms(
        entry, _platforms_for_entry(entry)
    )
