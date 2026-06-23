"""Gree heatpump IR protocol implementations."""

from __future__ import annotations

from infrared_protocols.commands import Command

from .base import (
    FAN_1, FAN_2, FAN_3, FAN_AUTO, HDIR_AUTO, HDIR_LEFT, HDIR_MIDDLE,
    HDIR_MLEFT, HDIR_MRIGHT, HDIR_RIGHT, HDIR_SWING, MODE_AUTO, MODE_COOL,
    MODE_DRY, MODE_FAN, MODE_HEAT, POWER_OFF, VDIR_AUTO, VDIR_DOWN,
    VDIR_MDOWN, VDIR_MIDDLE, VDIR_MUP, VDIR_SWING, VDIR_UP,
    HeatpumpIRBase, IRSenderCapture, RawIRCommand,
)

_HDR_MARK = 9000
_HDR_SPACE = 4000
_BIT_MARK = 620
_ONE_SPACE = 1600
_ZERO_SPACE = 540
_MSG_SPACE = 19000

_POWER_OFF = 0x00
_POWER_ON = 0x08

_MODE_AUTO = 0x00
_MODE_COOL = 0x01
_MODE_DRY = 0x02
_MODE_FAN = 0x03
_MODE_HEAT = 0x04

_FAN_AUTO = 0x00
_FAN1 = 0x10
_FAN2 = 0x20
_FAN3 = 0x30

_VSWING_BIT = (1 << 6)
_VDIR_SWING = 0x01
_VDIR_UP = 0x02
_VDIR_MUP = 0x03
_VDIR_MIDDLE = 0x04
_VDIR_MDOWN = 0x05
_VDIR_DOWN = 0x06

_HDIR_AUTO = 0x00
_HDIR_SWING = 0x01
_HDIR_LEFT = 0x02
_HDIR_MLEFT = 0x03
_HDIR_MIDDLE = 0x04
_HDIR_MRIGHT = 0x05
_HDIR_RIGHT = 0x06

_TURBO_BIT = (1 << 4)
_LIGHT_BIT = (1 << 5)
_HEALTH_BIT = (1 << 6)
_IFEEL_BIT = 0x08


def _convert_params(power, mode, fan, temp, swing_v, swing_h):
    power_mode = _POWER_ON
    operating_mode = _MODE_HEAT
    fan_speed = _FAN_AUTO
    temperature = 21
    swing_vv = 0
    swing_hh = 0

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

    if fan == FAN_AUTO:
        fan_speed = _FAN_AUTO
    elif fan == FAN_1:
        fan_speed = _FAN1
    elif fan == FAN_2:
        fan_speed = _FAN2
    elif fan == FAN_3:
        fan_speed = _FAN3

    if swing_v == VDIR_SWING:
        swing_vv = _VDIR_SWING
    elif swing_v == VDIR_UP:
        swing_vv = _VDIR_UP
    elif swing_v == VDIR_MUP:
        swing_vv = _VDIR_MUP
    elif swing_v == VDIR_MIDDLE:
        swing_vv = _VDIR_MIDDLE
    elif swing_v == VDIR_MDOWN:
        swing_vv = _VDIR_MDOWN
    elif swing_v == VDIR_DOWN:
        swing_vv = _VDIR_DOWN

    if swing_h == HDIR_SWING:
        swing_hh = _HDIR_SWING
    elif swing_h == HDIR_LEFT:
        swing_hh = _HDIR_LEFT
    elif swing_h == HDIR_MLEFT:
        swing_hh = _HDIR_MLEFT
    elif swing_h == HDIR_MIDDLE:
        swing_hh = _HDIR_MIDDLE
    elif swing_h == HDIR_MRIGHT:
        swing_hh = _HDIR_MRIGHT
    elif swing_h == HDIR_RIGHT:
        swing_hh = _HDIR_RIGHT

    if 15 < temp < 31:
        temperature = temp - 16

    return power_mode, operating_mode, fan_speed, temperature, swing_vv, swing_hh


def _calc_checksum(buf):
    buf[8] = (((
        (buf[0] & 0x0F) +
        (buf[1] & 0x0F) +
        (buf[2] & 0x0F) +
        (buf[3] & 0x0F) +
        ((buf[5] & 0xF0) >> 4) +
        ((buf[6] & 0xF0) >> 4) +
        ((buf[7] & 0xF0) >> 4) +
        0x0A) & 0x0F) << 4) | (buf[7] & 0x0F)


def _send_buffer(ir: IRSenderCapture, buf: list[int], length: int = 8) -> None:
    ir.setFrequency(38)
    for pos in range(0, length, 8):
        if pos:
            ir.mark(_BIT_MARK)
            ir.space(_MSG_SPACE)
        ir.mark(_HDR_MARK)
        ir.space(_HDR_SPACE)
        for i in range(4):
            ir.sendIRbyte(buf[pos + i], _BIT_MARK, _ZERO_SPACE, _ONE_SPACE)
        ir.mark(_BIT_MARK)
        ir.space(_ZERO_SPACE)
        ir.mark(_BIT_MARK)
        ir.space(_ONE_SPACE)
        ir.mark(_BIT_MARK)
        ir.space(_ZERO_SPACE)
        ir.mark(_BIT_MARK)
        ir.space(_MSG_SPACE)
        for i in range(5, 9):
            ir.sendIRbyte(buf[pos + i], _BIT_MARK, _ZERO_SPACE, _ONE_SPACE)
        ir.mark(_BIT_MARK)
        ir.space(0)


