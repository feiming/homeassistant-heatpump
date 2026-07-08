"""Fan platform for the HeatpumpIR integration.

Drives an IR ceiling fan (currently the Panasonic 9-speed model) through an
infrared emitter, mapping Home Assistant's 0-100 % speed onto the fan's nine
discrete steps.
"""

from __future__ import annotations

import logging
import math

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.components.infrared import InfraredEmitterConsumerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util.percentage import (
    percentage_to_ranged_value,
    ranged_value_to_percentage,
)
from homeassistant.util.scaling import int_states_in_range

from .const import CONF_INFRARED_ENTITY_ID, CONF_MODEL, DOMAIN
from .ir import create_fan_model
from .ir.panasonic_fan import MAX_SPEED, MIN_SPEED, SPEED_OFF

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 1

#: Inclusive range of the fan's discrete running speeds.
_SPEED_RANGE = (MIN_SPEED, MAX_SPEED)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the HeatpumpIR fan entity from a config entry."""
    model = create_fan_model(entry.data[CONF_MODEL])
    infrared_entity_id = entry.data[CONF_INFRARED_ENTITY_ID]
    async_add_entities([HeatpumpIRFan(entry, model, infrared_entity_id)])


class HeatpumpIRFan(InfraredEmitterConsumerEntity, FanEntity, RestoreEntity):
    """Fan entity controlling an IR ceiling fan via an infrared emitter."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_assumed_state = True
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )

    def __init__(
        self,
        entry: ConfigEntry,
        model: object,
        infrared_entity_id: str,
    ) -> None:
        """Initialize the fan entity."""
        self._model = model
        self._infrared_emitter_entity_id = infrared_entity_id

        self._attr_unique_id = entry.entry_id
        from homeassistant.helpers.device_registry import DeviceInfo

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=model.display_name,
            manufacturer=model.display_name.split()[0],
            model=model.model_id,
        )

        # Current speed: SPEED_OFF (0) or MIN_SPEED..MAX_SPEED.
        self._speed = SPEED_OFF
        # Speed to restore when turned on without an explicit percentage.
        self._last_on_speed = MAX_SPEED

    async def async_added_to_hass(self) -> None:
        """Restore last known state when HA starts."""
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is None:
            return

        attrs = last.attributes
        pct = attrs.get("percentage")
        if pct:
            self._speed = self._percentage_to_speed(pct)
            self._last_on_speed = self._speed
        elif last.state == "on":
            self._speed = self._last_on_speed

    @property
    def speed_count(self) -> int:
        """Return the number of discrete speeds the fan supports."""
        return int_states_in_range(_SPEED_RANGE)

    @property
    def is_on(self) -> bool:
        """Return True if the fan is running."""
        return self._speed != SPEED_OFF

    @property
    def percentage(self) -> int:
        """Return the current speed as a percentage (0 when off)."""
        if self._speed == SPEED_OFF:
            return 0
        return ranged_value_to_percentage(_SPEED_RANGE, self._speed)

    @staticmethod
    def _percentage_to_speed(percentage: int) -> int:
        """Map a 1-100 % request onto a discrete running speed."""
        return math.ceil(percentage_to_ranged_value(_SPEED_RANGE, percentage))

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the fan speed as a percentage (0 turns it off)."""
        if percentage == 0:
            await self.async_turn_off()
            return
        self._speed = self._percentage_to_speed(percentage)
        self._last_on_speed = self._speed
        await self._send_speed()
        self.async_write_ha_state()

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: object,
    ) -> None:
        """Turn the fan on, optionally at a given percentage."""
        if percentage is not None:
            await self.async_set_percentage(percentage)
            return
        self._speed = self._last_on_speed
        await self._send_speed()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: object) -> None:
        """Turn the fan off."""
        self._speed = SPEED_OFF
        await self._send_speed()
        self.async_write_ha_state()

    async def _send_speed(self) -> None:
        """Build the IR command for the current speed and send it."""
        try:
            command = self._model.get_command(self._speed)
        except Exception:
            _LOGGER.exception(
                "Failed to build IR command for fan model %s", self._model.model_id
            )
            return
        await self._send_command(command)
