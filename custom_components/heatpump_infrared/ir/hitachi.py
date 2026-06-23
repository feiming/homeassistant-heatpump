"""Hitachi heatpump IR protocol implementation."""

from __future__ import annotations

from infrared_protocols.commands import Command

from .base import (
    FAN_1, FAN_2, FAN_3, FAN_4, FAN_AUTO, HDIR_AUTO, HDIR_SWING,
    MODE_AUTO, MODE_COOL, MODE_DRY, MODE_FAN, MODE_HEAT, POWER_OFF,
    VDIR_AUTO, VDIR_SWING, HeatpumpIRBase, IRSenderCapture, RawIRCommand,
)

_HDR_MARK = 3436
_HDR_SPACE = 1640
_BIT_MARK = 420
_ONE_SPACE = 1250
_ZERO_SPACE = 500

_MODE_AUTO = 0x02
_MODE_HEAT = 0x03
_MODE_COOL = 0x04
_MODE_DRY = 0x05
_MODE_FAN = 0x0C

_POWER_OFF = 0x00
_POWER_ON = 0x80

_FAN_AUTO = 0x01
_FAN1 = 0x02
_FAN2 = 0x03
_FAN3 = 0x04
_FAN4 = 0x05


class HitachiHeatpumpIR(HeatpumpIRBase):
    model_id = "hitachi"
    display_name = "Hitachi"
    min_temp = 16.0
    max_temp = 32.0
    fan_speeds = 4

    def get_command(self, power, mode, fan, temp, swing_v=VDIR_AUTO, swing_h=HDIR_AUTO) -> Command:
        operating_mode = _MODE_HEAT
        fan_speed = _FAN_AUTO
        temperature = 23
        swing_vv = 0x00
        swing_hh = 0x00

        if power == POWER_OFF:
            power_mode = _POWER_OFF
        else:
            power_mode = _POWER_ON

        if mode == MODE_AUTO:
            operating_mode = _MODE_AUTO
        elif mode == MODE_HEAT:
            operating_mode = _MODE_HEAT
        elif mode == MODE_COOL:
            operating_mode = _MODE_COOL
        elif mode == MODE_DRY:
            operating_mode = _MODE_DRY
            fan = FAN_2
        elif mode == MODE_FAN:
            operating_mode = _MODE_FAN
            temp = 64
            if fan == FAN_AUTO:
                fan = FAN_2

        if fan == FAN_AUTO:
            fan_speed = _FAN_AUTO
        elif fan == FAN_1:
            fan_speed = _FAN1
        elif fan == FAN_2:
            fan_speed = _FAN2
        elif fan == FAN_3:
            fan_speed = _FAN3
        elif fan == FAN_4:
            fan_speed = _FAN4
        else:
            fan_speed = _FAN4

        if (15 < temp < 33) or temp == 64:
            temperature = temp

        if swing_v == VDIR_SWING:
            swing_vv = 0x01
        if swing_h == HDIR_SWING:
            swing_hh = 0x01

        buf = [
            0x01, 0x10, 0x30, 0x40, 0xBF, 0x01, 0xFE, 0x11, 0x12,
            0x08, 0x00, 0x00, 0x00, 0x00, 0x06, 0x06, 0x00, 0x80,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x80, 0x01, 0x00, 0x00, 0x00,
        ]

        if temperature == 16:
            buf[9] = 0x09
        buf[10] = operating_mode
        buf[11] = (temperature << 1) & 0xFF
        buf[13] = fan_speed
        buf[14] |= swing_vv
        buf[15] |= swing_hh
        buf[17] = power_mode

        checksum = 1086
        for i in range(27):
            checksum -= buf[i]
        buf[27] = checksum & 0xFF

        ir = IRSenderCapture()
        ir.setFrequency(38)
        ir.mark(_HDR_MARK)
        ir.space(_HDR_SPACE)
        for b in buf:
            ir.sendIRbyte(b, _BIT_MARK, _ZERO_SPACE, _ONE_SPACE)
        ir.mark(_BIT_MARK)
        ir.space(0)
        return RawIRCommand.from_sender(ir)
