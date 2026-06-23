"""Samsung heatpump IR protocol implementations.

Ported from SamsungHeatpumpIR.cpp (arduino-heatpumpir).
Covers models: AQV (AQV12PSBN / AQV09ASA), FJM (RJ040F2HXEA).
"""

from __future__ import annotations

from infrared_protocols.commands import Command

from .base import (
    FAN_1,
    FAN_2,
    FAN_3,
    FAN_4,
    FAN_AUTO,
    HDIR_AUTO,
    HDIR_SWING,
    POWER_OFF,
    POWER_ON,
    VDIR_AUTO,
    VDIR_SWING,
    HeatpumpIRBase,
    IRSenderCapture,
    MODE_AUTO,
    MODE_COOL,
    MODE_DRY,
    MODE_FAN,
    MODE_HEAT,
    RawIRCommand,
)

# AQV timing constants
_AQV_HDR_MARK = 3000
_AQV_HDR_SPACE = 9000
_AQV_BIT_MARK = 500
_AQV_ONE_SPACE = 1500
_AQV_ZERO_SPACE = 500
_AQV_MSG_SPACE = 2000

# FJM timing constants
_FJM_HDR_MARK = 2920
_FJM_HDR_SPACE = 8960
_FJM_BIT_MARK = 490
_FJM_ONE_SPACE = 1560
_FJM_ZERO_SPACE = 546

# AQV operating mode codes
_AQV_MODE_AUTO = 0x00
_AQV_MODE_HEAT = 0x40
_AQV_MODE_COOL = 0x10
_AQV_MODE_DRY = 0x20
_AQV_MODE_FAN = 0x30
_AQV_MODE_OFF = 0xC0
_AQV_MODE_ON = 0xF0

# AQV fan speed codes
_AQV_FAN_AUTO = 0x01
_AQV_FAN1 = 0x05
_AQV_FAN2 = 0x09
_AQV_FAN3 = 0x0B

# AQV swing codes
_AQV_VS_SWING = 0xAE
_AQV_VS_AUTO = 0xFE
_AQV_HS_SWING = 0xB0
_AQV_VHS_SWING = 0xC0
_AQV_VHS_OFF = 0xF0

# FJM additional
_FJM_FAN4 = 0x0F
_FJM_VS_SWING = 0xA0
_FJM_TURBO = 0x06

# FJM fixed header bytes (PROGMEM in C++)
_FJM_HEADER = bytes([0x02, 0x92, 0x0F, 0x00, 0x00, 0x00, 0xF0])
_FJM_OFF_CODE = bytes(
    [
        0x02, 0xB2, 0x0F, 0x00, 0x00, 0x00, 0xC0,
        0x01, 0x72, 0x0F, 0x00, 0x90, 0xD0, 0x01,
        0x01, 0x02, 0xFF, 0x01, 0x60, 0x4B, 0xC0,
    ]
)


def _aqv_fill_checksum(chunk: bytearray) -> None:
    """Compute and fill the Samsung AQV checksum in-place."""
    chunk[1] &= 0x0F
    chunk[2] &= 0xF0
    total = 0
    for j in range(7):
        b = chunk[j]
        for _ in range(8):
            if b & 0x01:
                total += 1
            b >>= 1
    total = (~total) & 0xFF
    chunk[1] |= (total & 0x0F) << 4
    chunk[2] |= (total & 0xF0) >> 4


