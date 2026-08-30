"""Tests for the climate platform's external temperature-sensor feedback.

IR emitters are fire-and-forget, so the climate entity can optionally track
an external temperature sensor entity and surface its reading as
current_temperature — this is the only feedback a user gets that the unit is
actually responding to commands.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from custom_components.heatpump_infrared import climate as climate_mod
from custom_components.heatpump_infrared.climate import HeatpumpIRClimate
from custom_components.heatpump_infrared.const import (
    CONF_CONTROL_DEADBAND,
    CONF_CONTROL_INTERVAL,
    CONF_CONTROL_MAX_OFFSET,
    CONF_CONTROL_STRATEGY,
    CONF_TEMPERATURE_SENSOR_ID,
    CONTROL_OFFSET,
    CONTROL_POWER,
    CONTROL_SETPOINT,
)

HVACMode = climate_mod.HVACMode


class FakeModel:
    display_name = "Test Brand X"
    model_id = "test_model"
    min_temp = 16
    max_temp = 30
    fan_speeds = 3

    def __init__(self):
        self.commands = []

    def get_command(self, **kwargs):
        self.commands.append(kwargs)
        return kwargs


class FakeConfigEntry:
    def __init__(self, options=None):
        self.entry_id = "test-entry"
        self.data = {}
        self.options = options or {}


class FakeState:
    def __init__(self, state):
        self.state = state


class FakeStates:
    def __init__(self, states):
        self._states = states

    def get(self, entity_id):
        return self._states.get(entity_id)


class FakeHass:
    def __init__(self, states):
        self.states = FakeStates(states)

    def async_create_task(self, coro):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


def _run(coro):
    return asyncio.run(coro)


def _make_climate(
    sensor_entity_id=None,
    initial_sensor_state=None,
    strategy=None,
    deadband=None,
    max_offset=None,
    interval=None,
):
    options = {}
    if sensor_entity_id:
        options[CONF_TEMPERATURE_SENSOR_ID] = sensor_entity_id
    if strategy is not None:
        options[CONF_CONTROL_STRATEGY] = strategy
    if deadband is not None:
        options[CONF_CONTROL_DEADBAND] = deadband
    if max_offset is not None:
        options[CONF_CONTROL_MAX_OFFSET] = max_offset
    if interval is not None:
        options[CONF_CONTROL_INTERVAL] = interval
    entry = FakeConfigEntry(options=options)
    entity = HeatpumpIRClimate(entry, FakeModel(), "infrared.test_emitter")

    states = {}
    if sensor_entity_id and initial_sensor_state is not None:
        states[sensor_entity_id] = FakeState(initial_sensor_state)
    entity.hass = FakeHass(states)
    return entity


class TestTemperatureSensorFeedback:
    def test_no_sensor_configured_leaves_current_temperature_none(self):
        entity = _make_climate()
        _run(entity.async_added_to_hass())
        assert entity._attr_current_temperature is None

    def test_initial_reading_is_applied_on_add(self):
        entity = _make_climate("sensor.living_room", initial_sensor_state="21.5")
        _run(entity.async_added_to_hass())
        assert entity._attr_current_temperature == 21.5

    def test_unavailable_initial_state_is_ignored(self):
        entity = _make_climate(
            "sensor.living_room", initial_sensor_state="unavailable"
        )
        _run(entity.async_added_to_hass())
        assert entity._attr_current_temperature is None

    def test_unknown_initial_state_is_ignored(self):
        entity = _make_climate("sensor.living_room", initial_sensor_state="unknown")
        _run(entity.async_added_to_hass())
        assert entity._attr_current_temperature is None

    def test_missing_sensor_entity_is_ignored(self):
        entity = _make_climate("sensor.does_not_exist")
        _run(entity.async_added_to_hass())
        assert entity._attr_current_temperature is None

    def test_non_numeric_reading_is_ignored(self):
        entity = _make_climate(
            "sensor.living_room", initial_sensor_state="not-a-number"
        )
        _run(entity.async_added_to_hass())
        assert entity._attr_current_temperature is None

    def test_subscribes_to_configured_sensor(self, monkeypatch):
        captured = {}

        def fake_track(hass, entity_ids, callback):
            captured["entity_ids"] = entity_ids
            return lambda: None

        monkeypatch.setattr(
            climate_mod, "async_track_state_change_event", fake_track
        )

        entity = _make_climate("sensor.living_room", initial_sensor_state="20.0")
        _run(entity.async_added_to_hass())

        assert captured["entity_ids"] == ["sensor.living_room"]

    def test_does_not_subscribe_when_no_sensor_configured(self, monkeypatch):
        called = False

        def fake_track(hass, entity_ids, callback):
            nonlocal called
            called = True
            return lambda: None

        monkeypatch.setattr(
            climate_mod, "async_track_state_change_event", fake_track
        )

        entity = _make_climate()
        _run(entity.async_added_to_hass())

        assert called is False

    def test_state_change_event_updates_current_temperature(self, monkeypatch):
        captured = {}

        def fake_track(hass, entity_ids, callback):
            captured["callback"] = callback
            return lambda: None

        monkeypatch.setattr(
            climate_mod, "async_track_state_change_event", fake_track
        )

        entity = _make_climate("sensor.living_room", initial_sensor_state="20.0")
        _run(entity.async_added_to_hass())
        assert entity._attr_current_temperature == 20.0

        event = climate_mod.Event({"new_state": FakeState("23.4")})
        captured["callback"](event)

        assert entity._attr_current_temperature == 23.4

    def test_state_change_to_unavailable_keeps_last_good_reading(self, monkeypatch):
        captured = {}

        def fake_track(hass, entity_ids, callback):
            captured["callback"] = callback
            return lambda: None

        monkeypatch.setattr(
            climate_mod, "async_track_state_change_event", fake_track
        )

        entity = _make_climate("sensor.living_room", initial_sensor_state="19.0")
        _run(entity.async_added_to_hass())
        assert entity._attr_current_temperature == 19.0

        event = climate_mod.Event({"new_state": FakeState("unavailable")})
        captured["callback"](event)

        assert entity._attr_current_temperature == 19.0


from custom_components.heatpump_infrared.ir.base import POWER_OFF, POWER_ON


class TestFeedbackControlStrategies:
    """The feedback sensor can drive a hysteresis loop that stops/resumes the unit."""

    def _setup(self, monkeypatch, strategy, mode, target, start_temp, deadband=0.5):
        captured = {}

        def fake_track(hass, entity_ids, cb):
            captured["cb"] = cb
            return lambda: None

        monkeypatch.setattr(
            climate_mod, "async_track_state_change_event", fake_track
        )
        entity = _make_climate(
            "sensor.room",
            initial_sensor_state=str(start_temp),
            strategy=strategy,
            deadband=deadband,
        )
        _run(entity.async_added_to_hass())
        entity._attr_hvac_mode = mode
        entity._attr_target_temperature = target
        entity._model.commands.clear()
        return entity, captured

    @staticmethod
    def _emit(captured, temp):
        captured["cb"](climate_mod.Event({"new_state": FakeState(str(temp))}))

    def test_display_only_never_sends_on_sensor_change(self, monkeypatch):
        entity, captured = self._setup(
            monkeypatch, "none", HVACMode.HEAT, 20, 20
        )
        self._emit(captured, 25)
        assert entity._model.commands == []
        assert entity._demand_active is True

    def test_power_strategy_stops_and_resumes_when_heating(self, monkeypatch):
        entity, captured = self._setup(
            monkeypatch, CONTROL_POWER, HVACMode.HEAT, 20, 20
        )

        self._emit(captured, 20.6)  # past target + deadband → stop
        assert entity._demand_active is False
        assert entity._model.commands[-1]["power"] == POWER_OFF

        self._emit(captured, 20.4)  # still inside hysteresis band → no change
        assert entity._demand_active is False

        self._emit(captured, 19.4)  # below target - deadband → resume
        assert entity._demand_active is True
        assert entity._model.commands[-1]["power"] == POWER_ON

    def test_power_strategy_stops_and_resumes_when_cooling(self, monkeypatch):
        entity, captured = self._setup(
            monkeypatch, CONTROL_POWER, HVACMode.COOL, 24, 24
        )
        self._emit(captured, 23.4)
        assert entity._model.commands[-1]["power"] == POWER_OFF
        self._emit(captured, 24.6)
        assert entity._model.commands[-1]["power"] == POWER_ON

    def test_setpoint_strategy_parks_setpoint_at_min_when_heating(self, monkeypatch):
        entity, captured = self._setup(
            monkeypatch, CONTROL_SETPOINT, HVACMode.HEAT, 20, 20
        )
        self._emit(captured, 20.6)
        last = entity._model.commands[-1]
        assert last["power"] == POWER_ON
        assert last["temp"] == FakeModel.min_temp

        self._emit(captured, 19.4)
        assert entity._model.commands[-1]["temp"] == 20

    def test_setpoint_strategy_parks_setpoint_at_max_when_cooling(self, monkeypatch):
        entity, captured = self._setup(
            monkeypatch, CONTROL_SETPOINT, HVACMode.COOL, 24, 24
        )
        self._emit(captured, 23.4)
        assert entity._model.commands[-1]["temp"] == FakeModel.max_temp

    def test_no_override_without_feedback_sensor(self, monkeypatch):
        entity = _make_climate(strategy=CONTROL_POWER)
        _run(entity.async_added_to_hass())
        entity._attr_hvac_mode = HVACMode.HEAT
        entity._attr_target_temperature = 20
        entity._attr_current_temperature = 25
        entity._evaluate_demand()
        assert entity._demand_active is True

    def test_hvac_action_idle_while_loop_holds_unit_off(self, monkeypatch):
        entity, captured = self._setup(
            monkeypatch, CONTROL_POWER, HVACMode.HEAT, 20, 20
        )
        self._emit(captured, 21)
        assert entity._demand_active is False
        assert entity.hvac_action == climate_mod.HVACAction.IDLE


class TestOffsetCompensation:
    """The offset strategy biases the setpoint so the room tracks the target."""

    def _setup(self, monkeypatch, mode, target, start_temp, deadband=0.5,
               max_offset=3, interval=10):
        self.clock = [0.0]
        monkeypatch.setattr(climate_mod, "_monotonic", lambda: self.clock[0])
        captured = {}

        def fake_track(hass, entity_ids, cb):
            captured["cb"] = cb
            return lambda: None

        monkeypatch.setattr(
            climate_mod, "async_track_state_change_event", fake_track
        )
        entity = _make_climate(
            "sensor.room",
            initial_sensor_state=str(start_temp),
            strategy=CONTROL_OFFSET,
            deadband=deadband,
            max_offset=max_offset,
            interval=interval,
        )
        _run(entity.async_added_to_hass())
        entity._attr_hvac_mode = mode
        entity._attr_target_temperature = target
        entity._model.commands.clear()
        return entity, captured

    def _emit(self, captured, temp):
        captured["cb"](climate_mod.Event({"new_state": FakeState(str(temp))}))

    def _tick(self, minutes):
        self.clock[0] += minutes * 60

    def test_cooling_biases_setpoint_down_when_room_too_warm(self, monkeypatch):
        entity, captured = self._setup(monkeypatch, HVACMode.COOL, 25, 25)

        self._emit(captured, 27)  # too warm, first adjust is always allowed
        assert entity._control_offset == 1.0
        assert entity._model.commands[-1]["temp"] == 24

        self._emit(captured, 27)  # within interval → no further change
        assert entity._control_offset == 1.0

        self._tick(10)
        self._emit(captured, 27)  # still too warm → bias further
        assert entity._control_offset == 2.0
        assert entity._model.commands[-1]["temp"] == 23

    def test_bias_backs_off_when_room_overshoots(self, monkeypatch):
        entity, captured = self._setup(monkeypatch, HVACMode.COOL, 25, 25)
        self._emit(captured, 27)
        assert entity._control_offset == 1.0

        self._tick(10)
        self._emit(captured, 23)  # now below target - deadband → ease off
        assert entity._control_offset == 0.0
        assert entity._model.commands[-1]["temp"] == 25

    def test_offset_is_capped_at_max(self, monkeypatch):
        entity, captured = self._setup(
            monkeypatch, HVACMode.COOL, 25, 25, max_offset=2
        )
        for _ in range(5):
            self._emit(captured, 30)
            self._tick(10)
        assert entity._control_offset == 2.0
        assert entity._model.commands[-1]["temp"] == 23

    def test_heating_biases_setpoint_up_when_room_too_cold(self, monkeypatch):
        entity, captured = self._setup(monkeypatch, HVACMode.HEAT, 20, 20)
        self._emit(captured, 18)
        assert entity._control_offset == 1.0
        assert entity._model.commands[-1]["temp"] == 21

    def test_no_adjustment_inside_deadband(self, monkeypatch):
        entity, captured = self._setup(monkeypatch, HVACMode.COOL, 25, 25)
        self._emit(captured, 25.2)
        assert entity._control_offset == 0.0
        assert entity._model.commands == []

    def test_mode_change_resets_offset(self, monkeypatch):
        entity, captured = self._setup(monkeypatch, HVACMode.COOL, 25, 25)
        self._emit(captured, 28)
        assert entity._control_offset == 1.0
        _run(entity.async_set_hvac_mode(HVACMode.HEAT))
        assert entity._control_offset == 0.0

    def test_offset_exposed_and_restored(self, monkeypatch):
        entity, captured = self._setup(monkeypatch, HVACMode.COOL, 25, 25)
        self._emit(captured, 28)
        assert entity.extra_state_attributes == {"control_offset": 1.0}

        restored = _make_climate(
            "sensor.room", initial_sensor_state="25", strategy=CONTROL_OFFSET
        )

        async def fake_last_state():
            return climate_mod.State(
                "cool", {"temperature": 25, "control_offset": 2.0}
            )

        restored.async_get_last_state = fake_last_state
        _run(restored.async_added_to_hass())
        assert restored._control_offset == 2.0
