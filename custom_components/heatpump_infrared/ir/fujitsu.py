"""Fujitsu AWYZ heatpump IR protocol implementation.

Ported from FujitsuHeatpumpIR.cpp (arduino-heatpumpir).
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

# Timing constants
_HDR_MARK = 3210
_HDR_SPACE = 1680
_BIT_MARK = 410
_ONE_SPACE = 1230
_ZERO_SPACE = 440

# Operating mode codes
_MODE_AUTO = 0x00
_MODE_HEAT = 0x04
_MODE_COOL = 0x01
_MODE_DRY = 0x02
_MODE_FAN = 0x03
_MODE_OFF = 0xFF  # pseudo-value triggers short OFF message

# Fan speed codes
_FAN_AUTO = 0x00
_FAN1 = 0x04
_FAN2 = 0x03
_FAN3 = 0x02
_FAN4 = 0x01

# Swing codes
_VDIR_MANUAL = 0x00
_VDIR_SWING = 0x10
_HDIR_MANUAL = 0x00
_HDIR_SWING = 0x20

# Eco mode
_ECO_OFF = 0x20
_ECO_ON = 0x00


class FujitsuAWYZHeatpumpIR(HeatpumpIRBase):
    """Fujitsu Nocria AWYZ14 (remote P/N AR-PZ2)."""

    model_id = "fujitsu_awyz"
    display_name = "Fujitsu AWYZ"
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
        if power == POWER_OFF:
            op_mode = _MODE_OFF
        else:
            op_mode = {
                MODE_AUTO: _MODE_AUTO,
                MODE_HEAT: _MODE_HEAT,
                MODE_COOL: _MODE_COOL,
                MODE_DRY: _MODE_DRY,
                MODE_FAN: _MODE_FAN,
            }.get(mode, _MODE_HEAT)

        fan_code = {
            FAN_AUTO: _FAN_AUTO,
            FAN_1: _FAN1,
            FAN_2: _FAN2,
            FAN_3: _FAN3,
            FAN_4: _FAN4,
        }.get(fan, _FAN_AUTO)

        temperature = max(16, min(30, temp))

        swing_v_code = _VDIR_SWING if swing_v == VDIR_SWING else _VDIR_MANUAL
        swing_h_code = _HDIR_SWING if swing_h == HDIR_SWING else _HDIR_MANUAL

        return _send_fujitsu(op_mode, fan_code, temperature, swing_v_code, swing_h_code)


def _send_fujitsu_msg(ir: IRSenderCapture, msg: bytes) -> None:
    """Send header + payload for a Fujitsu message."""
    ir.mark(_HDR_MARK)
    ir.space(_HDR_SPACE)
    for byte in msg:
        ir.sendIRbyte(byte, _BIT_MARK, _ZERO_SPACE, _ONE_SPACE)
    ir.mark(_BIT_MARK)
    ir.space(0)


def _send_fujitsu(
    op_mode: int,
    fan_speed: int,
    temperature: int,
    swing_v: int,
    swing_h: int,
    eco: int = _ECO_OFF,
) -> RawIRCommand:
    """Build the Fujitsu IR signal."""
    ir = IRSenderCapture()
    ir.setFrequency(38)

    if op_mode == _MODE_OFF:
        off_msg = bytes([0x14, 0x63, 0x00, 0x10, 0x10, 0x02, 0xFD])
        _send_fujitsu_msg(ir, off_msg)
        return RawIRCommand.from_sender(ir)

    template = bytearray(
        [
            0x14, 0x63, 0x00, 0x10, 0x10, 0xFE, 0x09, 0x30,
            0x80, 0x04, 0x00, 0x00, 0x00, 0x00, 0x20, 0x00,
        ]
    )

    template[9] = op_mode
    template[14] = eco
    template[8] = ((temperature - 16) << 4) | 0x01
    template[10] = fan_speed + swing_v + swing_h

    checksum = sum(template[:15]) & 0xFF
    template[15] = (0x9E - checksum) & 0xFF

    _send_fujitsu_msg(ir, bytes(template))
    return RawIRCommand.from_sender(ir)