class SamsungAQVHeatpumpIR(HeatpumpIRBase):
    """Samsung AQV12PSBN / AQV09ASA series."""

    model_id = "samsung_aqv"
    display_name = "Samsung AQV"
    min_temp = 16.0
    max_temp = 27.0
    fan_speeds = 3

    def get_command(
        self,
        power: int,
        mode: int,
        fan: int,
        temp: int,
        swing_v: int = VDIR_AUTO,
        swing_h: int = HDIR_AUTO,
    ) -> Command:
        power_code = _AQV_MODE_OFF
        op_mode = _AQV_MODE_HEAT
        fan_code = _AQV_FAN_AUTO
        temperature = max(16, min(27, temp))

        if power == POWER_ON:
            power_code = _AQV_MODE_ON
            if mode == MODE_AUTO:
                op_mode = _AQV_MODE_AUTO
                fan = FAN_AUTO
            elif mode == MODE_HEAT:
                op_mode = _AQV_MODE_HEAT
            elif mode == MODE_COOL:
                op_mode = _AQV_MODE_COOL
            elif mode == MODE_DRY:
                op_mode = _AQV_MODE_DRY
                fan = FAN_AUTO
            elif mode == MODE_FAN:
                op_mode = _AQV_MODE_FAN
                if fan == FAN_AUTO:
                    fan = FAN_1

        fan_code = {
            FAN_AUTO: _AQV_FAN_AUTO,
            FAN_1: _AQV_FAN1,
            FAN_2: _AQV_FAN2,
            FAN_3: _AQV_FAN3,
        }.get(fan, _AQV_FAN_AUTO)

        if swing_v == VDIR_SWING and swing_h == HDIR_SWING:
            swing = _AQV_VHS_SWING
        elif swing_v == VDIR_SWING:
            swing = _AQV_VS_SWING
        elif swing_h == HDIR_SWING:
            swing = _AQV_HS_SWING
        else:
            swing = _AQV_VHS_OFF

        return _send_samsung_aqv(power_code, op_mode, fan_code, temperature, swing)


def _send_samsung_aqv(
    power_mode: int,
    op_mode: int,
    fan_speed: int,
    temperature: int,
    swing: int,
) -> RawIRCommand:
    """Build Samsung AQV 21-byte (3×7) IR signal."""
    raw = bytearray(
        [
            0x02, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x01, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x01, 0x02, 0x00, 0x01, 0x00, 0x00, 0x00,
        ]
    )

    raw[6] = power_mode
    raw[20] = power_mode
    raw[19] = op_mode | fan_speed
    raw[18] = (temperature - 16) << 4
    raw[16] = swing

    _aqv_fill_checksum(raw[0:7])
    _aqv_fill_checksum(raw[7:14])
    _aqv_fill_checksum(raw[14:21])

    ir = IRSenderCapture()
    ir.setFrequency(38)

    ir.mark(_AQV_HDR_MARK)
    ir.space(_AQV_HDR_SPACE)
    for b in raw[0:7]:
        ir.sendIRbyte(b, _AQV_BIT_MARK, _AQV_ZERO_SPACE, _AQV_ONE_SPACE)

    ir.mark(_AQV_BIT_MARK)
    ir.space(_AQV_MSG_SPACE)
    ir.mark(_AQV_HDR_MARK)
    ir.space(_AQV_HDR_SPACE)
    for b in raw[7:14]:
        ir.sendIRbyte(b, _AQV_BIT_MARK, _AQV_ZERO_SPACE, _AQV_ONE_SPACE)

    ir.mark(_AQV_BIT_MARK)
    ir.space(_AQV_MSG_SPACE)
    ir.mark(_AQV_HDR_MARK)
    ir.space(_AQV_HDR_SPACE)
    for b in raw[14:21]:
        ir.sendIRbyte(b, _AQV_BIT_MARK, _AQV_ZERO_SPACE, _AQV_ONE_SPACE)

    ir.mark(_AQV_BIT_MARK)
    ir.space(0)
    return RawIRCommand.from_sender(ir)


