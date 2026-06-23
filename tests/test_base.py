"""Tests for IRSenderCapture, RawIRCommand, and HeatpumpIRBase."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from custom_components.heatpump_infrared.ir.base import (
    IRSenderCapture,
    RawIRCommand,
)


class TestIRSenderCapture:
    def test_set_frequency_converts_to_hz(self):
        ir = IRSenderCapture()
        ir.setFrequency(38)
        assert ir._modulation == 38000

    def test_mark_appends_positive(self):
        ir = IRSenderCapture()
        ir.mark(500)
        assert ir._timings == [500]

    def test_space_appends_negative(self):
        ir = IRSenderCapture()
        ir.space(1000)
        assert ir._timings == [-1000]

    def test_zero_space_is_dropped(self):
        ir = IRSenderCapture()
        ir.space(0)
        assert ir._timings == []

    def test_timings_alternate_after_sendIRbyte(self):
        ir = IRSenderCapture()
        ir.sendIRbyte(0xAA, bit_mark=400, zero_space=500, one_space=1500)
        timings = ir._timings
        # should always start with mark (positive) and alternate
        for i, t in enumerate(timings):
            if i % 2 == 0:
                assert t > 0, f"expected mark at index {i}, got {t}"
            else:
                assert t < 0, f"expected space at index {i}, got {t}"

    def test_sendIRbyte_lsb_first(self):
        ir = IRSenderCapture()
        # 0x01 = 0b00000001 → first bit (LSB) is 1, rest are 0
        ir.sendIRbyte(0x01, bit_mark=400, zero_space=500, one_space=1500)
        timings = ir._timings
        # first pair: mark=400, space=-1500 (bit=1, one_space)
        assert timings[0] == 400
        assert timings[1] == -1500
        # second pair: mark=400, space=-500 (bit=0, zero_space)
        assert timings[2] == 400
        assert timings[3] == -500

    def test_sendIRbyte_custom_bit_count(self):
        ir = IRSenderCapture()
        ir.sendIRbyte(0x01, bit_mark=400, zero_space=500, one_space=1500, bit_count=3)
        # 3 bits → 6 timings
        assert len(ir._timings) == 6

    def test_bit_reverse_known_values(self):
        assert IRSenderCapture.bit_reverse(0x00) == 0x00
        assert IRSenderCapture.bit_reverse(0xFF) == 0xFF
        assert IRSenderCapture.bit_reverse(0x01) == 0x80
        assert IRSenderCapture.bit_reverse(0x80) == 0x01
        assert IRSenderCapture.bit_reverse(0x0F) == 0xF0
        assert IRSenderCapture.bit_reverse(0xF0) == 0x0F
        assert IRSenderCapture.bit_reverse(0xA5) == 0xA5  # palindrome

    def test_bit_reverse_roundtrip(self):
        for v in range(256):
            assert IRSenderCapture.bit_reverse(IRSenderCapture.bit_reverse(v)) == v


class TestRawIRCommand:
    def test_get_raw_timings_returns_copy(self):
        cmd = RawIRCommand([100, -200, 300], modulation=38000)
        t = cmd.get_raw_timings()
        assert t == [100, -200, 300]

    def test_modulation_stored(self):
        cmd = RawIRCommand([], modulation=56000)
        assert cmd.modulation == 56000

    def test_from_sender(self):
        ir = IRSenderCapture()
        ir.setFrequency(38)
        ir.mark(9000)
        ir.space(4500)
        ir.mark(500)
        cmd = RawIRCommand.from_sender(ir)
        assert cmd.modulation == 38000
        assert cmd.get_raw_timings() == [9000, -4500, 500]

    def test_from_sender_isolates_timings(self):
        ir = IRSenderCapture()
        ir.mark(100)
        cmd = RawIRCommand.from_sender(ir)
        ir.mark(200)  # mutate after capture
        assert cmd.get_raw_timings() == [100]