class GreeGenericHeatpumpIR(HeatpumpIRBase):
    model_id = "gree_generic"
    display_name = "Gree"
    min_temp = 16.0
    max_temp = 30.0
    fan_speeds = 3

    def get_command(self, power, mode, fan, temp, swing_v=VDIR_AUTO, swing_h=HDIR_AUTO) -> Command:
        pm, om, fs, temperature, sv, sh = _convert_params(power, mode, fan, temp, swing_v, swing_h)
        buf = [0] * 9
        buf[0] = fs | om | pm
        buf[1] = temperature
        _calc_checksum(buf)
        ir = IRSenderCapture()
        _send_buffer(ir, buf)
        return RawIRCommand.from_sender(ir)


class GreeYANHeatpumpIR(HeatpumpIRBase):
    model_id = "gree_yan"
    display_name = "Gree YAN"
    min_temp = 16.0
    max_temp = 30.0
    fan_speeds = 3

    def get_command(self, power, mode, fan, temp, swing_v=VDIR_AUTO, swing_h=HDIR_AUTO) -> Command:
        pm, om, fs, temperature, sv, sh = _convert_params(power, mode, fan, temp, swing_v, swing_h)
        buf = [0] * 9
        buf[0] = fs | om | pm
        buf[1] = temperature
        buf[2] = 0x60
        buf[3] = 0x50
        if sv == _VDIR_SWING:
            sv = 0
        buf[4] = sv
        buf[5] |= 0x20
        # YAN checksum
        buf[8] = ((buf[0] << 4) + (buf[1] << 4) + 0xC0) & 0xFF
        ir = IRSenderCapture()
        _send_buffer(ir, buf)
        return RawIRCommand.from_sender(ir)


class GreeYAAHeatpumpIR(HeatpumpIRBase):
    model_id = "gree_yaa"
    display_name = "Gree YAA"
    min_temp = 16.0
    max_temp = 30.0
    fan_speeds = 3

    def get_command(self, power, mode, fan, temp, swing_v=VDIR_AUTO, swing_h=HDIR_AUTO) -> Command:
        pm, om, fs, temperature, sv, sh = _convert_params(power, mode, fan, temp, swing_v, swing_h)
        buf = [0] * 9
        buf[0] = fs | om | pm
        buf[1] = temperature
        buf[2] = _LIGHT_BIT
        buf[3] = 0x50
        buf[5] |= 0x20
        buf[6] = 0x20
        if sv == _VDIR_SWING:
            buf[0] |= _VSWING_BIT
        elif sv != 0:
            buf[5] = sv
        _calc_checksum(buf)
        ir = IRSenderCapture()
        _send_buffer(ir, buf)
        return RawIRCommand.from_sender(ir)


class GreeYACHeatpumpIR(HeatpumpIRBase):
    model_id = "gree_yac"
    display_name = "Gree YAC"
    min_temp = 16.0
    max_temp = 30.0
    fan_speeds = 3

    def get_command(self, power, mode, fan, temp, swing_v=VDIR_AUTO, swing_h=HDIR_AUTO) -> Command:
        pm, om, fs, temperature, sv, sh = _convert_params(power, mode, fan, temp, swing_v, swing_h)
        buf = [0] * 9
        buf[0] = fs | om | pm
        buf[1] = temperature
        buf[2] = _LIGHT_BIT
        buf[3] = 0x50
        buf[5] |= 0x20
        buf[6] = 0x20
        if sh == _HDIR_AUTO:
            sh = _HDIR_SWING
        buf[4] |= (sh << 4)
        if sv == _VDIR_SWING:
            buf[0] |= _VSWING_BIT
        elif sv != 0:
            buf[5] = sv
        _calc_checksum(buf)
        ir = IRSenderCapture()
        _send_buffer(ir, buf)
        return RawIRCommand.from_sender(ir)


class GreeYTHeatpumpIR(HeatpumpIRBase):
    model_id = "gree_yt"
    display_name = "Gree YT"
    min_temp = 16.0
    max_temp = 30.0
    fan_speeds = 3

    def get_command(self, power, mode, fan, temp, swing_v=VDIR_AUTO, swing_h=HDIR_AUTO) -> Command:
        pm, om, fs, temperature, sv, sh = _convert_params(power, mode, fan, temp, swing_v, swing_h)
        buf = [0] * 9
        buf[0] = fs | om | pm
        buf[1] = temperature
        buf[2] = _LIGHT_BIT | _HEALTH_BIT
        buf[3] = 0x50
        if sv == _VDIR_SWING:
            buf[0] |= _VSWING_BIT
            buf[4] = sv
        _calc_checksum(buf)
        ir = IRSenderCapture()
        _send_buffer(ir, buf)
        return RawIRCommand.from_sender(ir)
