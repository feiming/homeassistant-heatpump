"""Mitsubishi Heavy heatpump IR protocol implementations (ZJ, ZEA, ZM, FDTC)."""

from __future__ import annotations

from infrared_protocols.commands import Command

from .base import (
    FAN_1, FAN_2, FAN_3, FAN_4, FAN_AUTO, HDIR_AUTO, HDIR_LEFT, HDIR_MIDDLE,
    HDIR_MLEFT, HDIR_MRIGHT, HDIR_RIGHT, HDIR_SWING, MODE_AUTO, MODE_COOL,
    MODE_DRY, MODE_FAN, MODE_HEAT, POWER_OFF, VDIR_AUTO, VDIR_DOWN,
    VDIR_MDOWN, VDIR_MIDDLE, VDIR_MUP, VDIR_SWING, VDIR_UP,
    HeatpumpIRBase, IRSenderCapture, RawIRCommand,
)

_HDR_MARK = 3200
_HDR_SPACE = 1600
_BIT_MARK = 400
_ONE_SPACE = 1200
_ZERO_SPACE = 400

_MODE_AUTO = 0x07
_MODE_HEAT = 0x03
_MODE_COOL = 0x06
_MODE_DRY = 0x05
_MODE_FAN = 0x04
_MODE_OFF = 0x08
_MODE_ON = 0x00


class MitsubishiHeavyZJHeatpumpIR(HeatpumpIRBase):
    model_id = "mitsubishi_heavy_zj"
    display_name = "Mitsubishi Heavy ZJ"
    min_temp = 18.0
    max_temp = 30.0
    fan_speeds = 3

    def get_command(self, power, mode, fan, temp, swing_v=VDIR_AUTO, swing_h=HDIR_AUTO) -> Command:
        power_mode = _MODE_ON
        operating_mode = _MODE_HEAT
        temperature = 23
        clean_mode = 0x20  # ZJ_CLEAN_OFF

        fan_speeds = {
            FAN_AUTO: 0xE0, FAN_1: 0xA0, FAN_2: 0x80, FAN_3: 0x60,
            FAN_4: 0x40, 5: 0x00,
        }
        fan_speed = fan_speeds.get(fan, 0xE0)

        vs_map = {
            VDIR_SWING: 0x0A, VDIR_UP: 0x02, VDIR_MUP: 0x18,
            VDIR_MIDDLE: 0x10, VDIR_MDOWN: 0x08, VDIR_DOWN: 0x00,
        }
        hs_map = {
            HDIR_SWING: 0x4C, HDIR_MIDDLE: 0x48, HDIR_LEFT: 0xC8,
            HDIR_MLEFT: 0x88, HDIR_MRIGHT: 0x08, HDIR_RIGHT: 0xC4,
        }

        swing_vv = vs_map.get(swing_v, 0x1A)  # VS_STOP
        swing_hh = hs_map.get(swing_h, 0xCC)  # HS_STOP

        if power == POWER_OFF:
            power_mode = _MODE_OFF
        mode_map = {
            MODE_AUTO: _MODE_AUTO, MODE_HEAT: _MODE_HEAT,
            MODE_COOL: _MODE_COOL, MODE_DRY: _MODE_DRY, MODE_FAN: _MODE_FAN,
        }
        operating_mode = mode_map.get(mode, _MODE_HEAT)

        if 17 < temp < 31:
            temperature = ((~((temp - 17) << 4)) & 0xF0)

        buf = [0x52, 0xAE, 0xC3, 0x26, 0xD9, 0x11, 0x00, 0x07, 0x00, 0x00, 0x00]
        buf[5] |= swing_hh | (swing_vv & 0x02) | clean_mode
        buf[7] |= fan_speed | (swing_vv & 0x18)
        buf[9] |= operating_mode | power_mode | temperature
        buf[6] = (~buf[5]) & 0xFF
        buf[8] = (~buf[7]) & 0xFF
        buf[10] = (~buf[9]) & 0xFF

        ir = IRSenderCapture()
        ir.setFrequency(38)
        ir.mark(_HDR_MARK)
        ir.space(_HDR_SPACE)
        for b in buf:
            ir.sendIRbyte(b, _BIT_MARK, _ZERO_SPACE, _ONE_SPACE)
        ir.mark(_BIT_MARK)
        ir.space(0)
        return RawIRCommand.from_sender(ir)