class SamsungFJMHeatpumpIR(HeatpumpIRBase):
    """Samsung FJM (RJ040F2HXEA / MH026FNEA) series."""

    model_id = "samsung_fjm"
    display_name = "Samsung FJM"
    min_temp = 16.0
    max_temp = 30.0
    fan_speeds = 4

    def get_command(
        self,
        power: int,
        mode: int,
        fan: int,
        temp: int,
        swing_v: int = VDIR_AUTO,
        swing_h: int = HDIR_AUTO,
    ) -> Command:
        power_code = POWER_ON
        op_mode = _AQV_MODE_HEAT
        fan_code = _AQV_FAN_AUTO
        temperature = max(16, min(30, temp))
        swing_code = _FJM_VS_SWING if swing_v == VDIR_SWING else _AQV_VHS_OFF

        if power == POWER_OFF:
            return _send_samsung_fjm_off()

        if mode == MODE_AUTO:
            op_mode = _AQV_MODE_AUTO
            fan = FAN_AUTO
        elif mode == MODE_HEAT:
            op_mode = _AQV_MODE_HEAT
        elif mode == MODE_COOL:
            op_mode = _AQV_MODE_COOL
        elif mode == MODE_DRY:
            op_mode = _AQV_MODE_DRY
            fan = FAN_AUTO
        elif mode == MODE_FAN:
            op_mode = _AQV_MODE_FAN
            temperature = 24
            if fan == FAN_AUTO:
                fan = FAN_1

        fan_code = {
            FAN_AUTO: _AQV_FAN_AUTO,
            FAN_1: _AQV_FAN1,
            FAN_2: _AQV_FAN2,
            FAN_3: _AQV_FAN3,
            FAN_4: _FJM_FAN4,
        }.get(fan, _AQV_FAN_AUTO)

        return _send_samsung_fjm_on(op_mode, fan_code, temperature, swing_code)


def _send_samsung_fjm_frame(ir: IRSenderCapture, data: bytes) -> None:
    """Send one FJM 7-byte chunk with preceding header."""
    ir.mark(_FJM_HDR_MARK)
    ir.space(_FJM_HDR_SPACE)
    for b in data:
        ir.sendIRbyte(b, _FJM_BIT_MARK, _FJM_ZERO_SPACE, _FJM_ONE_SPACE)


def _send_samsung_fjm_off() -> RawIRCommand:
    """Build the Samsung FJM power-OFF signal."""
    ir = IRSenderCapture()
    ir.setFrequency(38)
    ir.mark(_FJM_HDR_MARK)
    ir.space(_FJM_HDR_SPACE)

    for i, b in enumerate(_FJM_OFF_CODE):
        ir.sendIRbyte(b, _FJM_BIT_MARK, _FJM_ZERO_SPACE, _FJM_ONE_SPACE)
        if i in (6, 13):
            ir.mark(_FJM_BIT_MARK)
            ir.space(_FJM_ONE_SPACE)
            ir.mark(_FJM_HDR_MARK)
            ir.space(_FJM_HDR_SPACE)

    ir.mark(_FJM_BIT_MARK)
    ir.space(0)
    return RawIRCommand.from_sender(ir)


def _send_samsung_fjm_on(
    op_mode: int, fan_speed: int, temperature: int, swing_v: int, turbo: bool = False
) -> RawIRCommand:
    """Build the Samsung FJM power-ON signal."""
    template = bytearray([0x01, 0x00, 0x0F, 0x01, 0x00, 0x00, 0xF0])

    template[2] |= swing_v
    template[4] = (temperature - 16) << 4
    template[5] = op_mode | fan_speed

    if turbo:
        template[3] |= _FJM_TURBO

    # Checksum: count set bits in bytes 2-5 (byte 2 masked)
    total = 0
    for j in range(2, 6):
        b = template[j] & (0xFE if j == 2 else 0xFF)
        for _ in range(8):
            if b & 0x01:
                total += 1
            b >>= 1
    checksum = ((28 - total) << 4) | 0x02
    template[1] = checksum & 0xFF

    ir = IRSenderCapture()
    ir.setFrequency(38)
    ir.mark(_FJM_HDR_MARK)
    ir.space(_FJM_HDR_SPACE)

    for b in _FJM_HEADER:
        ir.sendIRbyte(b, _FJM_BIT_MARK, _FJM_ZERO_SPACE, _FJM_ONE_SPACE)

    ir.mark(_FJM_BIT_MARK)
    ir.space(_FJM_ONE_SPACE)
    ir.mark(_FJM_HDR_MARK)
    ir.space(_FJM_HDR_SPACE)

    for b in template:
        ir.sendIRbyte(b, _FJM_BIT_MARK, _FJM_ZERO_SPACE, _FJM_ONE_SPACE)

    ir.mark(_FJM_BIT_MARK)
    ir.space(0)
    return RawIRCommand.from_sender(ir)
