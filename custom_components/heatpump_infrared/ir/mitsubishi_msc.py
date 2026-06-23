"""Mitsubishi MSC and SEZ heatpump IR protocol implementations."""

from __future__ import annotations

from infrared_protocols.commands import Command

from .base import (
    FAN_1, FAN_2, FAN_3, FAN_AUTO, HDIR_AUTO, MODE_AUTO, MODE_COOL,
    MODE_DRY, MODE_FAN, MODE_HEAT, POWER_OFF, VDIR_AUTO, VDIR_DOWN,
    VDIR_MDOWN, VDIR_MIDDLE, VDIR_MUP, VDIR_SWING, VDIR_UP,
    HeatpumpIRBase, IRSenderCapture, RawIRCommand,
)

# Mitsubishi MSC timing
_MSC_HDR_MARK = 3060
_MSC_HDR_SPACE = 1580
_MSC_BIT_MARK = 350
_MSC_ONE_SPACE = 1150
_MSC_ZERO_SPACE = 390

_MSC_MODE_AUTO = 0x08
_MSC_MODE_HEAT = 0x01
_MSC_MODE_COOL = 0x03
_MSC_MODE_DRY = 0x02
_MSC_MODE_FAN = 0x07
_MSC_MODE_ON = 0x24
_MSC_MODE_OFF = 0x20

_MSC_FAN_AUTO = 0x00
_MSC_FAN1 = 0x02
_MSC_FAN2 = 0x03
_MSC_FAN3 = 0x05

_MSC_VS_AUTO = 0x00
_MSC_VS_UP = 0x08
_MSC_VS_MUP = 0x10
_MSC_VS_MIDDLE = 0x18
_MSC_VS_MDOWN = 0x20
_MSC_VS_DOWN = 0x28
_MSC_VS_SWING = 0x38

# Mitsubishi SEZ timing
_SEZ_HDR_MARK = 3060
_SEZ_HDR_SPACE = 1580
_SEZ_BIT_MARK = 350
_SEZ_ONE_SPACE = 1150
_SEZ_ZERO_SPACE = 390

_SEZ_MODE_AUTO = 0x03
_SEZ_MODE_HEAT = 0x02
_SEZ_MODE_COOL = 0x01
_SEZ_MODE_DRY = 0x05
_SEZ_MODE_FAN = 0x00
_SEZ_MODE_ON = 0x40
_SEZ_MODE_OFF = 0x00

_SEZ_FAN1 = 0x32
_SEZ_FAN2 = 0x34
_SEZ_FAN3 = 0x36


class MitsubishiMSCHeatpumpIR(HeatpumpIRBase):
    model_id = "mitsubishi_msc"
    display_name = "Mitsubishi MSC"
    min_temp = 17.0
    max_temp = 30.0
    fan_speeds = 3

    def get_command(self, power, mode, fan, temp, swing_v=VDIR_AUTO, swing_h=HDIR_AUTO) -> Command:
        power_mode = _MSC_MODE_ON
        operating_mode = _MSC_MODE_AUTO
        fan_speed = _MSC_FAN_AUTO
        temperature = 23
        swing_vv = _MSC_VS_AUTO

        if power == POWER_OFF:
            power_mode = _MSC_MODE_OFF

        mode_map = {
            MODE_AUTO: _MSC_MODE_AUTO, MODE_HEAT: _MSC_MODE_HEAT,
            MODE_COOL: _MSC_MODE_COOL, MODE_DRY: _MSC_MODE_DRY, MODE_FAN: _MSC_MODE_FAN,
        }
        operating_mode = mode_map.get(mode, _MSC_MODE_AUTO)

        fan_map = {FAN_AUTO: _MSC_FAN_AUTO, FAN_1: _MSC_FAN1, FAN_2: _MSC_FAN2, FAN_3: _MSC_FAN3}
        fan_speed = fan_map.get(fan, _MSC_FAN_AUTO)

        vs_map = {
            VDIR_SWING: _MSC_VS_SWING, VDIR_AUTO: _MSC_VS_AUTO, VDIR_UP: _MSC_VS_UP,
            VDIR_MUP: _MSC_VS_MUP, VDIR_MIDDLE: _MSC_VS_MIDDLE,
            VDIR_MDOWN: _MSC_VS_MDOWN, VDIR_DOWN: _MSC_VS_DOWN,
        }
        swing_vv = vs_map.get(swing_v, _MSC_VS_AUTO)

        if 15 < temp < 32:
            temperature = temp

        buf = [0x23, 0xCB, 0x26, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        buf[5] = power_mode
        buf[6] = operating_mode
        buf[7] = 31 - temperature
        buf[8] = fan_speed | swing_vv

        checksum = sum(buf) & 0xFF
        buf[13] = checksum

        ir = IRSenderCapture()
        ir.setFrequency(38)
        ir.mark(_MSC_HDR_MARK)
        ir.space(_MSC_HDR_SPACE)
        for b in buf:
            ir.sendIRbyte(b, _MSC_BIT_MARK, _MSC_ZERO_SPACE, _MSC_ONE_SPACE)
        ir.mark(_MSC_BIT_MARK)
        ir.space(0)
        return RawIRCommand.from_sender(ir)


class MitsubishiSEZHeatpumpIR(HeatpumpIRBase):
    model_id = "mitsubishi_sez"
    display_name = "Mitsubishi SEZ"
    min_temp = 17.0
    max_temp = 30.0
    fan_speeds = 3

    def get_command(self, power, mode, fan, temp, swing_v=VDIR_AUTO, swing_h=HDIR_AUTO) -> Command:
        power_mode = _SEZ_MODE_ON
        operating_mode = _SEZ_MODE_AUTO
        fan_speed = _SEZ_FAN1
        temperature = 23

        if power == POWER_OFF:
            power_mode = _SEZ_MODE_OFF

        mode_map = {
            MODE_AUTO: _SEZ_MODE_AUTO, MODE_HEAT: _SEZ_MODE_HEAT,
            MODE_COOL: _SEZ_MODE_COOL, MODE_DRY: _SEZ_MODE_DRY, MODE_FAN: _SEZ_MODE_FAN,
        }
        operating_mode = mode_map.get(mode, _SEZ_MODE_AUTO)

        fan_map = {FAN_AUTO: _SEZ_FAN1, FAN_1: _SEZ_FAN1, FAN_2: _SEZ_FAN2, FAN_3: _SEZ_FAN3}
        fan_speed = fan_map.get(fan, _SEZ_FAN1)

        if 16 < temp < 31:
            temperature = temp

        buf = [0x23, 0xCB, 0x26, 0x21, 0x00, 0x40, 0x00, 0x00, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        buf[5] = power_mode
        buf[6] = ((temperature - 16) << 4) | operating_mode
        buf[7] = fan_speed
        buf[11] = (~buf[5]) & 0xFF
        buf[12] = (~buf[6]) & 0xFF
        buf[13] = (~buf[7]) & 0xFF
        buf[14] = (~buf[8]) & 0xFF
        buf[15] = (~buf[9]) & 0xFF
        buf[16] = (~buf[10]) & 0xFF

        ir = IRSenderCapture()
        ir.setFrequency(38)
        ir.mark(_SEZ_HDR_MARK)
        ir.space(_SEZ_HDR_SPACE)
        for b in buf:
            ir.sendIRbyte(b, _SEZ_BIT_MARK, _SEZ_ZERO_SPACE, _SEZ_ONE_SPACE)
        ir.mark(_SEZ_BIT_MARK)
        ir.space(0)
        return RawIRCommand.from_sender(ir)
