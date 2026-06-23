"""Protocol-specific tests verifying correct byte encoding for key brands."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from custom_components.heatpump_infrared.ir.base import (
    FAN_1, FAN_2, FAN_3, FAN_AUTO,
    HDIR_AUTO, HDIR_SWING,
    MODE_AUTO, MODE_COOL, MODE_DRY, MODE_FAN, MODE_HEAT,
    POWER_OFF, POWER_ON,
    VDIR_AUTO, VDIR_SWING,
    IRSenderCapture,
    RawIRCommand,
)


def decode_bytes(timings, hdr_mark, hdr_space, bit_mark, zero_space, one_space):
    """Decode raw timings back into bytes for protocol verification."""
    # skip header
    i = 2
    bytes_out = []
    while i + 1 < len(timings):
        byte = 0
        for bit in range(8):
            if i + 1 >= len(timings):
                break
            mark = timings[i]
            space = timings[i + 1]
            if abs(space) > (one_space + zero_space) // 2:
                byte |= (1 << bit)
            i += 2
        bytes_out.append(byte)
        # stop at end mark (no following space, or MSG_SPACE gap)
        if i < len(timings) and abs(timings[i]) > 5000:
            break
    return bytes_out


class TestMideaProtocol:
    """Midea uses 3 byte-pairs (byte + ~byte), sent twice with MSG_SPACE."""

    def setup_method(self):
        from custom_components.heatpump_infrared.ir.midea import MideaHeatpumpIR
        self.model = MideaHeatpumpIR()

    def test_power_off_special_frame(self):
        cmd = self.model.get_command(POWER_OFF, MODE_COOL, FAN_AUTO, 22)
        timings = cmd.get_raw_timings()
        # OFF uses fixed message [0x4D, 0xDE, 0x07]
        # HDR mark = 4420, HDR space = 4300
        assert timings[0] == 4420
        assert timings[1] == -4300

    def test_byte_inversion_pattern(self):
        """Each byte is followed by its bitwise inverse."""
        from custom_components.heatpump_infrared.ir.midea import (
            _HDR_MARK, _HDR_SPACE, _BIT_MARK, _ZERO_SPACE, _ONE_SPACE,
        )
        cmd = self.model.get_command(POWER_ON, MODE_COOL, FAN_AUTO, 22)
        timings = cmd.get_raw_timings()
        # skip header (2 timings), then 6 bytes × 16 timings each
        i = 2
        for _ in range(3):
            byte_val = 0
            inv_val = 0
            for bit in range(8):
                space = timings[i + 1]
                if abs(space) > (_ONE_SPACE + _ZERO_SPACE) // 2:
                    byte_val |= (1 << bit)
                i += 2
            for bit in range(8):
                space = timings[i + 1]
                if abs(space) > (_ONE_SPACE + _ZERO_SPACE) // 2:
                    inv_val |= (1 << bit)
                i += 2
            assert (byte_val ^ inv_val) == 0xFF, (
                f"byte {byte_val:#04x} and inverse {inv_val:#04x} don't complement"
            )


class TestHyundaiProtocol:
    """Hyundai has 4 bytes + 3-bit trailer '010' (35-bit protocol)."""

    def setup_method(self):
        from custom_components.heatpump_infrared.ir.hyundai import HyundaiHeatpumpIR
        self.model = HyundaiHeatpumpIR()

    def test_header_timing(self):
        cmd = self.model.get_command(POWER_ON, MODE_COOL, FAN_AUTO, 22)
        timings = cmd.get_raw_timings()
        assert timings[0] == 8840   # HDR_MARK
        assert timings[1] == -4440  # HDR_SPACE

    def test_total_bit_count(self):
        """35 bits = 4×8 + 3, so timings = 2 (hdr) + 35×2 (bits) + 1 (end mark) = 73."""
        cmd = self.model.get_command(POWER_ON, MODE_COOL, FAN_AUTO, 22)
        timings = cmd.get_raw_timings()
        assert len(timings) == 73

    def test_temperature_encoding(self):
        """Temperature in buf[1] = temp - 16."""
        from custom_components.heatpump_infrared.ir.hyundai import (
            _BIT_MARK, _ZERO_SPACE, _ONE_SPACE,
        )
        cmd = self.model.get_command(POWER_ON, MODE_COOL, FAN_AUTO, 24)
        timings = cmd.get_raw_timings()
        # byte 1 starts at timing index 2 + 16 = 18
        byte1 = 0
        i = 2 + 16  # skip header + first byte (8 bits × 2 timings)
        for bit in range(8):
            space = timings[i + 1]
            if abs(space) > (_ONE_SPACE + _ZERO_SPACE) // 2:
                byte1 |= (1 << bit)
            i += 2
        assert byte1 == 24 - 16  # = 8


class TestCarrierProtocol:
    def setup_method(self):
        from custom_components.heatpump_infrared.ir.carrier import CarrierNQVHeatpumpIR
        self.model = CarrierNQVHeatpumpIR()

    def test_message_sent_twice(self):
        """NQV protocol sends the same 9-byte frame twice with MSG_SPACE between."""
        cmd = self.model.get_command(POWER_ON, MODE_COOL, FAN_AUTO, 22)
        timings = cmd.get_raw_timings()
        # find the MSG_SPACE gap (negative value > 7000)
        msg_space_indices = [
            i for i, t in enumerate(timings) if t < -7000
        ]
        assert len(msg_space_indices) == 1, "expected exactly one MSG_SPACE gap"

    def test_nqv_header(self):
        cmd = self.model.get_command(POWER_ON, MODE_COOL, FAN_AUTO, 22)
        timings = cmd.get_raw_timings()
        assert timings[0] == 4320
        assert timings[1] == -4350


class TestToshibaProtocol:
    def setup_method(self):
        from custom_components.heatpump_infrared.ir.toshiba import ToshibaHeatpumpIR
        self.model = ToshibaHeatpumpIR()

    def test_header_timing(self):
        cmd = self.model.get_command(POWER_ON, MODE_HEAT, FAN_AUTO, 22)
        timings = cmd.get_raw_timings()
        assert timings[0] == 4400
        assert timings[1] == -4400

    def test_9_byte_frame(self):
        """Toshiba sends 9 bytes: 72 bits = 144 mark/space pairs + header(2) + end(1) = 147."""
        cmd = self.model.get_command(POWER_ON, MODE_HEAT, FAN_AUTO, 22)
        timings = cmd.get_raw_timings()
        assert len(timings) == 147


class TestGreeProtocol:
    def setup_method(self):
        from custom_components.heatpump_infrared.ir.gree import GreeGenericHeatpumpIR
        self.model = GreeGenericHeatpumpIR()

    def test_header_timing(self):
        cmd = self.model.get_command(POWER_ON, MODE_COOL, FAN_AUTO, 22)
        timings = cmd.get_raw_timings()
        assert timings[0] == 9000
        assert timings[1] == -4000

    def test_msg_space_present(self):
        """Gree has a MSG_SPACE of 19000µs between the two payload halves."""
        cmd = self.model.get_command(POWER_ON, MODE_COOL, FAN_AUTO, 22)
        timings = cmd.get_raw_timings()
        msg_spaces = [t for t in timings if t < -15000]
        assert len(msg_spaces) == 1
        assert msg_spaces[0] == -19000


class TestDaikinARC417Protocol:
    def setup_method(self):
        from custom_components.heatpump_infrared.ir.daikin_arc417 import DaikinARC417HeatpumpIR
        self.model = DaikinARC417HeatpumpIR()

    def test_two_frame_structure(self):
        """ARC417 sends 7 bytes, MSG_SPACE, header, then 13 bytes."""
        cmd = self.model.get_command(POWER_ON, MODE_COOL, FAN_AUTO, 22)
        timings = cmd.get_raw_timings()
        # MSG_SPACE = 30000µs
        msg_spaces = [t for t in timings if t < -25000]
        assert len(msg_spaces) == 1

    def test_header_timing(self):
        cmd = self.model.get_command(POWER_ON, MODE_COOL, FAN_AUTO, 22)
        timings = cmd.get_raw_timings()
        assert timings[0] == 5050
        assert timings[1] == -2100


class TestHitachiProtocol:
    def setup_method(self):
        from custom_components.heatpump_infrared.ir.hitachi import HitachiHeatpumpIR
        self.model = HitachiHeatpumpIR()

    def test_28_byte_frame(self):
        """Hitachi sends 28 bytes: 224 bits = 448 timings + header(2) + end(1) = 451."""
        cmd = self.model.get_command(POWER_ON, MODE_COOL, FAN_AUTO, 22)
        timings = cmd.get_raw_timings()
        assert len(timings) == 451

    def test_header_timing(self):
        cmd = self.model.get_command(POWER_ON, MODE_COOL, FAN_AUTO, 22)
        timings = cmd.get_raw_timings()
        assert timings[0] == 3436
        assert timings[1] == -1640


class TestElectroluxProtocol:
    def setup_method(self):
        from custom_components.heatpump_infrared.ir.electrolux import ElectroluxYALHeatpumpIR
        self.model = ElectroluxYALHeatpumpIR()

    def test_header_timing(self):
        cmd = self.model.get_command(POWER_ON, MODE_COOL, FAN_AUTO, 22)
        timings = cmd.get_raw_timings()
        assert timings[0] == 9000
        assert timings[1] == -4000

    def test_msg_space_present(self):
        cmd = self.model.get_command(POWER_ON, MODE_COOL, FAN_AUTO, 22)
        timings = cmd.get_raw_timings()
        msg_spaces = [t for t in timings if t < -15000]
        assert len(msg_spaces) == 1
        assert msg_spaces[0] == -19000


class TestNibeProtocol:
    def setup_method(self):
        from custom_components.heatpump_infrared.ir.nibe import NibeHeatpumpIR
        self.model = NibeHeatpumpIR()

    def test_header_timing(self):
        cmd = self.model.get_command(POWER_ON, MODE_HEAT, FAN_AUTO, 22)
        timings = cmd.get_raw_timings()
        assert timings[0] == 6382
        assert timings[1] == -3144

    def test_power_off_differs(self):
        on_cmd = self.model.get_command(POWER_ON, MODE_HEAT, FAN_AUTO, 22)
        off_cmd = self.model.get_command(POWER_OFF, MODE_HEAT, FAN_AUTO, 22)
        assert on_cmd.get_raw_timings() != off_cmd.get_raw_timings()


class TestMSCProtocol:
    def setup_method(self):
        from custom_components.heatpump_infrared.ir.mitsubishi_msc import MitsubishiMSCHeatpumpIR
        self.model = MitsubishiMSCHeatpumpIR()

    def test_14_byte_frame(self):
        """MSC sends 14 bytes: 112 bits = 224 timings + header(2) + end(1) = 227."""
        cmd = self.model.get_command(POWER_ON, MODE_COOL, FAN_AUTO, 22)
        timings = cmd.get_raw_timings()
        assert len(timings) == 227

    def test_checksum_is_sum_of_all_bytes(self):
        """The last byte is the sum of all preceding bytes & 0xFF."""
        from custom_components.heatpump_infrared.ir.mitsubishi_msc import (
            _MSC_BIT_MARK, _MSC_ZERO_SPACE, _MSC_ONE_SPACE,
        )
        cmd = self.model.get_command(POWER_ON, MODE_COOL, FAN_1, 22)
        timings = cmd.get_raw_timings()
        # decode all 14 bytes
        decoded = []
        i = 2  # skip header
        for _ in range(14):
            byte = 0
            for bit in range(8):
                space = timings[i + 1]
                if abs(space) > (_MSC_ONE_SPACE + _MSC_ZERO_SPACE) // 2:
                    byte |= (1 << bit)
                i += 2
            decoded.append(byte)
        assert decoded[13] == sum(decoded[:13]) & 0xFF


class TestPhilcoProtocol:
    def setup_method(self):
        from custom_components.heatpump_infrared.ir.philco import PhilcoPHS32HeatpumpIR
        self.model = PhilcoPHS32HeatpumpIR()

    def test_three_chunk_structure(self):
        """Philco sends 6 bytes + MSG_SPACE + 8 bytes + MSG_SPACE + 7 bytes."""
        cmd = self.model.get_command(POWER_ON, MODE_COOL, FAN_AUTO, 22)
        timings = cmd.get_raw_timings()
        msg_spaces = [t for t in timings if t < -7000]
        assert len(msg_spaces) == 2

    def test_header_timing(self):
        cmd = self.model.get_command(POWER_ON, MODE_COOL, FAN_AUTO, 22)
        timings = cmd.get_raw_timings()
        assert timings[0] == 9000
        assert timings[1] == -4500


class TestBGHProtocol:
    def setup_method(self):
        from custom_components.heatpump_infrared.ir.bgh import BGHHeatpumpIR
        self.model = BGHHeatpumpIR()

    def test_two_chunk_structure(self):
        """BGH sends 7 bytes + MSG_SPACE + 7 bytes."""
        cmd = self.model.get_command(POWER_ON, MODE_COOL, FAN_AUTO, 22)
        timings = cmd.get_raw_timings()
        msg_spaces = [t for t in timings if t < -7000]
        assert len(msg_spaces) == 1

    def test_header_timing(self):
        cmd = self.model.get_command(POWER_ON, MODE_COOL, FAN_AUTO, 22)
        timings = cmd.get_raw_timings()
        assert timings[0] == 9060
        assert timings[1] == -4550


class TestBalluProtocol:
    def setup_method(self):
        from custom_components.heatpump_infrared.ir.ballu import BalluHeatpumpIR
        self.model = BalluHeatpumpIR()

    def test_6_byte_frame(self):
        """Ballu sends 6 bytes: 48 bits = 96 timings + header(2) + end(1) = 99."""
        cmd = self.model.get_command(POWER_ON, MODE_COOL, FAN_AUTO, 22)
        timings = cmd.get_raw_timings()
        assert len(timings) == 99

    def test_header_timing(self):
        cmd = self.model.get_command(POWER_ON, MODE_COOL, FAN_AUTO, 22)
        timings = cmd.get_raw_timings()
        assert timings[0] == 9300
        assert timings[1] == -4550
