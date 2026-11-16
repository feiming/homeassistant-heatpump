"""Climate platform for the HeatpumpIR integration."""

from __future__ import annotations

import logging
import time

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
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
    RestoreClimate,
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

from .const import (
    CONF_CONTROL_DEADBAND,
    CONF_CONTROL_INTERVAL,
    CONF_CONTROL_MAX_OFFSET,
    CONF_CONTROL_STRATEGY,
    CONF_INFRARED_ENTITY_ID,
    CONF_MODEL,
    CONF_TEMPERATURE_SENSOR_ID,
    CONTROL_NONE,
    CONTROL_OFFSET,
    CONTROL_POWER,
    CONTROL_SETPOINT,
    DEFAULT_CONTROL_DEADBAND,
    DEFAULT_CONTROL_INTERVAL,
    DEFAULT_CONTROL_MAX_OFFSET,
    DEFAULT_CONTROL_STRATEGY,
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

# Seam for tests — monotonic clock used to rate-limit offset adjustments.
_monotonic = time.monotonic

# °C the offset strategy moves the setpoint by on each adjustment.
_OFFSET_STEP = 1.0

# Tolerance (°C) around the target before the feedback-sensor heuristic
# considers the target reached and reports IDLE instead of HEATING/COOLING.
_ACTION_DEADBAND = 0.3

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


def _as_float(value: object, default: float) -> float:
    """Coerce an options value to float, falling back to a default."""
    try:
        return float(value)  # type: ignore[arg-type]
    except (ValueError, TypeError):
        return default


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


class HeatpumpIRClimate(InfraredEmitterConsumerEntity, RestoreClimate):
    """Climate entity controlling a heat pump via an infrared emitter."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_assumed_state = True
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
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
        self._control_strategy = entry.options.get(
            CONF_CONTROL_STRATEGY, DEFAULT_CONTROL_STRATEGY
        )
        self._control_deadband = _as_float(
            entry.options.get(CONF_CONTROL_DEADBAND), DEFAULT_CONTROL_DEADBAND
        )
        self._control_max_offset = _as_float(
            entry.options.get(CONF_CONTROL_MAX_OFFSET), DEFAULT_CONTROL_MAX_OFFSET
        )
        self._control_interval = (
            _as_float(
                entry.options.get(CONF_CONTROL_INTERVAL), DEFAULT_CONTROL_INTERVAL
            )
            * 60
        )

        # False while a stop/setpoint strategy is holding the unit off because
        # the target has been reached. Always True for the other strategies.
        self._demand_active = True
        # Learned bias (°C) the offset strategy applies to the setpoint.
        self._control_offset = 0.0
        self._last_offset_adjust: float | None = None

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
        self._attr_native_target_temperature = 22.0
        self._attr_fan_mode = FAN_AUTO
        self._attr_swing_mode = SWING_OFF
        self._attr_native_current_temperature = None

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
        if last is not None:
            if last.state in {m.value for m in HVACMode}:
                self._attr_hvac_mode = HVACMode(last.state)

            attrs = last.attributes
            # The stored temperatures come back converted to °C, whatever unit
            # the system displays; out-of-range targets are dropped because the
            # restored value is what gets sent to the unit.
            climate_data = await self.async_get_last_climate_data(validate_range=True)
            if (
                climate_data is not None
                and (temp := climate_data.native_target_temperature) is not None
            ):
                self._attr_native_target_temperature = float(round(temp))

            if (fan := attrs.get("fan_mode")) and fan in self._attr_fan_modes:
                self._attr_fan_mode = fan

            if (swing := attrs.get("swing_mode")) and swing in self._attr_swing_modes:
                self._attr_swing_mode = swing

            if (off := attrs.get("control_offset")) is not None:
                self._control_offset = _as_float(off, 0.0)

        # Re-evaluate now that the restored mode/target are in place.
        self._evaluate_demand()

    @property
    def extra_state_attributes(self) -> dict[str, float] | None:
        """Expose the learned setpoint bias while the offset strategy is active."""
        if self._control_strategy == CONTROL_OFFSET:
            return {"control_offset": round(self._control_offset, 1)}
        return None

    @callback
    def _handle_temperature_sensor_change(
        self, event: Event[EventStateChangedData]
    ) -> None:
        """Update current_temperature from the feedback sensor's new state.

        This is also where the closed loop runs. For the stop/setpoint
        strategies a fresh command is sent whenever demand flips; for the
        offset strategy the setpoint bias is nudged and re-sent when the
        rounded setpoint changes.
        """
        self._update_current_temperature(event.data["new_state"])

        if self._control_strategy in (CONTROL_POWER, CONTROL_SETPOINT):
            was_active = self._demand_active
            self._evaluate_demand()
            if self._demand_active != was_active:
                self.hass.async_create_task(self._send_for_demand())
        elif self._control_strategy == CONTROL_OFFSET:
            if self._adjust_offset():
                self.hass.async_create_task(self._send_current_state())

        self.async_write_ha_state()

    def _update_current_temperature(self, state: State | None) -> None:
        """Set current_temperature from a sensor state, ignoring bad readings."""
        if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return
        try:
            self._attr_native_current_temperature = float(state.state)
        except ValueError:
            _LOGGER.warning(
                "Feedback sensor %s has a non-numeric state: %s",
                self._temperature_sensor_entity_id,
                state.state,
            )

    @property
    def hvac_action(self) -> HVACAction | None:
        """Best-effort action, derived by comparing the feedback sensor to the target.

        IR emitters give no real confirmation, so this is a heuristic, not a
        measurement: it assumes the unit is actively heating/cooling whenever
        the feedback sensor hasn't yet reached the target (within a small
        deadband), and idle once it has.
        """
        if self._attr_hvac_mode == HVACMode.OFF:
            return HVACAction.OFF

        # Feedback loop is actively holding the unit off because the target
        # has been reached (only happens in heat/cool modes).
        if not self._demand_active:
            return HVACAction.IDLE

        if (
            self._temperature_sensor_entity_id is None
            or self._attr_native_current_temperature is None
        ):
            return None

        current = self._attr_native_current_temperature
        target = self._attr_native_target_temperature

        if self._attr_hvac_mode == HVACMode.COOL:
            return (
                HVACAction.COOLING
                if current > target + _ACTION_DEADBAND
                else HVACAction.IDLE
            )
        if self._attr_hvac_mode == HVACMode.HEAT:
            return (
                HVACAction.HEATING
                if current < target - _ACTION_DEADBAND
                else HVACAction.IDLE
            )
        if self._attr_hvac_mode == HVACMode.HEAT_COOL:
            if current > target + _ACTION_DEADBAND:
                return HVACAction.COOLING
            if current < target - _ACTION_DEADBAND:
                return HVACAction.HEATING
            return HVACAction.IDLE
        if self._attr_hvac_mode == HVACMode.DRY:
            return HVACAction.DRYING
        if self._attr_hvac_mode == HVACMode.FAN_ONLY:
            return HVACAction.FAN

        return None

    # ------------------------------------------------------------------
    # Setters — each updates local state and sends the full IR command
    # ------------------------------------------------------------------

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new HVAC mode."""
        if hvac_mode != self._attr_hvac_mode:
            # The offset bias is direction-specific; start fresh on a mode change.
            self._control_offset = 0.0
            self._last_offset_adjust = None
        self._attr_hvac_mode = hvac_mode
        await self._apply_state()
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs: float) -> None:
        """Set target temperature."""
        if (temp := kwargs.get(ATTR_TEMPERATURE)) is not None:
            self._attr_native_target_temperature = temp
            if self._attr_hvac_mode != HVACMode.OFF:
                await self._apply_state()
            self.async_write_ha_state()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set fan mode."""
        self._attr_fan_mode = fan_mode
        if self._attr_hvac_mode != HVACMode.OFF:
            await self._apply_state()
        self.async_write_ha_state()

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        """Set swing mode."""
        self._attr_swing_mode = swing_mode
        if self._attr_hvac_mode != HVACMode.OFF:
            await self._apply_state()
        self.async_write_ha_state()

    async def async_turn_on(self) -> None:
        """Turn on (restore last non-off mode or default to HEAT_COOL)."""
        if self._attr_hvac_mode == HVACMode.OFF:
            self._attr_hvac_mode = HVACMode.HEAT_COOL
        await self._apply_state()
        self.async_write_ha_state()

    async def async_turn_off(self) -> None:
        """Turn off."""
        self._attr_hvac_mode = HVACMode.OFF
        await self._apply_state()
        self.async_write_ha_state()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    _LOOP_MODES = (HVACMode.HEAT, HVACMode.COOL, HVACMode.HEAT_COOL)

    @callback
    def _evaluate_demand(self) -> None:
        """Update ``_demand_active`` from the feedback sensor (hysteresis loop).

        Only acts when a control strategy is configured, a feedback sensor is
        available and the unit is in a heat/cool mode; otherwise demand is
        always active and the unit is left to regulate itself.
        """
        if (
            self._control_strategy not in (CONTROL_POWER, CONTROL_SETPOINT)
            or self._temperature_sensor_entity_id is None
            or self._attr_native_current_temperature is None
            or self._attr_hvac_mode not in self._LOOP_MODES
        ):
            self._demand_active = True
            return

        current = self._attr_native_current_temperature
        target = self._attr_native_target_temperature or self._model.min_temp
        band = self._control_deadband

        if self._attr_hvac_mode == HVACMode.HEAT:
            if self._demand_active and current >= target + band:
                self._demand_active = False
            elif not self._demand_active and current <= target - band:
                self._demand_active = True
        elif self._attr_hvac_mode == HVACMode.COOL:
            if self._demand_active and current <= target - band:
                self._demand_active = False
            elif not self._demand_active and current >= target + band:
                self._demand_active = True
        else:  # HEAT_COOL — single setpoint, unit picks the direction
            if self._demand_active and abs(current - target) <= band:
                self._demand_active = False
            elif not self._demand_active and abs(current - target) >= band * 2:
                self._demand_active = True

    @callback
    def _adjust_offset(self) -> bool:
        """Nudge the learned setpoint bias toward the target (offset strategy).

        Runs at most once per configured interval so the room has time to
        respond. Returns True when the rounded setpoint we would send has
        changed and an IR command should be re-sent.
        """
        if (
            self._temperature_sensor_entity_id is None
            or self._attr_native_current_temperature is None
            or self._attr_hvac_mode not in self._LOOP_MODES
        ):
            return False

        before = self._compensated_setpoint()

        current = self._attr_native_current_temperature
        target = self._attr_native_target_temperature or self._model.min_temp
        band = self._control_deadband
        now = _monotonic()

        if (
            self._last_offset_adjust is None
            or now - self._last_offset_adjust >= self._control_interval
        ):
            too_cold = current < target - band
            too_warm = current > target + band
            if self._attr_hvac_mode == HVACMode.COOL:
                # Higher offset → lower setpoint → more cooling.
                step = _OFFSET_STEP if too_warm else -_OFFSET_STEP if too_cold else 0.0
            else:  # HEAT / HEAT_COOL: higher offset → higher setpoint → more heat.
                step = _OFFSET_STEP if too_cold else -_OFFSET_STEP if too_warm else 0.0

            if step:
                self._control_offset = max(
                    -self._control_max_offset,
                    min(self._control_max_offset, self._control_offset + step),
                )
                self._last_offset_adjust = now

        return self._compensated_setpoint() != before

    def _compensated_setpoint(self) -> int:
        """Target temperature with the offset bias applied, clamped to the model."""
        target = self._attr_native_target_temperature or self._model.min_temp
        raw = (
            target - self._control_offset
            if self._attr_hvac_mode == HVACMode.COOL
            else target + self._control_offset
        )
        clamped = max(self._model.min_temp, min(self._model.max_temp, raw))
        return int(round(clamped))

    async def _apply_state(self) -> None:
        """Re-evaluate the feedback loop and send the matching IR command."""
        self._evaluate_demand()
        await self._send_for_demand()

    async def _send_for_demand(self) -> None:
        """Send the active command, or the strategy's suspend command."""
        if self._demand_active:
            await self._send_current_state()
        else:
            await self._send_suspend_command()

    async def _send_suspend_command(self) -> None:
        """Tell the unit to stop, per the configured control strategy."""
        # Power strategy, or HEAT_COOL where there is no "off direction" for a
        # single setpoint: just switch the unit off (HA mode is left unchanged
        # so demand can resume it).
        if (
            self._control_strategy == CONTROL_POWER
            or self._attr_hvac_mode == HVACMode.HEAT_COOL
        ):
            await self._send_current_state(power_override=POWER_OFF)
            return

        # Setpoint strategy: park the setpoint at the extreme that stops output.
        if self._attr_hvac_mode == HVACMode.HEAT:
            await self._send_current_state(temp_override=int(self._model.min_temp))
        else:  # COOL
            await self._send_current_state(temp_override=int(self._model.max_temp))

    async def _send_current_state(
        self,
        *,
        power_override: int | None = None,
        temp_override: int | None = None,
    ) -> None:
        """Build the IR command from current state and send it."""
        power, ir_mode = _HA_HVAC_TO_IR.get(
            self._attr_hvac_mode, (POWER_OFF, MODE_AUTO)
        )
        if power_override is not None:
            power = power_override

        ir_fan = _HA_FAN_TO_IR.get(self._attr_fan_mode or FAN_AUTO, IR_FAN_AUTO)

        swing_v, swing_h = _HA_SWING_TO_IR.get(
            self._attr_swing_mode or SWING_OFF, (VDIR_AUTO, HDIR_AUTO)
        )

        if temp_override is not None:
            temp = temp_override
        elif (
            self._control_strategy == CONTROL_OFFSET
            and self._attr_hvac_mode in self._LOOP_MODES
        ):
            temp = self._compensated_setpoint()
        else:
            temp = int(self._attr_native_target_temperature or self._model.min_temp)

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
