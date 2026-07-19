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
from custom_components.heatpump_infrared.const import CONF_TEMPERATURE_SENSOR_ID


class FakeModel:
    display_name = "Test Brand X"
    model_id = "test_model"
    min_temp = 16
    max_temp = 30
    fan_speeds = 3


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


def _run(coro):
    return asyncio.run(coro)


def _make_climate(sensor_entity_id=None, initial_sensor_state=None):
    options = {CONF_TEMPERATURE_SENSOR_ID: sensor_entity_id} if sensor_entity_id else {}
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
