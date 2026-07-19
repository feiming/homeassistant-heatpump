"""Climate platform for the HeatpumpIR integration."""

from __future__ import annotations

import logging

from homeassistant.components.climate import (
    FAN_AUTO,
    FAN_DIFFUSE,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    SWING_BOTH,
    SWING_HORIZONTAL,
    SWING_OFF,
    SWING_VERTICAL,
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.components.infrared import InfraredEmitterConsumerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_TEMPERATURE,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfTemperature,
)
from homeassistant.core import (
    Event,
    EventStateChangedData,
    HomeAssistant,
    State,
    callback,
)
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    CONF_INFRARED_ENTITY_ID,
    CONF_MODEL,
    CONF_TEMPERATURE_SENSOR_ID,
    DOMAIN,
)
from .ir import create_model
from .ir.base import (
    FAN_1,
    FAN_2,
    FAN_3,
    FAN_4,
    FAN_5,
    FAN_AUTO as IR_FAN_AUTO,
    FAN_SILENT,
    HDIR_AUTO,
    HDIR_SWING,
    POWER_OFF,
    POWER_ON,
    VDIR_AUTO,
    VDIR_SWING,
    HeatpumpIRBase,
    MODE_AUTO,
    MODE_COOL,
    MODE_DRY,
    MODE_FAN,
    MODE_HEAT,
)

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 1

# HA fan mode → internal IR fan constant
_HA_FAN_TO_IR: dict[str, int] = {
    FAN_AUTO: IR_FAN_AUTO,
    FAN_LOW: FAN_1,
    "medium_low": FAN_2,
    FAN_MEDIUM: FAN_3,
    "medium_high": FAN_4,
    FAN_HIGH: FAN_5,
    FAN_DIFFUSE: FAN_SILENT,
}

# Internal IR fan constant → HA fan mode
_IR_FAN_TO_HA: dict[int, str] = {v: k for k, v in _HA_FAN_TO_IR.items()}

# HA HVAC mode → (power, IR mode constant)
_HA_HVAC_TO_IR: dict[HVACMode, tuple[int, int]] = {
    HVACMode.OFF: (POWER_OFF, MODE_AUTO),
    HVACMode.HEAT: (POWER_ON, MODE_HEAT),
    HVACMode.COOL: (POWER_ON, MODE_COOL),
    HVACMode.DRY: (POWER_ON, MODE_DRY),
    HVACMode.FAN_ONLY: (POWER_ON, MODE_FAN),
    HVACMode.HEAT_COOL: (POWER_ON, MODE_AUTO),
}

