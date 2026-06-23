"""Carrier heatpump IR protocol implementations (NQV and MCA)."""

from __future__ import annotations

from infrared_protocols.commands import Command

from .base import (
    FAN_1, FAN_2, FAN_3, FAN_4, FAN_5, FAN_AUTO, HDIR_AUTO, MODE_AUTO,
    MODE_COOL, MODE_DRY, MODE_FAN, MODE_HEAT, POWER_OFF, VDIR_AUTO,
    HeatpumpIRBase, IRSenderCapture, RawIRCommand,
)

# Carrier NQV timing
_NQV_HDR_MARK = 4320
_NQV_HDR_SPACE = 4350
_NQV_BIT_MARK = 500
_NQV_ONE_SPACE = 1650
_NQV_ZERO_SPACE = 550
_NQV_MSG_SPACE = 7400

_NQV_MODE_AUTO = 0x00
_NQV_MODE_HEAT = 0xC0
_NQV_MODE_COOL = 0x80
_NQV_MODE_DRY = 0x40
_NQV_MODE_FAN = 0x20
_NQV_MODE_OFF = 0xE0

_NQV_FAN_AUTO = 0x00
_NQV_FAN1 = 0x02
_NQV_FAN2 = 0x06
_NQV_FAN3 = 0x01
_NQV_FAN4 = 0x05
_NQV_FAN5 = 0x03

_NQV_TEMPERATURES = [0x00, 0x08, 0x04, 0x0c, 0x02, 0x0a, 0x06, 0x0e,
                     0x01, 0x09, 0x05, 0x0d, 0x03, 0x0b]

# Carrier MCA timing
_MCA_HDR_MARK = 4510
_MCA_HDR_SPACE = 4470
_MCA_BIT_MARK = 600
_MCA_ONE_SPACE = 1560
_MCA_ZERO_SPACE = 500

_MCA_MODE_AUTO = 0x10
_MCA_MODE_COOL = 0x00
_MCA_MODE_DRY = 0x20
_MCA_MODE_FAN_IR = 0x20
_MCA_MODE_HEAT = 0x30
_MCA_MODE_OFF = 0x00
_MCA_MODE_ON = 0x20

_MCA_FAN_DRY_AUTO = 0x00
_MCA_FAN1 = 0x01
_MCA_FAN2 = 0x02
_MCA_FAN3 = 0x04
_MCA_FAN_AUTO = 0x05
_MCA_FAN_OFF = 0x06

_MCA_TEMPERATURES = [0, 8, 12, 4, 6, 14, 10, 2, 3, 11, 9, 1, 5, 13, 7]


class CarrierNQVHeatpumpIR(HeatpumpIRBase):
    model_id = "carrier_nqv"
    display_name = "Carrier NQV"
    min_temp = 17.0
    max_temp = 30.0
    fan_speeds = 5

    def get_command(self, power, mode, fan, temp, swing_v=VDIR_AUTO, swing_h=HDIR_AUTO) -> Command:
        operating_mode = _NQV_MODE_HEAT
        fan_speed = _NQV_FAN_AUTO
        temperature = 23

        if power == POWER_OFF:
            operating_mode = _NQV_MODE_OFF
        else:
            if mode == MODE_AUTO:
                operating_mode = _NQV_MODE_AUTO
            elif mode == MODE_HEAT:
                operating_mode = _NQV_MODE_HEAT
            elif mode == MODE_COOL:
                operating_mode = _NQV_MODE_COOL
            elif mode == MODE_DRY:
                operating_mode = _NQV_MODE_DRY
                fan = FAN_AUTO
            elif mode == MODE_FAN:
                operating_mode = _NQV_MODE_FAN
                temp = 22

        if fan == FAN_AUTO:
            fan_speed = _NQV_FAN_AUTO
        elif fan == FAN_1:
            fan_speed = _NQV_FAN1
        elif fan == FAN_2:
            fan_speed = _NQV_FAN2
        elif fan == FAN_3:
            fan_speed = _NQV_FAN3
        elif fan == FAN_4:
            fan_speed = _NQV_FAN4
        elif fan == FAN_5:
            fan_speed = _NQV_FAN5

        if 16 < temp < 31:
            temperature = temp

        buf = [0x4F, 0xB0, 0xC0, 0x3F, 0x80, 0x00, 0x00, 0x00, 0x00]
        buf[5] = _NQV_TEMPERATURES[temperature - 17]
        buf[6] = operating_mode | fan_speed

        checksum = 0
        for i in range(8):
            checksum += IRSenderCapture.bit_reverse(buf[i])

        # Mode-dependent checksum corrections
        mode_nibble = buf[6] & 0xF0
        fan_nibble = buf[6] & 0x0F
        if mode_nibble == 0x00:  # AUTO
            checksum += 0x02
            if fan_nibble in (0x02, 0x03, 0x06):
                checksum += 0x80
        elif mode_nibble == 0x40:  # DRY
            checksum += 0x02
        elif mode_nibble == 0xC0:  # HEAT
            if fan_nibble in (0x05, 0x06):
                checksum += 0xC0
        elif mode_nibble == 0x20:  # FAN
            checksum += 0x02
            if fan_nibble in (0x02, 0x03, 0x06):
                checksum += 0x80

        buf[8] = IRSenderCapture.bit_reverse(checksum & 0xFF)

        ir = IRSenderCapture()
        ir.setFrequency(38)
        ir.mark(_NQV_HDR_MARK)
        ir.space(_NQV_HDR_SPACE)
        for b in buf:
            ir.sendIRbyte(b, _NQV_BIT_MARK, _NQV_ZERO_SPACE, _NQV_ONE_SPACE)
        ir.mark(_NQV_BIT_MARK)
        ir.space(_NQV_MSG_SPACE)
        ir.mark(_NQV_HDR_MARK)
        ir.space(_NQV_HDR_SPACE)
        for b in buf:
            ir.sendIRbyte(b, _NQV_BIT_MARK, _NQV_ZERO_SPACE, _NQV_ONE_SPACE)
        ir.mark(_NQV_BIT_MARK)
        ir.space(0)
        return RawIRCommand.from_sender(ir)


