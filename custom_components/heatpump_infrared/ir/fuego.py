"""Fuego and Airway heatpump IR protocol implementations."""

from __future__ import annotations

from infrared_protocols.commands import Command

from .base import (
    FAN_1, FAN_2, FAN_3, FAN_AUTO, HDIR_AUTO, MODE_AUTO, MODE_COOL,
    MODE_DRY, MODE_FAN, MODE_HEAT, POWER_OFF, VDIR_AUTO, VDIR_DOWN,
    VDIR_MDOWN, VDIR_MIDDLE, VDIR_MUP, VDIR_SWING, VDIR_UP,
    HeatpumpIRBase, IRSenderCapture, RawIRCommand,
)

# Fuego timing
_FUEGO_HDR_MARK = 3600
_FUEGO_HDR_SPACE = 1630
_FUEGO_BIT_MARK = 420
_FUEGO_ONE_SPACE = 1380
_FUEGO_ZERO_SPACE = 420

_FUEGO_MODE_AUTO = 0x08
_FUEGO_MODE_HEAT = 0x01
_FUEGO_MODE_COOL = 0x03
_FUEGO_MODE_DRY = 0x02
_FUEGO_MODE_FAN = 0x07
_FUEGO_MODE_ON = 0x04
_FUEGO_MODE_OFF = 0x00

_FUEGO_FAN_AUTO = 0x00
_FUEGO_FAN1 = 0x02
_FUEGO_FAN2 = 0x03
_FUEGO_FAN3 = 0x05

_FUEGO_VS_AUTO = 0x00
_FUEGO_VS_UP = 0x08
_FUEGO_VS_MUP = 0x10
_FUEGO_VS_MIDDLE = 0x18
_FUEGO_VS_MDOWN = 0x20
_FUEGO_VS_DOWN = 0x28
_FUEGO_VS_SWING = 0x38

# Airway timing
_AIRWAY_HDR_MARK = 3080
_AIRWAY_HDR_SPACE = 1700
_AIRWAY_BIT_MARK = 400
_AIRWAY_ONE_SPACE = 1060
_AIRWAY_ZERO_SPACE = 320

_AIRWAY_MODE_AUTO = 0x08
_AIRWAY_MODE_HEAT = 0x01
_AIRWAY_MODE_COOL = 0x03
_AIRWAY_MODE_DRY = 0x02
_AIRWAY_MODE_FAN = 0x07
_AIRWAY_MODE_ON = 0x04
_AIRWAY_MODE_OFF = 0x00

_AIRWAY_FAN_AUTO = 0x00
_AIRWAY_FAN1 = 0x02
_AIRWAY_FAN2 = 0x03
_AIRWAY_FAN3 = 0x05

_AIRWAY_VS_AUTO = 0x00
_AIRWAY_VS_UP = 0x08
_AIRWAY_VS_MUP = 0x10
_AIRWAY_VS_MIDDLE = 0x18
_AIRWAY_VS_MDOWN = 0x20
_AIRWAY_VS_DOWN = 0x28
_AIRWAY_VS_SWING = 0x38


def _build_fuego_template(power_mode, operating_mode, fan_speed, temperature, swing_vv,
                           hdr_mark, hdr_space, bit_mark, zero_space, one_space,
                           template_base, power_off_swing):
    buf = list(template_base)
    buf[5] |= power_mode
    buf[6] |= operating_mode
    buf[7] |= 31 - temperature
    buf[8] |= fan_speed | swing_vv

    checksum = sum(buf[:13]) & 0xFF
    buf[13] = checksum

    ir = IRSenderCapture()
    ir.setFrequency(38)
    ir.mark(hdr_mark)
    ir.space(hdr_space)
    for b in buf:
        ir.sendIRbyte(b, bit_mark, zero_space, one_space)
    ir.mark(bit_mark)
    ir.space(0)
    return RawIRCommand.from_sender(ir)


