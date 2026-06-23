"""HeatpumpIR integration for Home Assistant.

Provides a climate entity that controls heat pumps via an infrared emitter,
using the protocol implementations ported from the arduino-heatpumpir library
(https://github.com/ToniA/arduino-heatpumpir).
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

PLATFORMS = [Platform.CLIMATE]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HeatpumpIR from a config entry."""
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a HeatpumpIR config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
