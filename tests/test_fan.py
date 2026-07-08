"""Tests for the Panasonic ceiling-fan IR encoder.

The reference below is the original captured remote: ten AEHA payloads, one per
speed 1-9 plus off. The encoder must regenerate each byte-for-byte.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from infrared_protocols.commands import Command

from custom_components.heatpump_infrared.ir import (
    FAN_MODELS,
    create_fan_model,
)
from custom_components.heatpump_infrared.ir.panasonic_fan import (
    MAX_SPEED,
    MIN_SPEED,
    SPEED_OFF,
    PanasonicCeilingFanIR,
    build_payload,
)
from custom_components.heatpump_infrared.ir.panasonic_fan import (
    _AEHA_BIT_MARK,
    _AEHA_ONE_SPACE,
    _AEHA_ZERO_SPACE,
)

# Original captured payloads (address 0x4004), keyed by speed. 0 == off.
_REFERENCE = {
    1: [0x0B, 0x21, 0x8C, 0x40, 0x84, 0x4C, 0x02, 0xB2, 0x0E, 0x81, 0xC1, 0x1A, 0xCA],
    2: [0x0B, 0x21, 0x8C, 0x40, 0x44, 0x4C, 0x02, 0xB2, 0x0E, 0x81, 0xC1, 0x1A, 0x0A],
    3: [0x0B, 0x21, 0x8C, 0x40, 0xC4, 0x4C, 0x02, 0xB2, 0x0E, 0x81, 0xC1, 0x1A, 0x8A],
    4: [0x0B, 0x21, 0x8C, 0x40, 0x24, 0x4C, 0x02, 0xB2, 0x0E, 0x81, 0xC1, 0x1A, 0x6A],
    5: [0x0B, 0x21, 0x8C, 0x40, 0xA4, 0x4C, 0x02, 0xB2, 0x0E, 0x81, 0xC1, 0x1A, 0xEA],
    6: [0x0B, 0x21, 0x8C, 0x40, 0x64, 0x4C, 0x02, 0xB2, 0x0E, 0x81, 0xC1, 0x1A, 0x2A],
    7: [0x0B, 0x21, 0x8C, 0x40, 0xE4, 0x4C, 0x02, 0xB2, 0x0E, 0x81, 0xC1, 0x1A, 0xAA],
    8: [0x0B, 0x21, 0x8C, 0x40, 0x14, 0x4C, 0x02, 0xB2, 0x0E, 0x81, 0xC1, 0x1A, 0x5A],
    9: [0x0B, 0x21, 0x8C, 0x40, 0x94, 0x4C, 0x02, 0xB2, 0x0E, 0x81, 0xC1, 0x1A, 0xDA],
    0: [0x0B, 0x21, 0x8C, 0x80, 0x84, 0xCC, 0x02, 0xB2, 0x0E, 0x81, 0xC1, 0x1A, 0x8A],
}

_ADDRESS = 0x4004


def _decode_bytes(timings):
    """Decode AEHA raw timings (after the 2-timing header) into byte values."""
    threshold = (_AEHA_ONE_SPACE + _AEHA_ZERO_SPACE) // 2
    i = 2  # skip header mark/space
    out = []
    # Every full byte is 16 timings; a trailing stop mark may remain.
    while i + 16 <= len(timings):
        byte = 0
        for bit in range(8):
            space = timings[i + 1]
            if abs(space) > threshold:
                byte |= 1 << bit
            i += 2
        out.append(byte)
    return out


def _decode_frame(timings):
    """Return (address, payload_bytes) decoded from a fan command's timings."""
    decoded = _decode_bytes(timings)
    address = decoded[0] | (decoded[1] << 8)
    payload = decoded[2:]
    return address, payload


class TestFanEncoder:
    def setup_method(self):
        self.model = PanasonicCeilingFanIR()

    @pytest.mark.parametrize("speed", list(range(0, 10)))
    def test_payload_matches_reference(self, speed):
        assert build_payload(speed) == _REFERENCE[speed]

    @pytest.mark.parametrize("speed", list(range(0, 10)))
    def test_command_reproduces_reference(self, speed):
        cmd = self.model.get_command(speed)
        assert isinstance(cmd, Command)
        address, payload = _decode_frame(cmd.get_raw_timings())
        assert address == _ADDRESS
        assert payload == _REFERENCE[speed]

    def test_checksum_is_xor_of_preceding_bytes(self):
        for speed in range(0, 10):
            payload = build_payload(speed)
            chk = 0
            for byte in payload[:-1]:
                chk ^= byte
            assert payload[-1] == chk

    def test_modulation_is_38khz(self):
        assert self.model.get_command(MIN_SPEED).modulation == 38000

    def test_timings_start_with_header_mark(self):
        timings = self.model.get_command(MIN_SPEED).get_raw_timings()
        assert timings[0] == 3400  # header mark
        assert timings[1] == -1700  # header space

    def test_timings_alternate_mark_space(self):
        timings = self.model.get_command(5).get_raw_timings()
        assert timings[0] > 0
        for i in range(len(timings) - 1):
            assert (timings[i] > 0) != (timings[i + 1] > 0)

    def test_off_and_running_differ(self):
        off = self.model.get_command(SPEED_OFF).get_raw_timings()
        on = self.model.get_command(MIN_SPEED).get_raw_timings()
        assert off != on

    def test_each_speed_is_distinct(self):
        seen = {
            tuple(self.model.get_command(s).get_raw_timings())
            for s in range(0, 10)
        }
        assert len(seen) == 10

    @pytest.mark.parametrize("speed", [-1, 10, 99])
    def test_invalid_speed_raises(self, speed):
        with pytest.raises(ValueError):
            self.model.get_command(speed)


class TestFanRegistry:
    def test_fan_models_listed(self):
        ids = [model_id for _, model_id, _ in FAN_MODELS]
        assert "panasonic_ceiling_fan" in ids

    def test_create_fan_model(self):
        model = create_fan_model("panasonic_ceiling_fan")
        assert isinstance(model, PanasonicCeilingFanIR)
        assert model.model_id == "panasonic_ceiling_fan"
        assert model.min_speed == MIN_SPEED
        assert model.max_speed == MAX_SPEED

    def test_create_fan_model_unknown_raises(self):
        with pytest.raises(KeyError):
            create_fan_model("nonexistent_fan_xyz")
