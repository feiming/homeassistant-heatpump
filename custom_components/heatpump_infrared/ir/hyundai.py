"""Hyundai heatpump IR protocol implementation."""

from __future__ import annotations

from infrared_protocols.commands import Command

from .base import (
    FAN_1, FAN_2, FAN_3, FAN_AUTO, HDIR_AUTO, MODE_AUTO, MODE_COOL,
    MODE_DRY, MODE_FAN, MODE_HEAT, POWER_OFF, VDIR_AUTO, VDIR_SWING,
    HeatpumpIRBase, IRSenderCapture, RawIRCommand,
)

_HDR_MARK = 8840
_HDR_SPACE = 4440
_BIT_MARK = 640
_ONE_SPACE = 1670
_ZERO_SPACE = 570

_MODE_AUTO = 0x00
_MODE_HEAT = 0x04
_MODE_COOL = 0x01
_MODE_DRY = 0x02
_MODE_FAN = 0x03
_MODE_ON = 0x08
_MODE_OFF = 0x00

_FAN_AUTO = 0x00
_FAN1 = 0x10
_FAN2 = 0x20
_FAN3 = 0x30

_VS_AUTO = 0x00
_VS_SWING = 0x40


class HyundaiHeatpumpIR(HeatpumpIRBase):
    model_id = "hyundai"
    display_name = "Hyundai"
    min_temp = 16.0
    max_temp = 30.0
    fan_speeds = 3

    def get_command(self, power, mode, fan, temp, swing_v=VDIR_AUTO, swing_h=HDIR_AUTO) -> Command:
        power_mode = _MODE_ON
        operating_mode = _MODE_HEAT
        fan_speed = _FAN_AUTO
        temperature = 23
        swing_vv = _VS_AUTO

        if power == POWER_OFF:
            power_mode = _MODE_OFF

        mode_map = {
            MODE_AUTO: _MODE_AUTO, MODE_HEAT: _MODE_HEAT,
            MODE_COOL: _MODE_COOL, MODE_DRY: _MODE_DRY, MODE_FAN: _MODE_FAN,
        }
        operating_mode = mode_map.get(mode, _MODE_HEAT)

        if mode == MODE_FAN:
            temp = 24

        fan_map = {FAN_AUTO: _FAN_AUTO, FAN_1: _FAN1, FAN_2: _FAN2, FAN_3: _FAN3}
        fan_speed = fan_map.get(fan, _FAN_AUTO)

        if swing_v == VDIR_SWING:
            swing_vv = _VS_SWING

        if 15 < temp < 31:
            temperature = temp

        buf = [0x00, 0x00, 0x00, 0x50]
        buf[0] = swing_vv | fan_speed | power_mode | operating_mode
        buf[1] = temperature - 16

        ir = IRSenderCapture()
        ir.setFrequency(38)
        ir.mark(_HDR_MARK)
        ir.space(_HDR_SPACE)
        for b in buf:
            ir.sendIRbyte(b, _BIT_MARK, _ZERO_SPACE, _ONE_SPACE)
        # 3 extra bits: '010'
        ir.mark(_BIT_MARK)
        ir.space(_ZERO_SPACE)
        ir.mark(_BIT_MARK)
        ir.space(_ONE_SPACE)
        ir.mark(_BIT_MARK)
        ir.space(_ZERO_SPACE)
        ir.mark(_BIT_MARK)
        ir.space(0)
        return RawIRCommand.from_sender(ir)