class CarrierMCAHeatpumpIR(HeatpumpIRBase):
    model_id = "carrier_mca"
    display_name = "Carrier MCA"
    min_temp = 17.0
    max_temp = 30.0
    fan_speeds = 3

    def get_command(self, power, mode, fan, temp, swing_v=VDIR_AUTO, swing_h=HDIR_AUTO) -> Command:
        power_mode = _MCA_MODE_ON
        operating_mode = _MCA_MODE_COOL
        fan_speed = _MCA_FAN_AUTO
        temperature = 23

        if power == POWER_OFF:
            power_mode = _MCA_MODE_OFF
            operating_mode = _MCA_MODE_COOL
            fan_speed = _MCA_FAN_OFF
            temperature = 31
        else:
            if mode == MODE_AUTO:
                operating_mode = _MCA_MODE_AUTO
                fan_speed = _MCA_FAN_DRY_AUTO
            elif mode == MODE_COOL:
                operating_mode = _MCA_MODE_COOL
            elif mode == MODE_HEAT:
                operating_mode = _MCA_MODE_HEAT
            elif mode == MODE_DRY:
                operating_mode = _MCA_MODE_DRY
                fan_speed = _MCA_FAN_DRY_AUTO
            elif mode == MODE_FAN:
                operating_mode = _MCA_MODE_FAN_IR
                temp = 31

            if mode not in (MODE_AUTO, MODE_DRY):
                if fan == FAN_AUTO:
                    fan_speed = _MCA_FAN_AUTO
                elif fan == FAN_1:
                    fan_speed = _MCA_FAN1
                elif fan == FAN_2:
                    fan_speed = _MCA_FAN2
                elif fan == FAN_3:
                    fan_speed = _MCA_FAN3

            if 16 < temp < 31 and mode != MODE_FAN:
                temperature = temp

        buf = [0x4D, 0xB2, 0xD8, 0x00, 0x00, 0x00]
        buf[2] |= power_mode | fan_speed
        buf[4] |= operating_mode | _MCA_TEMPERATURES[temperature - 17]
        buf[3] = (~buf[2]) & 0xFF
        buf[5] = (~buf[4]) & 0xFF

        ir = IRSenderCapture()
        ir.setFrequency(38)
        ir.mark(_MCA_HDR_MARK)
        ir.space(_MCA_HDR_SPACE)
        for b in buf:
            ir.sendIRbyte(b, _MCA_BIT_MARK, _MCA_ZERO_SPACE, _MCA_ONE_SPACE)
        ir.mark(_MCA_BIT_MARK)
        ir.space(_MCA_HDR_SPACE)
        ir.mark(_MCA_HDR_MARK)
        ir.space(_MCA_HDR_SPACE)
        for b in buf:
            ir.sendIRbyte(b, _MCA_BIT_MARK, _MCA_ZERO_SPACE, _MCA_ONE_SPACE)
        ir.mark(_MCA_BIT_MARK)
        ir.space(0)
        return RawIRCommand.from_sender(ir)
