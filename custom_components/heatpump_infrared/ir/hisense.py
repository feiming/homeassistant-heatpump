"""Hisense heatpump IR protocol implementation."""

from __future__ import annotations

from infrared_protocols.commands import Command

from .base import (
    FAN_1, FAN_2, FAN_3, FAN_AUTO, HDIR_AUTO, MODE_AUTO, MODE_COOL,
    MODE_DRY, MODE_FAN, MODE_HEAT, POWER_OFF, VDIR_AUTO,
    HeatpumpIRBase, IRSenderCapture, RawIRCommand,
)

_HDR_MARK = 9060
_HDR_SPACE = 4550
_BIT_MARK = 520
_ONE_SPACE = 1700
_ZERO_SPACE = 630
_MSG_SPACE = 8140

_POWER_OFF = 0x04
_POWER_ON = 0x00

_MODE_AUTO = 0x04
_MODE_HEAT = 0x00
_MODE_COOL = 0x02
_MODE_DRY = 0x03
_MODE_FAN_IR = 0x04

_FAN_AUTO = 0x00
_FAN1 = 0x03
_FAN2 = 0x02
_FAN3 = 0x01


class HisenseHeatpumpIR(HeatpumpIRBase):
    model_id = "hisense_aud"
    display_name = "Hisense AUD"
    min_temp = 18.0
    max_temp = 32.0
    fan_speeds = 3

    def get_command(self, power, mode, fan, temp, swing_v=VDIR_AUTO, swing_h=HDIR_AUTO) -> Command:
        power_mode = _POWER_ON
        operating_mode = _MODE_HEAT
        fan_speed = _FAN_AUTO
        temperature = 21

        if power == POWER_OFF:
            power_mode = _POWER_OFF
        else:
            if mode == MODE_AUTO:
                operating_mode = _MODE_AUTO
                fan = FAN_AUTO
            elif mode == MODE_HEAT:
                operating_mode = _MODE_HEAT
            elif mode == MODE_COOL:
                operating_mode = _MODE_COOL
            elif mode == MODE_DRY:
                operating_mode = _MODE_DRY
                fan = FAN_AUTO
            elif mode == MODE_FAN:
                operating_mode = _MODE_FAN_IR
                if fan == FAN_AUTO:
                    fan = FAN_1
                    temp = 25

        if fan == FAN_AUTO:
            fan_speed = _FAN_AUTO
        elif fan == FAN_1:
            fan_speed = _FAN1
        elif fan == FAN_2:
            fan_speed = _FAN2
        elif fan == FAN_3:
            fan_speed = _FAN3

        if 17 < temp < 33:
            temperature = temp

        buf = [0x87, 0x06, 0x00, 0x00, 0x00, 0x00, 0x00,
               0x00, 0x00, 0x00, 0x0C, 0x00, 0x00, 0x00]

        buf[2] = fan_speed | power_mode
        buf[3] = (((temperature - 18) << 4) | operating_mode) & 0xFF

        checksum = buf[2]
        for i in range(3, 13):
            checksum ^= buf[i]
        buf[13] = checksum & 0xFF

        ir = IRSenderCapture()
        ir.setFrequency(38)
        ir.mark(_HDR_MARK)
        ir.space(_HDR_SPACE)
        for i in range(7):
            ir.sendIRbyte(buf[i], _BIT_MARK, _ZERO_SPACE, _ONE_SPACE)
        ir.mark(_BIT_MARK)
        ir.space(_MSG_SPACE)
        for i in range(7, 14):
            ir.sendIRbyte(buf[i], _BIT_MARK, _ZERO_SPACE, _ONE_SPACE)
        ir.mark(_BIT_MARK)
        ir.space(0)
        return RawIRCommand.from_sender(ir)
