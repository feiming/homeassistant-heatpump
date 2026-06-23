"""Electrolux YAL heatpump IR protocol implementation."""

from __future__ import annotations

from infrared_protocols.commands import Command

from .base import (
    FAN_1, FAN_2, FAN_3, FAN_AUTO, HDIR_AUTO, HDIR_SWING, MODE_AUTO, MODE_COOL,
    MODE_DRY, MODE_FAN, MODE_HEAT, POWER_OFF, VDIR_AUTO, VDIR_SWING,
    HeatpumpIRBase, IRSenderCapture, RawIRCommand,
)

_HDR_MARK = 9000
_HDR_SPACE = 4000
_BIT_MARK = 620
_ONE_SPACE = 1600
_ZERO_SPACE = 540
_MSG_SPACE = 19000

_POWER_ON = 0x08
_POWER_OFF = 0x00

_MODE_AUTO = 0x00
_MODE_COOL = 0x01
_MODE_DRY = 0x02
_MODE_FAN = 0x03
_MODE_HEAT = 0x04

_FAN_AUTO = 0x00
_FAN1 = 0x10
_FAN2 = 0x20
_FAN3 = 0x30

_VDIR_AUTO = 0x00
_VDIR_SWING = 0x01

_HDIR_AUTO = 0x00
_HDIR_SWING = 0x01


class ElectroluxYALHeatpumpIR(HeatpumpIRBase):
    model_id = "electrolux_yal"
    display_name = "Electrolux YAL"
    min_temp = 16.0
    max_temp = 30.0
    fan_speeds = 3

    def get_command(self, power, mode, fan, temp, swing_v=VDIR_AUTO, swing_h=HDIR_AUTO) -> Command:
        power_mode = _POWER_ON
        operating_mode = _MODE_HEAT
        fan_speed = _FAN_AUTO
        temperature = 5  # temp - 16, so 21°C
        swing_vv = _VDIR_AUTO
        swing_hh = _HDIR_AUTO

        if power == POWER_OFF:
            power_mode = _POWER_OFF
        else:
            if mode == MODE_AUTO:
                operating_mode = _MODE_AUTO
                temp = 25
            elif mode == MODE_HEAT:
                operating_mode = _MODE_HEAT
            elif mode == MODE_COOL:
                operating_mode = _MODE_COOL
            elif mode == MODE_DRY:
                operating_mode = _MODE_DRY
                fan = FAN_1
            elif mode == MODE_FAN:
                operating_mode = _MODE_FAN

        fan_map = {FAN_AUTO: _FAN_AUTO, FAN_1: _FAN1, FAN_2: _FAN2, FAN_3: _FAN3}
        fan_speed = fan_map.get(fan, _FAN_AUTO)

        if swing_v == VDIR_SWING:
            swing_vv = _VDIR_SWING
        if swing_h == HDIR_SWING:
            swing_hh = _HDIR_SWING

        if 15 < temp < 31:
            temperature = temp - 16

        buf = [0x00, 0x00, 0x20, 0x50, 0x00, 0x20, 0x00, 0x00]
        buf[0] = fan_speed | operating_mode | power_mode
        buf[1] = temperature

        if swing_vv == _VDIR_SWING:
            buf[0] |= (1 << 6)
            buf[4] |= 0x01
        if swing_hh == _HDIR_SWING:
            buf[0] |= (1 << 6)
            buf[4] |= 0x10

        checksum = (
            (buf[0] & 0x0F) +
            (buf[1] & 0x0F) +
            (buf[2] & 0x0F) +
            (buf[3] & 0x0F) +
            ((buf[4] & 0xF0) >> 4) +
            ((buf[5] & 0xF0) >> 4) +
            ((buf[6] & 0xF0) >> 4) +
            0x0A
        ) & 0x0F
        buf[7] = (checksum << 4) | (buf[7] & 0x0F)

        ir = IRSenderCapture()
        ir.setFrequency(38)
        ir.mark(_HDR_MARK)
        ir.space(_HDR_SPACE)
        for i in range(4):
            ir.sendIRbyte(buf[i], _BIT_MARK, _ZERO_SPACE, _ONE_SPACE)
        # 3 bits always '010'
        ir.mark(_BIT_MARK)
        ir.space(_ZERO_SPACE)
        ir.mark(_BIT_MARK)
        ir.space(_ONE_SPACE)
        ir.mark(_BIT_MARK)
        ir.space(_ZERO_SPACE)
        ir.mark(_BIT_MARK)
        ir.space(_MSG_SPACE)
        for i in range(4, 8):
            ir.sendIRbyte(buf[i], _BIT_MARK, _ZERO_SPACE, _ONE_SPACE)
        ir.mark(_BIT_MARK)
        ir.space(0)
        return RawIRCommand.from_sender(ir)
