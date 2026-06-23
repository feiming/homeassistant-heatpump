"""Sharp and IVT heatpump IR protocol implementations."""

from __future__ import annotations

from infrared_protocols.commands import Command

from .base import (
    FAN_1, FAN_2, FAN_3, FAN_AUTO, HDIR_AUTO, MODE_COOL, MODE_DRY,
    MODE_FAN, MODE_HEAT, POWER_OFF, VDIR_AUTO,
    HeatpumpIRBase, IRSenderCapture, RawIRCommand,
)

_HDR_MARK = 3540
_HDR_SPACE = 1720
_BIT_MARK = 460
_ONE_SPACE = 1400
_ZERO_SPACE = 430

_MODE_HEAT = 0x01
_MODE_COOL = 0x02
_MODE_DRY = 0x03
_MODE_OFF = 0x21
_MODE_ON_SHARP = 0x31
_MODE_ON_IVT = 0x11

_FAN_AUTO = 0x20
_FAN1 = 0x30
_FAN2 = 0x50
_FAN3 = 0x70


def _build_sharp(power_mode, operating_mode, fan_speed, temperature):
    buf = [0xAA, 0x5A, 0xCF, 0x10, 0x00, 0x00, 0x00, 0x06, 0x08, 0x80, 0x04, 0xF0, 0x01]

    buf[5] = power_mode
    buf[6] = fan_speed | operating_mode

    if temperature == 10:
        buf[4] = 0x00
    else:
        buf[4] = (temperature - 17) & 0xFF

    checksum = 0
    for i in range(12):
        checksum ^= buf[i]
    checksum ^= buf[12] & 0x0F
    checksum ^= (checksum >> 4)
    checksum &= 0x0F
    buf[12] |= (checksum << 4)

    return buf


class SharpHeatpumpIR(HeatpumpIRBase):
    model_id = "sharp"
    display_name = "Sharp AY-ZP40KR"
    min_temp = 18.0
    max_temp = 32.0
    fan_speeds = 3

    def _power_on_code(self):
        return _MODE_ON_SHARP

    def get_command(self, power, mode, fan, temp, swing_v=VDIR_AUTO, swing_h=HDIR_AUTO) -> Command:
        power_mode = self._power_on_code()
        operating_mode = _MODE_HEAT
        fan_speed = _FAN_AUTO
        temperature = 23

        if power == POWER_OFF:
            power_mode = _MODE_OFF

        if mode == MODE_HEAT:
            operating_mode = _MODE_HEAT
        elif mode == MODE_COOL:
            operating_mode = _MODE_COOL
        elif mode == MODE_DRY:
            operating_mode = _MODE_DRY
            temp = 10
        elif mode == MODE_FAN:
            operating_mode = _MODE_COOL
            temp = 32

        if fan == FAN_AUTO:
            fan_speed = _FAN_AUTO
        elif fan == FAN_1:
            fan_speed = _FAN1
        elif fan == FAN_2:
            fan_speed = _FAN2
        elif fan == FAN_3:
            fan_speed = _FAN3

        if 16 < temp < 32:
            temperature = temp

        buf = _build_sharp(power_mode, operating_mode, fan_speed, temperature)

        ir = IRSenderCapture()
        ir.setFrequency(38)
        ir.mark(_HDR_MARK)
        ir.space(_HDR_SPACE)
        for b in buf:
            ir.sendIRbyte(b, _BIT_MARK, _ZERO_SPACE, _ONE_SPACE)
        ir.mark(_BIT_MARK)
        ir.space(0)
        return RawIRCommand.from_sender(ir)


class IVTHeatpumpIR(SharpHeatpumpIR):
    model_id = "ivt"
    display_name = "IVT AY-XP12FR-N"

    def _power_on_code(self):
        return _MODE_ON_IVT
