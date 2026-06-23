"""Toshiba heatpump IR protocol implementations."""

from __future__ import annotations

from infrared_protocols.commands import Command

from .base import (
    FAN_1, FAN_2, FAN_3, FAN_4, FAN_5, FAN_AUTO, HDIR_AUTO, MODE_AUTO,
    MODE_COOL, MODE_DRY, MODE_FAN, MODE_HEAT, POWER_OFF, VDIR_AUTO,
    HeatpumpIRBase, IRSenderCapture, RawIRCommand,
)

# Toshiba timing
_HDR_MARK = 4400
_HDR_SPACE = 4400
_BIT_MARK = 550
_ONE_SPACE = 1600
_ZERO_SPACE = 550

_MODE_AUTO = 0x00
_MODE_HEAT = 0xC0
_MODE_COOL = 0x80
_MODE_DRY = 0x40
_MODE_OFF = 0xE0

_FAN_AUTO = 0x00
_FAN1 = 0x02
_FAN2 = 0x06
_FAN3 = 0x01
_FAN4 = 0x05
_FAN5 = 0x03

# Daiseikai timing
_DAISEIKAI_HDR_MARK = 4320
_DAISEIKAI_HDR_SPACE = 4350
_DAISEIKAI_BIT_MARK = 550
_DAISEIKAI_ONE_SPACE = 1650
_DAISEIKAI_ZERO_SPACE = 485
_DAISEIKAI_MSG_SPACE = 7900

_DAISEIKAI_MODE_AUTO = 0x00
_DAISEIKAI_MODE_HEAT = 0xC0
_DAISEIKAI_MODE_COOL = 0x80
_DAISEIKAI_MODE_DRY = 0x40
_DAISEIKAI_MODE_FAN = 0x20
_DAISEIKAI_MODE_OFF = 0xE0

_DAISEIKAI_FAN_AUTO = 0x00
_DAISEIKAI_FAN1 = 0x02
_DAISEIKAI_FAN2 = 0x06
_DAISEIKAI_FAN3 = 0x01
_DAISEIKAI_FAN4 = 0x05
_DAISEIKAI_FAN5 = 0x03

_DAISEIKAI_TEMPERATURES = [0x00, 0x08, 0x04, 0x0c, 0x02, 0x0a, 0x06, 0x0e,
                            0x01, 0x09, 0x05, 0x0d, 0x03, 0x0b]


class ToshibaHeatpumpIR(HeatpumpIRBase):
    model_id = "toshiba"
    display_name = "Toshiba"
    min_temp = 17.0
    max_temp = 30.0
    fan_speeds = 5

    def get_command(self, power, mode, fan, temp, swing_v=VDIR_AUTO, swing_h=HDIR_AUTO) -> Command:
        operating_mode = _MODE_HEAT
        fan_speed = _FAN_AUTO
        temperature = 23

        if power == POWER_OFF:
            operating_mode = _MODE_OFF
        else:
            if mode == MODE_AUTO:
                operating_mode = _MODE_AUTO
            elif mode == MODE_COOL:
                operating_mode = _MODE_COOL
            elif mode == MODE_DRY:
                operating_mode = _MODE_DRY
            elif mode == MODE_FAN:
                operating_mode = _MODE_COOL
                temp = 30

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
        elif fan == FAN_5:
            fan_speed = _FAN5

        if 16 < temp < 31:
            temperature = temp

        buf = [0x4F, 0xB0, 0xC0, 0x3F, 0x80, 0x00, 0x00, 0x00, 0x00]
        buf[6] |= operating_mode | fan_speed
        buf[5] |= IRSenderCapture.bit_reverse(temperature - 17) >> 4

        checksum = 0
        for i in range(8):
            checksum ^= buf[i]
        buf[8] = checksum

        ir = IRSenderCapture()
        ir.setFrequency(38)
        ir.mark(_HDR_MARK)
        ir.space(_HDR_SPACE)
        for b in buf:
            ir.sendIRbyte(b, _BIT_MARK, _ZERO_SPACE, _ONE_SPACE)
        ir.mark(_BIT_MARK)
        ir.space(0)
        return RawIRCommand.from_sender(ir)


class ToshibaDaiseikaiHeatpumpIR(HeatpumpIRBase):
    model_id = "toshiba_daiseikai"
    display_name = "Toshiba Daiseikai"
    min_temp = 17.0
    max_temp = 30.0
    fan_speeds = 5

    def get_command(self, power, mode, fan, temp, swing_v=VDIR_AUTO, swing_h=HDIR_AUTO) -> Command:
        operating_mode = _DAISEIKAI_MODE_HEAT
        fan_speed = _DAISEIKAI_FAN_AUTO
        temperature = 23

        if power == POWER_OFF:
            operating_mode = _DAISEIKAI_MODE_OFF
        else:
            if mode == MODE_AUTO:
                operating_mode = _DAISEIKAI_MODE_AUTO
            elif mode == MODE_HEAT:
                operating_mode = _DAISEIKAI_MODE_HEAT
            elif mode == MODE_COOL:
                operating_mode = _DAISEIKAI_MODE_COOL
            elif mode == MODE_DRY:
                operating_mode = _DAISEIKAI_MODE_DRY
                fan = FAN_AUTO
            elif mode == MODE_FAN:
                operating_mode = _DAISEIKAI_MODE_FAN
                temp = 22

        if fan == FAN_AUTO:
            fan_speed = _DAISEIKAI_FAN_AUTO
        elif fan == FAN_1:
            fan_speed = _DAISEIKAI_FAN1
        elif fan == FAN_2:
            fan_speed = _DAISEIKAI_FAN2
        elif fan == FAN_3:
            fan_speed = _DAISEIKAI_FAN3
        elif fan == FAN_4:
            fan_speed = _DAISEIKAI_FAN4
        elif fan == FAN_5:
            fan_speed = _DAISEIKAI_FAN5

        if 16 < temp < 31:
            temperature = temp

        buf = [0x4F, 0xB0, 0xC0, 0x3F, 0x80, 0x00, 0x00, 0x00, 0x00]
        buf[5] = _DAISEIKAI_TEMPERATURES[temperature - 17]
        buf[6] = operating_mode | fan_speed

        checksum = 0
        for i in range(8):
            checksum ^= IRSenderCapture.bit_reverse(buf[i])
        buf[8] = IRSenderCapture.bit_reverse(checksum)

        ir = IRSenderCapture()
        ir.setFrequency(38)
        ir.mark(_DAISEIKAI_HDR_MARK)
        ir.space(_DAISEIKAI_HDR_SPACE)
        for b in buf:
            ir.sendIRbyte(b, _DAISEIKAI_BIT_MARK, _DAISEIKAI_ZERO_SPACE, _DAISEIKAI_ONE_SPACE)
        ir.mark(_DAISEIKAI_BIT_MARK)
        ir.space(_DAISEIKAI_MSG_SPACE)
        ir.mark(_DAISEIKAI_HDR_MARK)
        ir.space(_DAISEIKAI_HDR_SPACE)
        for b in buf:
            ir.sendIRbyte(b, _DAISEIKAI_BIT_MARK, _DAISEIKAI_ZERO_SPACE, _DAISEIKAI_ONE_SPACE)
        ir.mark(_DAISEIKAI_BIT_MARK)
        ir.space(0)
        return RawIRCommand.from_sender(ir)