class MitsubishiHeavyZEAHeatpumpIR(HeatpumpIRBase):
    model_id = "mitsubishi_heavy_zea"
    display_name = "Mitsubishi Heavy ZEA"
    min_temp = 18.0
    max_temp = 30.0
    fan_speeds = 4

    def get_command(self, power, mode, fan, temp, swing_v=VDIR_AUTO, swing_h=HDIR_AUTO) -> Command:
        power_mode = _MODE_ON
        operating_mode = _MODE_HEAT
        temperature = 23
        clean_mode = 0x08  # ZEA_CLEAN_OFF

        fan_speeds = {
            FAN_AUTO: 0xE0, FAN_1: 0xC2, FAN_2: 0xA4,
            FAN_3: 0x86, FAN_4: 0x68,
        }
        fan_speed = fan_speeds.get(fan, 0xE0)

        vs_map = {
            VDIR_SWING: 0x1A, VDIR_UP: 0x0E, VDIR_MUP: 0x31,
            VDIR_MIDDLE: 0x25, VDIR_MDOWN: 0x19, VDIR_DOWN: 0x0D,
        }
        hs_map = {
            HDIR_SWING: 0xD2, HDIR_MIDDLE: 0xA5, HDIR_LEFT: 0xC3,
            HDIR_MLEFT: 0xB4, HDIR_MRIGHT: 0x96, HDIR_RIGHT: 0x87,
        }

        swing_vv = vs_map.get(swing_v, 0x32)  # VS_STOP
        swing_hh = hs_map.get(swing_h, 0xF0)  # HS_STOP

        if power == POWER_OFF:
            power_mode = _MODE_OFF
        mode_map = {
            MODE_AUTO: _MODE_AUTO, MODE_HEAT: _MODE_HEAT,
            MODE_COOL: _MODE_COOL, MODE_DRY: _MODE_DRY, MODE_FAN: _MODE_FAN,
        }
        operating_mode = mode_map.get(mode, _MODE_HEAT)

        if 17 < temp < 31:
            temperature = ((~((temp - 17) << 4)) & 0xF0)

        buf = [0x52, 0xAE, 0xC3, 0x26, 0xD9, 0xDF, 0x20, 0x07, 0x00, 0x00, 0x00]
        buf[5] |= (swing_hh & 0xF0) | ((swing_vv >> 1) & 0x01) | clean_mode
        buf[6] |= ((swing_hh << 4) & 0xF0) | (swing_vv & 0x01)
        buf[7] |= (fan_speed & 0xE0) | ((swing_vv >> 1) & 0x18)
        buf[8] |= ((fan_speed << 4) & 0xE0) | ((swing_vv >> 1) & 0x18)
        buf[9] |= operating_mode | power_mode | temperature
        buf[6] = (~buf[5]) & 0xFF
        buf[8] = (~buf[7]) & 0xFF
        buf[10] = (~buf[9]) & 0xFF

        ir = IRSenderCapture()
        ir.setFrequency(38)
        ir.mark(_HDR_MARK)
        ir.space(_HDR_SPACE)
        for b in buf:
            ir.sendIRbyte(b, _BIT_MARK, _ZERO_SPACE, _ONE_SPACE)
        ir.mark(_BIT_MARK)
        ir.space(0)
        return RawIRCommand.from_sender(ir)