# Swing mode → (vdir, hdir) IR constants
_HA_SWING_TO_IR: dict[str, tuple[int, int]] = {
    SWING_OFF: (VDIR_AUTO, HDIR_AUTO),
    SWING_VERTICAL: (VDIR_SWING, HDIR_AUTO),
    SWING_HORIZONTAL: (VDIR_AUTO, HDIR_SWING),
    SWING_BOTH: (VDIR_SWING, HDIR_SWING),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up HeatpumpIR climate entity from a config entry."""
    model = create_model(entry.data[CONF_MODEL])
    infrared_entity_id = entry.data[CONF_INFRARED_ENTITY_ID]
    async_add_entities([HeatpumpIRClimate(entry, model, infrared_entity_id)])


def _fan_modes_for_model(model: HeatpumpIRBase) -> list[str]:
    """Return the fan mode list based on how many fan speeds the model supports."""
    if model.fan_speeds == 0:
        return [FAN_AUTO]
    speeds = [FAN_AUTO, FAN_LOW]
    if model.fan_speeds >= 3:
        speeds.append(FAN_MEDIUM)
    if model.fan_speeds >= 4:
        speeds.append("medium_high")
    if model.fan_speeds >= 5:
        speeds.append(FAN_HIGH)
    if model.fan_speeds >= 6:
        speeds.append(FAN_DIFFUSE)
    return speeds


class HeatpumpIRClimate(InfraredEmitterConsumerEntity, ClimateEntity, RestoreEntity):
    """Climate entity controlling a heat pump via an infrared emitter."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_assumed_state = True
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.SWING_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_hvac_modes = [
        HVACMode.OFF,
        HVACMode.HEAT_COOL,
        HVACMode.HEAT,
        HVACMode.COOL,
        HVACMode.DRY,
        HVACMode.FAN_ONLY,
    ]
    _attr_swing_modes = [SWING_OFF, SWING_VERTICAL, SWING_HORIZONTAL, SWING_BOTH]

    def __init__(
        self,
        entry: ConfigEntry,
        model: HeatpumpIRBase,
        infrared_entity_id: str,
    ) -> None:
        """Initialize the climate entity."""
        self._model = model
        self._infrared_emitter_entity_id = infrared_entity_id
        self._temperature_sensor_entity_id = entry.options.get(
            CONF_TEMPERATURE_SENSOR_ID
        )

        self._attr_unique_id = entry.entry_id
        from homeassistant.helpers.device_registry import DeviceInfo
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=model.display_name,
            manufacturer=model.display_name.split()[0],
            model=model.model_id,
        )

        self._attr_min_temp = model.min_temp
        self._attr_max_temp = model.max_temp
        self._attr_target_temperature_step = 1.0
        self._attr_fan_modes = _fan_modes_for_model(model)

        # Sensible defaults — overwritten by restore in async_added_to_hass
        self._attr_hvac_mode = HVACMode.OFF
        self._attr_target_temperature = 22.0
        self._attr_fan_mode = FAN_AUTO
        self._attr_swing_mode = SWING_OFF
        self._attr_current_temperature = None

    async def async_added_to_hass(self) -> None:
        """Restore last known state when HA starts."""
        await super().async_added_to_hass()

        if self._temperature_sensor_entity_id:
            self._update_current_temperature(
                self.hass.states.get(self._temperature_sensor_entity_id)
            )
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass,
                    [self._temperature_sensor_entity_id],
                    self._handle_temperature_sensor_change,
                )
            )

        last = await self.async_get_last_state()
        if last is None:
            return

        if last.state in {m.value for m in HVACMode}:
            self._attr_hvac_mode = HVACMode(last.state)

        attrs = last.attributes
        if (temp := attrs.get(ATTR_TEMPERATURE)) is not None:
            try:
                self._attr_target_temperature = float(temp)
            except (ValueError, TypeError):
                pass

        if (fan := attrs.get("fan_mode")) and fan in self._attr_fan_modes:
            self._attr_fan_mode = fan

        if (swing := attrs.get("swing_mode")) and swing in self._attr_swing_modes:
            self._attr_swing_mode = swing

    @callback
    def _handle_temperature_sensor_change(
        self, event: Event[EventStateChangedData]
    ) -> None:
        """Update current_temperature from the feedback sensor's new state."""
        self._update_current_temperature(event.data["new_state"])
        self.async_write_ha_state()

    def _update_current_temperature(self, state: State | None) -> None:
        """Set current_temperature from a sensor state, ignoring bad readings."""
        if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return
        try:
            self._attr_current_temperature = float(state.state)
        except ValueError:
            _LOGGER.warning(
                "Feedback sensor %s has a non-numeric state: %s",
                self._temperature_sensor_entity_id,
                state.state,
            )

    # ------------------------------------------------------------------
    # Setters — each updates local state and sends the full IR command
    # ------------------------------------------------------------------

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new HVAC mode."""
        self._attr_hvac_mode = hvac_mode
        await self._send_current_state()
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs: float) -> None:
        """Set target temperature."""
        if (temp := kwargs.get(ATTR_TEMPERATURE)) is not None:
            self._attr_target_temperature = temp
            if self._attr_hvac_mode != HVACMode.OFF:
                await self._send_current_state()
            self.async_write_ha_state()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set fan mode."""
        self._attr_fan_mode = fan_mode
        if self._attr_hvac_mode != HVACMode.OFF:
            await self._send_current_state()
        self.async_write_ha_state()

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        """Set swing mode."""
        self._attr_swing_mode = swing_mode
        if self._attr_hvac_mode != HVACMode.OFF:
            await self._send_current_state()
        self.async_write_ha_state()

    async def async_turn_on(self) -> None:
        """Turn on (restore last non-off mode or default to HEAT_COOL)."""
        if self._attr_hvac_mode == HVACMode.OFF:
            self._attr_hvac_mode = HVACMode.HEAT_COOL
        await self._send_current_state()
        self.async_write_ha_state()

    async def async_turn_off(self) -> None:
        """Turn off."""
        self._attr_hvac_mode = HVACMode.OFF
        await self._send_current_state()
        self.async_write_ha_state()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _send_current_state(self) -> None:
        """Build the IR command from current state and send it."""
        power, ir_mode = _HA_HVAC_TO_IR.get(
            self._attr_hvac_mode, (POWER_OFF, MODE_AUTO)
        )

        ir_fan = _HA_FAN_TO_IR.get(self._attr_fan_mode or FAN_AUTO, IR_FAN_AUTO)

        swing_v, swing_h = _HA_SWING_TO_IR.get(
            self._attr_swing_mode or SWING_OFF, (VDIR_AUTO, HDIR_AUTO)
        )

        temp = int(self._attr_target_temperature or self._model.min_temp)

        try:
            command = self._model.get_command(
                power=power,
                mode=ir_mode,
                fan=ir_fan,
                temp=temp,
                swing_v=swing_v,
                swing_h=swing_h,
            )
        except Exception:
            _LOGGER.exception(
                "Failed to build IR command for model %s", self._model.model_id
            )
            return

        await self._send_command(command)
