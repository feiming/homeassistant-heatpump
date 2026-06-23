"""Philco PHS32 heatpump IR protocol implementation."""

from __future__ import annotations

from infrared_protocols.commands import Command

from .base import (
    FAN_1, FAN_2, FAN_3, FAN_4, FAN_5, FAN_AUTO, HDIR_AUTO, MODE_COOL,
    MODE_DRY, MODE_FAN, MODE_HEAT, POWER_OFF, VDIR_AUTO,
    HeatpumpIRBase, IRSenderCapture, RawIRCommand,
)

_HDR_MARK = 9000
_HDR_SPACE = 4500
_MSG_SPACE = 8000
_BIT_MARK = 562
_ONE_SPACE = 1687
_ZERO_SPACE = 562

_POWER_ON = 0x30
_POWER_OFF = 0x20

_OFF_TEMP = 0x12
_DRY_TEMP = 0x19
_FAN_TEMP = 0x19

_MODE_HEAT = 0x00
_MODE_COOL = 0x02
_MODE_DRY = 0x03
_MODE_FAN = 0x04

_FAN_AUTO = 0x00
_FAN_LOW = 0x03
_FAN_MED = 0x02
_FAN_HIGH = 0x01


class PhilcoPHS32HeatpumpIR(HeatpumpIRBase):
    model_id = "philco_phs32"
    display_name = "Philco PHS32"
    min_temp = 18.0
    max_temp = 30.0
    fan_speeds = 3

    def get_command(self, power, mode, fan, temp, swing_v=VDIR_AUTO, swing_h=HDIR_AUTO) -> Command:
        power_mode = _POWER_ON
        operating_mode = _MODE_COOL
        fan_speed = _FAN_AUTO
        temperature = 24

        if power == POWER_OFF:
            power_mode = _POWER_OFF
            temperature = _OFF_TEMP
            operating_mode = _MODE_COOL
        else:
            if mode == MODE_HEAT:
                operating_mode = _MODE_HEAT
            elif mode == MODE_COOL:
                operating_mode = _MODE_COOL
            elif mode == MODE_DRY:
                operating_mode = _MODE_DRY
                fan = FAN_AUTO
                temp = _DRY_TEMP
            elif mode == MODE_FAN:
                operating_mode = _MODE_FAN
                temp = _FAN_TEMP
                if fan == FAN_AUTO:
                    fan = FAN_2

            if 17 < temp < 31:
                temperature = temp

        fan_map = {
            FAN_AUTO: _FAN_AUTO, FAN_1: _FAN_LOW, FAN_2: _FAN_LOW,
            FAN_3: _FAN_MED, FAN_4: _FAN_HIGH, FAN_5: _FAN_HIGH,
        }
        fan_speed = fan_map.get(fan, _FAN_AUTO)

        buf = [0x83, 0x06, 0x04, 0x00, 0x00, 0x00, 0x00,
               0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
               0x00, 0x00, 0x00, 0x00, 0x00, 0x08, 0x00]

        buf[18] = power_mode
        buf[2] += fan_speed
        buf[3] = ((temperature - 18) << 4) | operating_mode

        # Checksum 1: XOR bytes 2-12 into byte 13
        cs1 = 0
        for i in range(2, 13):
            cs1 ^= buf[i]
        buf[13] = cs1

        # Checksum 2: XOR bytes 14-19 into byte 20
        cs2 = 0
        for i in range(14, 20):
            cs2 ^= buf[i]
        buf[20] = cs2

        ir = IRSenderCapture()
        ir.setFrequency(38)
        ir.mark(_HDR_MARK)
        ir.space(_HDR_SPACE)
        for i in range(6):
            ir.sendIRbyte(buf[i], _BIT_MARK, _ZERO_SPACE, _ONE_SPACE)
        ir.mark(_BIT_MARK)
        ir.space(_MSG_SPACE)
        for i in range(6, 14):
            ir.sendIRbyte(buf[i], _BIT_MARK, _ZERO_SPACE, _ONE_SPACE)
        ir.mark(_BIT_MARK)
        ir.space(_MSG_SPACE)
        for i in range(14, 21):
            ir.sendIRbyte(buf[i], _BIT_MARK, _ZERO_SPACE, _ONE_SPACE)
        ir.mark(_BIT_MARK)
        ir.space(0)
        return RawIRCommand.from_sender(ir)
