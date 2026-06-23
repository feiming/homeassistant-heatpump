"""AUX heatpump IR protocol implementation."""

from __future__ import annotations

from infrared_protocols.commands import Command

from .base import (
    FAN_1, FAN_2, FAN_3, FAN_AUTO, HDIR_AUTO, HDIR_SWING, MODE_AUTO, MODE_COOL,
    MODE_DRY, MODE_FAN, MODE_HEAT, POWER_OFF, VDIR_AUTO, VDIR_SWING,
    HeatpumpIRBase, IRSenderCapture, RawIRCommand,
)

_HDR_MARK = 8800
_HDR_SPACE = 4580
_BIT_MARK = 490
_ONE_SPACE = 1740
_ZERO_SPACE = 620

_MODE_AUTO = 0x00
_MODE_HEAT = 0x80
_MODE_COOL = 0x20
_MODE_DRY = 0x40
_MODE_FAN = 0xC0
_MODE_ON = 0x20
_MODE_OFF = 0x00

_FAN_AUTO = 0xA0
_FAN1 = 0x60
_FAN2 = 0x40
_FAN3 = 0x20

_VDIR_MANUAL = 0x00
_VDIR_SWING = 0x07

_HDIR_MANUAL = 0x00
_HDIR_SWING = 0xE0


class AUXHeatpumpIR(HeatpumpIRBase):
    model_id = "aux"
    display_name = "AUX"
    min_temp = 16.0
    max_temp = 30.0
    fan_speeds = 3

    def get_command(self, power, mode, fan, temp, swing_v=VDIR_AUTO, swing_h=HDIR_AUTO) -> Command:
        power_mode = _MODE_ON
        operating_mode = _MODE_AUTO
        fan_speed = _FAN_AUTO
        temperature = 23
        swing_vv = _VDIR_MANUAL
        swing_hh = _HDIR_MANUAL

        if power == POWER_OFF:
            power_mode = _MODE_OFF

        mode_map = {
            MODE_AUTO: _MODE_AUTO, MODE_HEAT: _MODE_HEAT,
            MODE_COOL: _MODE_COOL, MODE_DRY: _MODE_DRY, MODE_FAN: _MODE_FAN,
        }
        operating_mode = mode_map.get(mode, _MODE_AUTO)

        fan_map = {FAN_AUTO: _FAN_AUTO, FAN_1: _FAN1, FAN_2: _FAN2, FAN_3: _FAN3}
        fan_speed = fan_map.get(fan, _FAN_AUTO)

        if 15 < temp < 31:
            temperature = temp

        if swing_v == VDIR_SWING:
            swing_vv = _VDIR_SWING
        if swing_h == HDIR_SWING:
            swing_hh = _HDIR_SWING

        buf = [0xC3, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x08, 0x00]
        buf[9] |= power_mode
        buf[6] |= operating_mode
        buf[1] |= ((temperature - 8) << 3) | swing_vv
        buf[4] |= fan_speed
        buf[2] |= swing_hh

        checksum = sum(buf[:12]) & 0xFF
        buf[12] = checksum

        ir = IRSenderCapture()
        ir.setFrequency(38)
        ir.mark(_HDR_MARK)
        ir.space(_HDR_SPACE)
        for b in buf:
            ir.sendIRbyte(b, _BIT_MARK, _ZERO_SPACE, _ONE_SPACE)
        ir.mark(_BIT_MARK)
        ir.space(0)
        return RawIRCommand.from_sender(ir)
