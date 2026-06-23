"""Daikin ARC480 heatpump IR protocol implementation."""

from __future__ import annotations

from infrared_protocols.commands import Command

from .base import (
    FAN_1, FAN_2, FAN_3, FAN_4, FAN_5, FAN_AUTO, FAN_SILENT, HDIR_AUTO,
    MODE_AUTO, MODE_COOL, MODE_DRY, MODE_FAN, MODE_HEAT, POWER_OFF, POWER_ON,
    VDIR_AUTO, VDIR_SWING,
    HeatpumpIRBase, IRSenderCapture, RawIRCommand,
)

_HDR_MARK = 3360
_HDR_SPACE = 1760
_BIT_MARK = 360
_ONE_SPACE = 1370
_ZERO_SPACE = 520

_MODE_AUTO = 0x00
_MODE_HEAT = 0x40
_MODE_COOL = 0x30
_MODE_DRY = 0x20
_MODE_FAN = 0x60
_MODE_OFF = 0x00
_MODE_ON = 0x01

_FAN_AUTO = 0xA0
_FAN1 = 0x30
_FAN2 = 0x40
_FAN3 = 0x50
_FAN4 = 0x60
_FAN5 = 0x70
_FAN_SILENT = 0xB0

_SWING_ON = 0x0F
_SWING_OFF = 0x00

_COMFORT_OFF = 0x00
_ECONO_OFF = 0x00
_SENSOR_OFF = 0x00
_QUIET_OFF = 0x00
_POWERFUL_OFF = 0x00


class DaikinARC480HeatpumpIR(HeatpumpIRBase):
    model_id = "daikin_arc480"
    display_name = "Daikin ARC480"
    min_temp = 18.0
    max_temp = 30.0
    fan_speeds = 5

    def get_command(self, power, mode, fan, temp, swing_v=VDIR_AUTO, swing_h=HDIR_AUTO) -> Command:
        operating_mode = _MODE_OFF
        fan_speed = _FAN_AUTO
        temperature = 23
        swing_vv = _SWING_OFF

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
            temp = 0x24
        elif mode == MODE_FAN:
            operating_mode |= _MODE_FAN
            temp = 0xC0

        fan_map = {
            FAN_AUTO: _FAN_AUTO, FAN_1: _FAN1, FAN_2: _FAN2, FAN_3: _FAN3,
            FAN_4: _FAN4, FAN_5: _FAN5, FAN_SILENT: _FAN_SILENT,
        }
        fan_speed = fan_map.get(fan, _FAN_AUTO)

        if swing_v == VDIR_SWING:
            swing_vv = _SWING_ON

        if mode == MODE_HEAT:
            if 9 < temp <= 30:
                temperature = temp << 1
        elif 17 < temp <= 30:
            temperature = temp << 1

        buf = [0x11, 0xDA, 0x27, 0x00, 0x00, 0x00, 0x00, 0x00,
               0x00, 0x00, 0x00, 0x00, 0x60, 0x00, 0x00, 0xC5, 0x00, 0x08, 0x00]

        buf[5] = operating_mode
        buf[6] = temperature
        buf[8] = fan_speed + swing_vv
        buf[13] = _QUIET_OFF + _POWERFUL_OFF
        buf[16] = _COMFORT_OFF + _ECONO_OFF + _SENSOR_OFF

        checksum = sum(buf[:18]) & 0xFF
        buf[18] = checksum

        ir = IRSenderCapture()
        ir.setFrequency(38)
        ir.mark(_HDR_MARK)
        ir.space(_HDR_SPACE)
        for b in buf:
            ir.sendIRbyte(b, _BIT_MARK, _ZERO_SPACE, _ONE_SPACE)
        ir.mark(_BIT_MARK)
        ir.space(0)
        return RawIRCommand.from_sender(ir)
