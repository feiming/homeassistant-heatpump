"""Daikin ARC417 heatpump IR protocol implementation."""

from __future__ import annotations

from infrared_protocols.commands import Command

from .base import (
    FAN_1, FAN_2, FAN_3, FAN_4, FAN_5, FAN_AUTO, HDIR_AUTO, MODE_AUTO,
    MODE_COOL, MODE_DRY, MODE_FAN, MODE_HEAT, POWER_OFF, POWER_ON, VDIR_AUTO,
    HeatpumpIRBase, IRSenderCapture, RawIRCommand,
)

_HDR_MARK = 5050
_HDR_SPACE = 2100
_BIT_MARK = 391
_ONE_SPACE = 1725
_ZERO_SPACE = 667
_MSG_SPACE = 30000

_MODE_AUTO = 0x10
_MODE_HEAT = 0x40
_MODE_COOL = 0x30
_MODE_DRY = 0x20
_MODE_FAN = 0x60
_MODE_OFF = 0x00
_MODE_ON = 0x01

_FAN_AUTO = 0x0A
_FAN1 = 0x03
_FAN2 = 0x04
_FAN3 = 0x05
_FAN4 = 0x06
_FAN5 = 0x07


class DaikinARC417HeatpumpIR(HeatpumpIRBase):
    model_id = "daikin_arc417"
    display_name = "Daikin ARC417"
    min_temp = 18.0
    max_temp = 30.0
    fan_speeds = 5

    def get_command(self, power, mode, fan, temp, swing_v=VDIR_AUTO, swing_h=HDIR_AUTO) -> Command:
        operating_mode = _MODE_OFF | _MODE_AUTO
        fan_speed = _FAN_AUTO
        temperature = 0x10  # 18°C encoded

        if power == POWER_ON:
            operating_mode |= _MODE_ON

        if mode == MODE_AUTO:
            operating_mode |= _MODE_AUTO
        elif mode == MODE_HEAT:
            operating_mode |= _MODE_HEAT
        elif mode == MODE_COOL:
            operating_mode |= _MODE_COOL
        elif mode == MODE_DRY:
            operating_mode |= _MODE_DRY
            temperature = 0x80
        elif mode == MODE_FAN:
            operating_mode |= _MODE_FAN
            temp = 0xC0

        if mode != MODE_DRY and mode != MODE_FAN:
            if (mode == MODE_HEAT and 13 < temp < 29) or (15 < temp < 33):
                temperature = (temp << 1) - 20

        fan_map = {FAN_AUTO: _FAN_AUTO, FAN_1: _FAN1, FAN_2: _FAN2, FAN_3: _FAN3, FAN_4: _FAN4, FAN_5: _FAN5}
        fan_speed = fan_map.get(fan, _FAN_AUTO)

        buf = [0x11, 0xDA, 0x27, 0xF0, 0x0D, 0x00, 0x0F,
               0x11, 0xDA, 0x27, 0x00, 0xD3, 0x11, 0x00, 0x00, 0x00, 0x1E, 0x0A, 0x08, 0x26]

        buf[12] = operating_mode
        buf[16] = temperature
        buf[17] = fan_speed

        checksum = sum(buf[7:19]) & 0xFF
        buf[19] = checksum

        ir = IRSenderCapture()
        ir.setFrequency(38)
        ir.mark(_HDR_MARK)
        ir.space(_HDR_SPACE)
        for i in range(7):
            ir.sendIRbyte(buf[i], _BIT_MARK, _ZERO_SPACE, _ONE_SPACE)
        ir.mark(_BIT_MARK)
        ir.space(_MSG_SPACE)
        ir.mark(_HDR_MARK)
        ir.space(_HDR_SPACE)
        for i in range(7, 20):
            ir.sendIRbyte(buf[i], _BIT_MARK, _ZERO_SPACE, _ONE_SPACE)
        ir.mark(_BIT_MARK)
        ir.space(0)
        return RawIRCommand.from_sender(ir)
