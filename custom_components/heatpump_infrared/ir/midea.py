"""Midea heatpump IR protocol implementation."""

from __future__ import annotations

from infrared_protocols.commands import Command

from .base import (
    FAN_1, FAN_2, FAN_3, FAN_AUTO, HDIR_AUTO, MODE_AUTO, MODE_COOL,
    MODE_DRY, MODE_FAN, MODE_HEAT, MODE_MAINT, POWER_OFF, VDIR_AUTO,
    HeatpumpIRBase, IRSenderCapture, RawIRCommand,
)

_HDR_MARK = 4420
_HDR_SPACE = 4300
_BIT_MARK = 620
_ONE_SPACE = 1560
_ZERO_SPACE = 480
_MSG_SPACE = 5100

_MODE_AUTO = 0x10
_MODE_HEAT = 0x30
_MODE_COOL = 0x00
_MODE_DRY = 0x20
_MODE_FAN_IR = 0x60
_MODE_FP = 0x70
_MODE_OFF = 0xFE
_MODE_ON = 0xFF

_FAN_AUTO = 0x02
_FAN1 = 0x06
_FAN2 = 0x05
_FAN3 = 0x03

_OFF_MSG = [0x4D, 0xDE, 0x07]
_FP_MSG = [0xAD, 0xAF, 0xB5]

_TEMPERATURES = [0, 8, 12, 4, 6, 14, 10, 2, 3, 11, 9, 1, 5, 13]


class MideaHeatpumpIR(HeatpumpIRBase):
    model_id = "midea"
    display_name = "Midea (Ultimate Pro Plus)"
    min_temp = 16.0
    max_temp = 30.0
    fan_speeds = 3

    def get_command(self, power, mode, fan, temp, swing_v=VDIR_AUTO, swing_h=HDIR_AUTO) -> Command:
        operating_mode = _MODE_HEAT
        fan_speed = _FAN_AUTO
        temperature = 23

        if power == POWER_OFF:
            operating_mode = _MODE_OFF
        else:
            if mode == MODE_AUTO:
                operating_mode = _MODE_AUTO
            elif mode == MODE_HEAT:
                operating_mode = _MODE_HEAT
            elif mode == MODE_COOL:
                operating_mode = _MODE_COOL
            elif mode == MODE_DRY:
                operating_mode = _MODE_DRY
            elif mode == MODE_FAN:
                operating_mode = _MODE_FAN_IR
            elif mode == MODE_MAINT:
                operating_mode = _MODE_FP

        if fan == FAN_AUTO:
            fan_speed = _FAN_AUTO
        elif fan == FAN_1:
            fan_speed = _FAN1
        elif fan == FAN_2:
            fan_speed = _FAN2
        elif fan == FAN_3:
            fan_speed = _FAN3

        if 16 < temp < 31:
            temperature = temp

        buf = [0x4D, 0x00, 0x00]

        if operating_mode == _MODE_OFF:
            buf = list(_OFF_MSG)
        elif operating_mode == _MODE_FP:
            buf = list(_FP_MSG)
        else:
            buf[1] = (~fan_speed) & 0xFF
            if operating_mode == _MODE_FAN_IR:
                buf[2] = _MODE_DRY | 0x07
            else:
                buf[2] = operating_mode | _TEMPERATURES[temperature - 17]

        ir = IRSenderCapture()
        ir.setFrequency(38)
        ir.mark(_HDR_MARK)
        ir.space(_HDR_SPACE)
        for i in range(3):
            ir.sendIRbyte(buf[i], _BIT_MARK, _ZERO_SPACE, _ONE_SPACE)
            ir.sendIRbyte((~buf[i]) & 0xFF, _BIT_MARK, _ZERO_SPACE, _ONE_SPACE)
        ir.mark(_BIT_MARK)
        ir.space(_MSG_SPACE)
        ir.mark(_HDR_MARK)
        ir.space(_HDR_SPACE)
        for i in range(3):
            ir.sendIRbyte(buf[i], _BIT_MARK, _ZERO_SPACE, _ONE_SPACE)
            ir.sendIRbyte((~buf[i]) & 0xFF, _BIT_MARK, _ZERO_SPACE, _ONE_SPACE)
        ir.mark(_BIT_MARK)
        ir.space(0)
        return RawIRCommand.from_sender(ir)