class MitsubishiHeavyZMHeatpumpIR(HeatpumpIRBase):
    model_id = "mitsubishi_heavy_zm"
    display_name = "Mitsubishi Heavy ZM"
    min_temp = 18.0
    max_temp = 30.0
    fan_speeds = 4

    def get_command(self, power, mode, fan, temp, swing_v=VDIR_AUTO, swing_h=HDIR_AUTO) -> Command:
        power_mode = _MODE_ON
        operating_mode = _MODE_HEAT
        temperature = 23
        clean_mode = 0x60  # ZM_CLEAN_OFF
        silent_mode = 0x80  # ZM_SILENT_OFF
        _3d_auto = 0x12  # ZM_3DAUTO_OFF

        fan_speeds = {
            FAN_AUTO: 0x0F, FAN_1: 0x0E, FAN_2: 0x0D,
            FAN_3: 0x0C, FAN_4: 0x0B,
        }
        fan_speed = fan_speeds.get(fan, 0x0F)

        vs_map = {
            VDIR_SWING: 0xE0, VDIR_UP: 0xC0, VDIR_MUP: 0xA0,
            VDIR_MIDDLE: 0x80, VDIR_MDOWN: 0x60, VDIR_DOWN: 0x40,
        }
        hs_map = {
            HDIR_SWING: 0x0F, HDIR_MIDDLE: 0x0C, HDIR_LEFT: 0x0E,
            HDIR_MLEFT: 0x0D, HDIR_MRIGHT: 0x0B, HDIR_RIGHT: 0x0A,
        }

        swing_vv = vs_map.get(swing_v, 0x20)  # VS_STOP
        swing_hh = hs_map.get(swing_h, 0x07)  # HS_STOP

        if power == POWER_OFF:
            power_mode = _MODE_OFF
        mode_map = {
            MODE_AUTO: _MODE_AUTO, MODE_HEAT: _MODE_HEAT,
            MODE_COOL: _MODE_COOL, MODE_DRY: _MODE_DRY, MODE_FAN: _MODE_FAN,
        }
        operating_mode = mode_map.get(mode, _MODE_HEAT)

        if 17 < temp < 31:
            temperature = ((~(temp - 17)) & 0x0F)

        buf = [0x52, 0xAE, 0xC3, 0x1A, 0xE5, 0x90, 0x00, 0xF0, 0x00,
               0xF0, 0x00, 0x0D, 0x00, 0x10, 0x00, 0xFF, 0x00, 0x7B, 0x00]

        buf[5] |= operating_mode | power_mode | clean_mode
        buf[7] |= temperature
        buf[9] |= fan_speed
        buf[11] |= swing_vv | _3d_auto
        buf[13] |= swing_hh | swing_vv
        buf[15] |= silent_mode

        buf[6] = (~buf[5]) & 0xFF
        buf[8] = (~buf[7]) & 0xFF
        buf[10] = (~buf[9]) & 0xFF
        buf[12] = (~buf[11]) & 0xFF
        buf[14] = (~buf[13]) & 0xFF
        buf[16] = (~buf[15]) & 0xFF
        buf[18] = (~buf[17]) & 0xFF

        ir = IRSenderCapture()
        ir.setFrequency(38)
        ir.mark(_HDR_MARK)
        ir.space(_HDR_SPACE)
        for b in buf:
            ir.sendIRbyte(b, _BIT_MARK, _ZERO_SPACE, _ONE_SPACE)
        ir.mark(_BIT_MARK)
        ir.space(0)
        return RawIRCommand.from_sender(ir)


class MitsubishiHeavyFDTCHeatpumpIR(HeatpumpIRBase):
    model_id = "mitsubishi_heavy_fdtc"
    display_name = "Mitsubishi Heavy FDTC"
    min_temp = 18.0
    max_temp = 30.0
    fan_speeds = 3

    _FDTC_HDR_MARK = 6000
    _FDTC_HDR_SPACE = 7500
    _FDTC_BIT_MARK = 500
    _FDTC_ONE_SPACE = 3500
    _FDTC_ZERO_SPACE = 1500

    def get_command(self, power, mode, fan, temp, swing_v=VDIR_AUTO, swing_h=HDIR_AUTO) -> Command:
        power_mode = 0x80  # ON
        operating_mode = 0x00  # AUTO
        fan_speed = 0x00  # FAN1
        temperature = 5  # = 21 - 16
        swing_vv = 0x00  # VS_UP

        if power == POWER_OFF:
            power_mode = 0x00

        mode_map = {
            MODE_AUTO: 0x00, MODE_HEAT: 0x40, MODE_COOL: 0x20,
            MODE_DRY: 0x10, MODE_FAN: 0x30,
        }
        operating_mode = mode_map.get(mode, 0x00)

        fan_map = {FAN_1: 0x00, FAN_2: 0x10, FAN_3: 0x20}
        fan_speed = fan_map.get(fan, 0x00)

        if 17 < temp < 31:
            temperature = (temp - 16) & 0x0F

        vs_map = {
            VDIR_SWING: 0x40, VDIR_UP: 0x00, VDIR_MUP: 0x10,
            VDIR_MIDDLE: 0x10, VDIR_MDOWN: 0x20, VDIR_DOWN: 0x30,
        }
        swing_vv = vs_map.get(swing_v, 0x00)

        buf = [0x0A, 0x00, 0x00, 0x40, 0xF4, 0xFF, 0xFF, 0xBF]
        buf[1] |= (swing_vv & 0x40) | fan_speed
        buf[2] |= operating_mode | power_mode | temperature
        buf[3] |= (swing_vv & 0x30)
        buf[4] = (~buf[0]) & 0xFF
        buf[5] = (~buf[1]) & 0xFF
        buf[6] = (~buf[2]) & 0xFF
        buf[7] = (~buf[3]) & 0xFF

        ir = IRSenderCapture()
        ir.setFrequency(38)
        ir.mark(self._FDTC_HDR_MARK)
        ir.space(self._FDTC_HDR_SPACE)
        for b in buf:
            ir.sendIRbyte(b, self._FDTC_BIT_MARK, self._FDTC_ZERO_SPACE, self._FDTC_ONE_SPACE)
        ir.mark(self._FDTC_BIT_MARK)
        ir.space(self._FDTC_HDR_SPACE)
        ir.mark(self._FDTC_BIT_MARK)
        ir.space(0)
        return RawIRCommand.from_sender(ir)
