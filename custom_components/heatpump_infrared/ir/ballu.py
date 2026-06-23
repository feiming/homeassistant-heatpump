"""Ballu heatpump IR protocol implementation."""

from __future__ import annotations

from infrared_protocols.commands import Command

from .base import (
    FAN_1, FAN_2, FAN_3, FAN_AUTO, HDIR_AUTO, MODE_COOL, MODE_DRY,
    MODE_FAN, MODE_HEAT, POWER_OFF, VDIR_AUTO,
    HeatpumpIRBase, IRSenderCapture, RawIRCommand,
)

_HDR_MARK = 9300
_HDR_SPACE = 4550
_BIT_MARK = 500
_ONE_SPACE = 1650
_ZERO_SPACE = 500

_MODE_HEAT = 0x00
_MODE_COOL = 0x02
_MODE_DRY = 0x03
_MODE_FAN = 0x04
_MODE_OFF = 0x04

_FAN_AUTO = 0x00
_FAN1 = 0x01
_FAN2 = 0x02
_FAN3 = 0x03


class BalluHeatpumpIR(HeatpumpIRBase):
    model_id = "ballu"
    display_name = "Ballu"
    min_temp = 16.0
    max_temp = 30.0
    fan_speeds = 3

    def get_command(self, power, mode, fan, temp, swing_v=VDIR_AUTO, swing_h=HDIR_AUTO) -> Command:
        power_mode = 0x00
        operating_mode = _MODE_COOL
        fan_speed = _FAN_AUTO
        temperature = 21

        if power == POWER_OFF:
            power_mode = _MODE_OFF
        else:
            mode_map = {
                MODE_COOL: _MODE_COOL, MODE_DRY: _MODE_DRY,
                MODE_FAN: _MODE_FAN, MODE_HEAT: _MODE_HEAT,
            }
            operating_mode = mode_map.get(mode, _MODE_COOL)

        fan_map = {FAN_AUTO: _FAN_AUTO, FAN_1: _FAN1, FAN_2: _FAN2, FAN_3: _FAN3}
        fan_speed = fan_map.get(fan, _FAN_AUTO)

        if 15 < temp < 31:
            temperature = temp

        buf = [0x83, 0x06, 0x04, 0x42, 0x00, 0x00]

        if power_mode == _MODE_OFF:
            buf[2] = power_mode
        else:
            buf[2] = fan_speed

        buf[3] = (((temperature - 16) << 4) | operating_mode) & 0xFF

        ir = IRSenderCapture()
        ir.setFrequency(38)
        ir.mark(_HDR_MARK)
        ir.space(_HDR_SPACE)
        for b in buf:
            ir.sendIRbyte(b, _BIT_MARK, _ZERO_SPACE, _ONE_SPACE)
        ir.mark(_BIT_MARK)
        ir.space(0)
        return RawIRCommand.from_sender(ir)