class FuegoHeatpumpIR(HeatpumpIRBase):
    model_id = "fuego"
    display_name = "Fuego"
    min_temp = 18.0
    max_temp = 31.0
    fan_speeds = 3

    def get_command(self, power, mode, fan, temp, swing_v=VDIR_AUTO, swing_h=HDIR_AUTO) -> Command:
        power_mode = _FUEGO_MODE_ON
        operating_mode = _FUEGO_MODE_HEAT
        fan_speed = _FUEGO_FAN_AUTO
        temperature = 23
        swing_vv = _FUEGO_VS_SWING

        if power == POWER_OFF:
            power_mode = _FUEGO_MODE_OFF
            swing_v = VDIR_MUP

        mode_map = {
            MODE_AUTO: _FUEGO_MODE_AUTO, MODE_COOL: _FUEGO_MODE_COOL,
            MODE_DRY: _FUEGO_MODE_DRY, MODE_FAN: _FUEGO_MODE_FAN,
        }
        operating_mode = mode_map.get(mode, _FUEGO_MODE_HEAT)

        fan_map = {FAN_AUTO: _FUEGO_FAN_AUTO, FAN_1: _FUEGO_FAN1, FAN_2: _FUEGO_FAN2, FAN_3: _FUEGO_FAN3}
        fan_speed = fan_map.get(fan, _FUEGO_FAN_AUTO)

        if 17 < temp < 32:
            temperature = temp

        vs_map = {
            VDIR_AUTO: _FUEGO_VS_AUTO, VDIR_SWING: _FUEGO_VS_SWING,
            VDIR_UP: _FUEGO_VS_UP, VDIR_MUP: _FUEGO_VS_MUP,
            VDIR_MIDDLE: _FUEGO_VS_MIDDLE, VDIR_MDOWN: _FUEGO_VS_MDOWN, VDIR_DOWN: _FUEGO_VS_DOWN,
        }
        swing_vv = vs_map.get(swing_v, _FUEGO_VS_SWING)

        template = [0x23, 0xCB, 0x26, 0x01, 0x80, 0x20, 0x00, 0x00, 0x40, 0x00, 0x00, 0x00, 0x00, 0x00]
        return _build_fuego_template(power_mode, operating_mode, fan_speed, temperature, swing_vv,
                                      _FUEGO_HDR_MARK, _FUEGO_HDR_SPACE, _FUEGO_BIT_MARK,
                                      _FUEGO_ZERO_SPACE, _FUEGO_ONE_SPACE, template, True)


class AIRWAYHeatpumpIR(HeatpumpIRBase):
    model_id = "airway"
    display_name = "AIRWAY"
    min_temp = 18.0
    max_temp = 31.0
    fan_speeds = 3

    def get_command(self, power, mode, fan, temp, swing_v=VDIR_AUTO, swing_h=HDIR_AUTO) -> Command:
        power_mode = _AIRWAY_MODE_ON
        operating_mode = _AIRWAY_MODE_HEAT
        fan_speed = _AIRWAY_FAN_AUTO
        temperature = 23
        swing_vv = _AIRWAY_VS_SWING

        if power == POWER_OFF:
            power_mode = _AIRWAY_MODE_OFF
            swing_v = VDIR_MUP

        mode_map = {
            MODE_AUTO: _AIRWAY_MODE_AUTO, MODE_COOL: _AIRWAY_MODE_COOL,
            MODE_DRY: _AIRWAY_MODE_DRY, MODE_FAN: _AIRWAY_MODE_FAN,
        }
        operating_mode = mode_map.get(mode, _AIRWAY_MODE_HEAT)

        fan_map = {FAN_AUTO: _AIRWAY_FAN_AUTO, FAN_1: _AIRWAY_FAN1, FAN_2: _AIRWAY_FAN2, FAN_3: _AIRWAY_FAN3}
        fan_speed = fan_map.get(fan, _AIRWAY_FAN_AUTO)

        if 17 < temp < 32:
            temperature = temp

        vs_map = {
            VDIR_AUTO: _AIRWAY_VS_AUTO, VDIR_SWING: _AIRWAY_VS_SWING,
            VDIR_UP: _AIRWAY_VS_UP, VDIR_MUP: _AIRWAY_VS_MUP,
            VDIR_MIDDLE: _AIRWAY_VS_MIDDLE, VDIR_MDOWN: _AIRWAY_VS_MDOWN, VDIR_DOWN: _AIRWAY_VS_DOWN,
        }
        swing_vv = vs_map.get(swing_v, _AIRWAY_VS_SWING)

        buf = [0x23, 0xCB, 0x26, 0x01, 0x00, 0x20, 0x00, 0x00, 0x40, 0x00, 0x00, 0x00, 0x00, 0x00]
        buf[5] |= power_mode
        buf[6] |= operating_mode
        buf[7] |= 31 - temperature
        buf[8] |= fan_speed | swing_vv

        checksum = sum(buf[:13]) & 0xFF
        buf[13] = checksum

        ir = IRSenderCapture()
        ir.setFrequency(38)
        ir.mark(_AIRWAY_HDR_MARK)
        ir.space(_AIRWAY_HDR_SPACE)
        for b in buf:
            ir.sendIRbyte(b, _AIRWAY_BIT_MARK, _AIRWAY_ZERO_SPACE, _AIRWAY_ONE_SPACE)
        ir.mark(_AIRWAY_BIT_MARK)
        ir.space(0)
        return RawIRCommand.from_sender(ir)
