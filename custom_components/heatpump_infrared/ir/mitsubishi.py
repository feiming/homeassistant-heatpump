"""Mitsubishi heatpump IR protocol implementations.

Ported from MitsubishiHeatpumpIR.cpp (arduino-heatpumpir).
Covers models: FD, FE, MSY, FA, KJ.
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
    HDIR_LEFT,
    HDIR_MIDDLE,
    HDIR_MLEFT,
    HDIR_MRIGHT,
    HDIR_RIGHT,
    HDIR_SWING,
    POWER_OFF,
    VDIR_AUTO,
    VDIR_DOWN,
    VDIR_MIDDLE,
    VDIR_MDOWN,
    VDIR_MUP,
    VDIR_SWING,
    VDIR_UP,
    HeatpumpIRBase,
    IRSenderCapture,
    MODE_AUTO,
    MODE_COOL,
    MODE_DRY,
    MODE_FAN,
    MODE_HEAT,
    MODE_MAINT,
    RawIRCommand,
)

# Timing constants
_HDR_MARK = 3500
_HDR_SPACE = 1700
_BIT_MARK = 430
_ONE_SPACE = 1250
_ZERO_SPACE = 390
_MSG_SPACE = 17500

# Operating mode codes
_MODE_AUTO = 0x20
_MODE_HEAT = 0x08
_MODE_COOL = 0x18
_MODE_DRY = 0x10
_MODE_FAN = 0x38
_MODE_OFF = 0x00
_MODE_ON = 0x20
_MODE3_AUTO = 0x60  # FA model
_MODE3_HEAT = 0x48
_MODE3_COOL = 0x58
_MODE3_DRY = 0x50
_MODE2_COOL = 0x18  # MSY model
_MODE2_IFEEL = 0x00
_MODE2_FAN = 0x38

# Fan speed codes
_FAN_AUTO = 0x00
_FAN1 = 0x01
_FAN2 = 0x02
_FAN3 = 0x03
_FAN4 = 0x04
_FAN5 = 0x05  # also QUIET on KJ

# Vertical swing codes
_VS_SWING = 0x78
_VS_AUTO = 0x40
_VS_UP = 0x48
_VS_MUP = 0x50
_VS_MIDDLE = 0x58
_VS_MDOWN = 0x60
_VS_DOWN = 0x68
_VS3_MDOWN = 0x58  # FA
_VS3_DOWN = 0x60   # FA

# Horizontal swing codes
_HS_SWING = 0xC0
_HS_MIDDLE = 0x30
_HS_LEFT = 0x10
_HS_MLEFT = 0x20
_HS_MRIGHT = 0x40
_HS_RIGHT = 0x50

# Model variants
_MODEL_FD = 0
_MODEL_FE = 1
_MODEL_MSY = 2
_MODEL_FA = 3
_MODEL_KJ = 4


def _build_mitsubishi(
    model: int,
    power_mode: int,
    operating_mode: int,
    fan_speed: int,
    temperature: int,
    swing_v: int,
    swing_h: int,
) -> list[int]:
    """Build the 18-byte Mitsubishi payload and return as list."""
    template = bytearray(
        [
            0x23, 0xCB, 0x26, 0x01, 0x00, 0x20, 0x48, 0x00,
            0x00, 0x00, 0x61, 0x00, 0x00, 0x00, 0x10, 0x40,
            0x00, 0x00,
        ]
    )

    if model == _MODEL_MSY:
        template[14] = 0x00
        template[15] = 0x00
    elif model == _MODEL_FA:
        template[10] = 0x00
        template[15] = 0x00
    elif model == _MODEL_KJ:
        template[15] = 0x00

    template[5] = power_mode
    template[6] = operating_mode

    if temperature == 10:
        template[7] = 0x00
        template[15] = 0x20
    else:
        template[7] = temperature - 16

    template[8] = swing_h
    template[9] = fan_speed | swing_v

    if model == _MODEL_KJ:
        if operating_mode in (_MODE_AUTO, _MODE_COOL):
            template[8] = 0x06
        elif operating_mode == _MODE_DRY:
            template[8] = 0x02
        else:
            template[8] = 0x00
        if swing_h != 0:
            template[16] = 0x02

    checksum = sum(template[:17]) & 0xFF
    template[17] = checksum
    return list(template)


def _send_mitsubishi_raw(
    model: int,
    power: int,
    op_mode: int,
    fan: int,
    temp: int,
    swing_v_code: int,
    swing_h_code: int,
) -> RawIRCommand:
    """Build the complete Mitsubishi IR command (sent twice with a gap)."""
    ir = IRSenderCapture()
    ir.setFrequency(38)

    payload = _build_mitsubishi(model, power, op_mode, fan, temp, swing_v_code, swing_h_code)

    for j in range(2):
        ir.mark(_HDR_MARK)
        ir.space(_HDR_SPACE)
        for byte in payload:
            ir.sendIRbyte(byte, _BIT_MARK, _ZERO_SPACE, _ONE_SPACE)

        if j == 0:
            ir.mark(_BIT_MARK)
            ir.space(_MSG_SPACE)
            if model == _MODEL_MSY:
                payload[14] = 0x24

    ir.mark(_BIT_MARK)
    ir.space(0)

    return RawIRCommand.from_sender(ir)


class _MitsubishiBase(HeatpumpIRBase):
    _model_variant: int
    min_temp: float = 16.0
    max_temp: float = 31.0
    fan_speeds: int = 5

    def get_command(
        self,
        power: int,
        mode: int,
        fan: int,
        temp: int,
        swing_v: int = VDIR_AUTO,
        swing_h: int = HDIR_AUTO,
    ) -> Command:
        power_code = _MODE_ON if power == 1 else _MODE_OFF
        op_code = _MODE_HEAT
        temperature = 23
        fan_code = _FAN_AUTO

        if power == POWER_OFF:
            power_code = _MODE_OFF
        else:
            if self._model_variant == _MODEL_FA:
                op_code = {
                    MODE_AUTO: _MODE3_AUTO,
                    MODE_HEAT: _MODE3_HEAT,
                    MODE_COOL: _MODE3_COOL,
                    MODE_DRY: _MODE3_DRY,
                }.get(mode, _MODE3_HEAT)
            elif self._model_variant == _MODEL_MSY:
                op_code = {
                    MODE_AUTO: _MODE2_IFEEL,
                    MODE_HEAT: _MODE_HEAT,
                    MODE_COOL: _MODE2_COOL,
                    MODE_DRY: _MODE_DRY,
                    MODE_FAN: _MODE2_FAN,
                }.get(mode, _MODE2_COOL)
            else:
                if mode == MODE_FAN:
                    if self._model_variant == _MODEL_FE:
                        op_code = _MODE_FAN
                        temp = 24
                    else:
                        op_code = _MODE_COOL
                        temp = 31
                elif mode == MODE_MAINT:
                    if self._model_variant in (_MODEL_FE, _MODEL_KJ):
                        op_code = _MODE_HEAT
                        temp = 10
                        fan = FAN_AUTO
                else:
                    op_code = {
                        MODE_AUTO: _MODE_AUTO,
                        MODE_HEAT: _MODE_HEAT,
                        MODE_COOL: _MODE_COOL,
                        MODE_DRY: _MODE_DRY,
                    }.get(mode, _MODE_HEAT)

        fan_code = {
            FAN_AUTO: _FAN_AUTO,
            FAN_1: _FAN1,
            FAN_2: _FAN2,
            FAN_3: _FAN3,
            FAN_4: _FAN4,
            FAN_5: _FAN5,
        }.get(fan, _FAN_AUTO)

        if temp != 10 and 17 <= temp <= 31:
            temperature = temp

        swing_v_code = {
            VDIR_AUTO: _VS_AUTO,
            VDIR_SWING: _VS_SWING,
            VDIR_UP: _VS_UP,
            VDIR_MUP: _VS_MUP,
            VDIR_MIDDLE: _VS_MIDDLE,
            VDIR_MDOWN: _VS_MDOWN,
            VDIR_DOWN: _VS_DOWN,
        }.get(swing_v, _VS_AUTO)

        if self._model_variant == _MODEL_KJ:
            swing_h_code = swing_h
        else:
            swing_h_code = {
                HDIR_AUTO: _HS_SWING,
                HDIR_SWING: _HS_SWING,
                HDIR_MIDDLE: _HS_MIDDLE,
                HDIR_LEFT: _HS_LEFT,
                HDIR_MLEFT: _HS_MLEFT,
                HDIR_MRIGHT: _HS_MRIGHT,
                HDIR_RIGHT: _HS_RIGHT,
            }.get(swing_h, _HS_SWING)

        return _send_mitsubishi_raw(
            self._model_variant,
            power_code,
            op_code,
            fan_code,
            temperature,
            swing_v_code,
            swing_h_code,
        )


class MitsubishiFDHeatpumpIR(_MitsubishiBase):
    """Mitsubishi FD series."""

    model_id = "mitsubishi_fd"
    display_name = "Mitsubishi FD"
    _model_variant = _MODEL_FD


class MitsubishiFEHeatpumpIR(_MitsubishiBase):
    """Mitsubishi FE series."""

    model_id = "mitsubishi_fe"
    display_name = "Mitsubishi FE"
    _model_variant = _MODEL_FE


class MitsubishiMSYHeatpumpIR(_MitsubishiBase):
    """Mitsubishi MSY series (only COOL/FAN modes)."""

    model_id = "mitsubishi_msy"
    display_name = "Mitsubishi MSY"
    _model_variant = _MODEL_MSY


class MitsubishiFAHeatpumpIR(_MitsubishiBase):
    """Mitsubishi FA series."""

    model_id = "mitsubishi_fa"
    display_name = "Mitsubishi FA"
    _model_variant = _MODEL_FA


class MitsubishiKJHeatpumpIR(_MitsubishiBase):
    """Mitsubishi KJ series."""

    model_id = "mitsubishi_kj"
    display_name = "Mitsubishi KJ"
    _model_variant = _MODEL_KJ
