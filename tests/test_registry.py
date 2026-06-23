"""Tests for the IR model registry: every registered model produces a valid command."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from infrared_protocols.commands import Command

from custom_components.heatpump_infrared.ir import MODELS, create_model
from custom_components.heatpump_infrared.ir.base import (
    FAN_AUTO,
    HDIR_AUTO,
    MODE_COOL,
    MODE_HEAT,
    POWER_OFF,
    POWER_ON,
    VDIR_AUTO,
    RawIRCommand,
)


def _all_model_ids():
    return [model_id for _, model_id, _ in MODELS]


@pytest.mark.parametrize("model_id", _all_model_ids())
def test_create_model_returns_instance(model_id):
    model = create_model(model_id)
    assert model is not None
    assert model.model_id == model_id


@pytest.mark.parametrize("model_id", _all_model_ids())
def test_power_on_returns_command(model_id):
    model = create_model(model_id)
    cmd = model.get_command(
        power=POWER_ON,
        mode=MODE_COOL,
        fan=FAN_AUTO,
        temp=24,
        swing_v=VDIR_AUTO,
        swing_h=HDIR_AUTO,
    )
    assert isinstance(cmd, Command)
    timings = cmd.get_raw_timings()
    assert len(timings) > 0


@pytest.mark.parametrize("model_id", _all_model_ids())
def test_power_off_returns_command(model_id):
    model = create_model(model_id)
    cmd = model.get_command(
        power=POWER_OFF,
        mode=MODE_COOL,
        fan=FAN_AUTO,
        temp=24,
    )
    assert isinstance(cmd, Command)
    assert len(cmd.get_raw_timings()) > 0


@pytest.mark.parametrize("model_id", _all_model_ids())
def test_timings_alternate_mark_space(model_id):
    model = create_model(model_id)
    cmd = model.get_command(POWER_ON, MODE_HEAT, FAN_AUTO, 22)
    timings = cmd.get_raw_timings()
    assert timings[0] > 0, f"{model_id}: first timing must be a mark (positive)"
    for i in range(len(timings) - 1):
        assert (timings[i] > 0) != (timings[i + 1] > 0), (
            f"{model_id}: timings must alternate at index {i},{i+1}: "
            f"{timings[i]}, {timings[i+1]}"
        )


@pytest.mark.parametrize("model_id", _all_model_ids())
def test_modulation_is_38khz(model_id):
    model = create_model(model_id)
    cmd = model.get_command(POWER_ON, MODE_COOL, FAN_AUTO, 22)
    assert cmd.modulation == 38000, f"{model_id}: expected 38000 Hz, got {cmd.modulation}"


@pytest.mark.parametrize("model_id", _all_model_ids())
def test_power_on_off_differ(model_id):
    model = create_model(model_id)
    on_cmd = model.get_command(POWER_ON, MODE_COOL, FAN_AUTO, 22)
    off_cmd = model.get_command(POWER_OFF, MODE_COOL, FAN_AUTO, 22)
    assert on_cmd.get_raw_timings() != off_cmd.get_raw_timings(), (
        f"{model_id}: power ON and OFF should produce different timings"
    )


@pytest.mark.parametrize("model_id", _all_model_ids())
def test_temperature_affects_timings(model_id):
    model = create_model(model_id)
    min_t = int(model.min_temp)
    max_t = int(model.max_temp)
    if max_t - min_t < 2:
        pytest.skip("temperature range too small")
    cmd_low = model.get_command(POWER_ON, MODE_COOL, FAN_AUTO, min_t + 1)
    cmd_high = model.get_command(POWER_ON, MODE_COOL, FAN_AUTO, max_t - 1)
    assert cmd_low.get_raw_timings() != cmd_high.get_raw_timings(), (
        f"{model_id}: different temperatures should produce different timings"
    )


def test_models_list_unique_ids():
    ids = _all_model_ids()
    assert len(ids) == len(set(ids)), "MODELS list contains duplicate model_ids"


def test_create_model_unknown_raises():
    with pytest.raises(KeyError):
        create_model("nonexistent_brand_xyz")
