"""Nibe heatpump IR protocol implementation."""

from __future__ import annotations

from infrared_protocols.commands import Command

from .base import (
    FAN_2, FAN_3, FAN_4, FAN_AUTO, FAN_SILENT, HDIR_AUTO, MODE_AUTO,
    MODE_COOL, MODE_DRY, MODE_FAN, MODE_HEAT, POWER_OFF, VDIR_AUTO,
    VDIR_DOWN, VDIR_MDOWN, VDIR_MIDDLE, VDIR_MUP, VDIR_SWING, VDIR_UP,
    HeatpumpIRBase, IRSenderCapture, RawIRCommand,
)

_HDR_MARK = 6382
_HDR_SPACE = 3144
_BIT_MARK = 412
_ONE_SPACE = 2102
_ZERO_SPACE = 823

_POWER_OFF = 0x00
_POWER_ON = 0x01

_MODE_COOL = 0x00
_MODE_HEAT = 0x01
_MODE_DRY = 0x04
_MODE_FAN = 0x06
_MODE_AUTO = 0x05

_FAN_AUTO = 0x00
_FAN_HIGH = 0x03
_FAN_MED = 0x01
_FAN_LOW = 0x02

_VDIR_AUTO = 0x00
_VDIR_POS1 = 0x04
_VDIR_POS2 = 0x02
_VDIR_POS3 = 0x06
_VDIR_POS4 = 0x01
_VDIR_POS5 = 0x05
_VDIR_ALL = 0x07


def _reverse_bits(value: int, bit_length: int) -> int:
    result = 0
    for i in range(bit_length):
        bit = (value >> i) & 1
        result |= bit << (bit_length - 1 - i)
    return result


class NibeHeatpumpIR(HeatpumpIRBase):
    model_id = "nibe"
    display_name = "Nibe"
    min_temp = 10.0
    max_temp = 32.0
    fan_speeds = 4

    def get_command(self, power, mode, fan, temp, swing_v=VDIR_AUTO, swing_h=HDIR_AUTO) -> Command:
        power_mode = _POWER_ON
        operating_mode = _MODE_HEAT
        fan_speed = _FAN_AUTO
        temperature = 21 - 4  # offset: actual - 4
        swing_vv = _VDIR_AUTO
        night_mode = 0x00
        i_feel_mode = 0x01  # default on
        air_filter = 0x01   # default on
        turbo_mode = 0x00

        if power == POWER_OFF:
            power_mode = _POWER_OFF

        mode_map = {
            MODE_AUTO: _MODE_AUTO, MODE_HEAT: _MODE_HEAT,
            MODE_COOL: _MODE_COOL, MODE_DRY: _MODE_DRY, MODE_FAN: _MODE_FAN,
        }
        operating_mode = mode_map.get(mode, _MODE_HEAT)

        if fan == FAN_AUTO:
            fan_speed = _FAN_AUTO if mode != MODE_FAN else _FAN_HIGH
        elif fan == FAN_4:
            fan_speed = _FAN_HIGH
        elif fan == FAN_3:
            fan_speed = _FAN_MED
        elif fan == FAN_2:
            fan_speed = _FAN_LOW
        elif fan == FAN_SILENT:
            night_mode = 0x01

        heat_mode = operating_mode in (_MODE_HEAT,)
        cool_dry = operating_mode in (_MODE_COOL, _MODE_DRY)

        if swing_v == VDIR_AUTO:
            swing_vv = _VDIR_AUTO
        elif swing_v == VDIR_SWING:
            swing_vv = _VDIR_ALL
        elif swing_v == VDIR_UP:
            swing_vv = _VDIR_POS3 if heat_mode else _VDIR_POS1
        elif swing_v == VDIR_MUP:
            swing_vv = _VDIR_POS3 if heat_mode else _VDIR_POS2
        elif swing_v == VDIR_MIDDLE:
            swing_vv = _VDIR_POS3
        elif swing_v == VDIR_MDOWN:
            swing_vv = _VDIR_POS4
        elif swing_v == VDIR_DOWN:
            swing_vv = _VDIR_POS4 if cool_dry else _VDIR_POS5

        if 9 < temp < 33:
            temperature = temp - 4

        temp_swap = _reverse_bits(temperature, 5)

        buf = [0x35, 0xAF, 0x00, 0x00, 0x40, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00]
        buf[2] |= operating_mode << 2
        buf[2] |= (temp_swap >> 3)
        buf[3] |= (temp_swap & 0x07) << 5
        buf[3] |= fan_speed << 3
        buf[4] |= swing_vv << 3
        buf[5] |= 0x7
        buf[7] |= (0x7 << 5)
        # time = 0 (00:00), reversed 11-bit
        buf[9] |= i_feel_mode
        buf[9] |= (power_mode << 2)
        buf[9] |= (air_filter << 3)
        buf[9] |= (turbo_mode << 4)
        buf[9] |= (night_mode << 5)

        checksum = 0
        for i in range(11):
            if i == 10:
                checksum += _reverse_bits(buf[i], 2)
            else:
                checksum += _reverse_bits(buf[i], 8)
        buf[11] = _reverse_bits(checksum & 0xFF, 8)

        ir = IRSenderCapture()
        ir.setFrequency(38)
        ir.mark(_HDR_MARK)
        ir.space(_HDR_SPACE)
        for i, b in enumerate(buf):
            if i == 10:
                ir.sendIRbyte(_reverse_bits(b, 2), _BIT_MARK, _ZERO_SPACE, _ONE_SPACE, 2)
            else:
                ir.sendIRbyte(_reverse_bits(b, 8), _BIT_MARK, _ZERO_SPACE, _ONE_SPACE)
        ir.mark(_BIT_MARK)
        ir.space(0)
        return RawIRCommand.from_sender(ir)
