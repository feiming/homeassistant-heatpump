"""Daikin heatpump IR protocol implementation.

Ported from DaikinHeatpumpIR.cpp (arduino-heatpumpir).
Covers the standard Daikin ARC433B50 remote protocol.
"""

from __future__ import annotations

from infrared_protocols.commands import Command

from .base import (
    FAN_1,
    FAN_2,
    FAN_3,
    FAN_4,
    FAN_5,
    FAN_AUTO,
    HDIR_AUTO,
    POWER_OFF,
    POWER_ON,
    VDIR_AUTO,
    HeatpumpIRBase,
    IRSenderCapture,
    MODE_AUTO,
    MODE_COOL,
    MODE_DRY,
    MODE_FAN,
    MODE_HEAT,
    RawIRCommand,
)

# Timing constants
_HDR_MARK = 3360
_HDR_SPACE = 1760
_BIT_MARK = 360
_ONE_SPACE = 1370
_ZERO_SPACE = 520
_MSG_SPACE = 32300

# Operating mode codes
_MODE_AUTO = 0x00
_MODE_HEAT = 0x40
_MODE_COOL = 0x30
_MODE_DRY = 0x20
_MODE_FAN_ONLY = 0x60
_MODE_OFF = 0x00
_MODE_ON = 0x01

# Fan speed codes
_FAN_AUTO = 0xA0
_FAN1 = 0x30
_FAN2 = 0x40
_FAN3 = 0x50
_FAN4 = 0x60
_FAN5 = 0x70


class DaikinHeatpumpIR(HeatpumpIRBase):
    """Daikin standard protocol (ARC433B50 remote)."""

    model_id = "daikin"
    display_name = "Daikin"
    min_temp = 18.0
    max_temp = 30.0
    fan_speeds = 5

    def get_command(
        self,
        power: int,
        mode: int,
        fan: int,
        temp: int,
        swing_v: int = VDIR_AUTO,
        swing_h: int = HDIR_AUTO,
    ) -> Command:
        op_mode = _MODE_OFF | _MODE_AUTO
        fan_speed = _FAN_AUTO
        temperature = 23

        if power == POWER_ON:
            op_mode |= _MODE_ON

        if mode == MODE_AUTO:
            op_mode |= _MODE_AUTO
        elif mode == MODE_HEAT:
            op_mode |= _MODE_HEAT
        elif mode == MODE_COOL:
            op_mode |= _MODE_COOL
        elif mode == MODE_DRY:
            op_mode |= _MODE_DRY
            temp = 0x24
        elif mode == MODE_FAN:
            op_mode |= _MODE_FAN_ONLY
            temp = 0xC0

        fan_speed = {
            FAN_AUTO: _FAN_AUTO,
            FAN_1: _FAN1,
            FAN_2: _FAN2,
            FAN_3: _FAN3,
            FAN_4: _FAN4,
            FAN_5: _FAN5,
        }.get(fan, _FAN_AUTO)

        if mode == MODE_HEAT and 10 <= temp <= 30:
            temperature = temp << 1
        elif 18 <= temp <= 30:
            temperature = temp << 1

        return _send_daikin(op_mode, fan_speed, temperature)


def _send_daikin(op_mode: int, fan_speed: int, temperature: int) -> RawIRCommand:
    """Build the Daikin 35-byte IR signal."""
    template = bytearray(
        [
            # First 8-byte header frame
            0x11, 0xDA, 0x27, 0x00, 0xC5, 0x00, 0x00, 0xD7,
            # Second 8-byte header frame (fixed)
            0x11, 0xDA, 0x27, 0x00, 0x42, 0x49, 0x05, 0xA2,
            # 19-byte payload frame
            0x11, 0xDA, 0x27, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x06, 0x60, 0x00, 0x00, 0xC0,
            0x00, 0x00, 0x00,
        ]
    )

    template[21] = op_mode
    template[22] = temperature
    template[24] = fan_speed

    checksum = sum(template[16:34]) & 0xFF
    template[34] = checksum

    ir = IRSenderCapture()
    ir.setFrequency(38)

    # Header
    ir.mark(_HDR_MARK)
    ir.space(_HDR_SPACE)

    for i in range(8):
        ir.sendIRbyte(template[i], _BIT_MARK, _ZERO_SPACE, _ONE_SPACE)

    ir.mark(_BIT_MARK)
    ir.space(_MSG_SPACE)
    ir.mark(_HDR_MARK)
    ir.space(_HDR_SPACE)

    for i in range(8, 16):
        ir.sendIRbyte(template[i], _BIT_MARK, _ZERO_SPACE, _ONE_SPACE)

    ir.mark(_BIT_MARK)
    ir.space(_MSG_SPACE)
    ir.mark(_HDR_MARK)
    ir.space(_HDR_SPACE)

    for i in range(16, 35):
        ir.sendIRbyte(template[i], _BIT_MARK, _ZERO_SPACE, _ONE_SPACE)

    ir.mark(_BIT_MARK)
    ir.space(0)

    return RawIRCommand.from_sender(ir)
