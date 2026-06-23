"""Panasonic heatpump IR protocol implementations.

For DKE/EKE/JKE/NKE/LKE models, delegates to the infrared-protocols library
which already implements the Kaseikyo/AEHA framing natively.

The older CKP protocol is ported from PanasonicCKPHeatpumpIR.cpp.
"""

from __future__ import annotations

from infrared_protocols.commands import Command
from infrared_protocols.commands.panasonic_ac import (
    PanasonicAcCommand,
    PanasonicAcFanSpeed,
    PanasonicAcMode,
    PanasonicAcSwingAxis1,
    PanasonicAcSwingAxis2,
    PanasonicAcToggle,
    PanasonicAcToggleCommand,
)

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
    RawIRCommand,
)


def _map_mode(mode: int) -> PanasonicAcMode:
    return {
        MODE_AUTO: PanasonicAcMode.AUTO,
        MODE_HEAT: PanasonicAcMode.HEAT,
        MODE_COOL: PanasonicAcMode.COOL,
        MODE_DRY: PanasonicAcMode.DRY,
    }.get(mode, PanasonicAcMode.AUTO)


def _map_fan(fan: int) -> PanasonicAcFanSpeed:
    return {
        FAN_AUTO: PanasonicAcFanSpeed.AUTO,
        FAN_1: PanasonicAcFanSpeed.LOW,
        FAN_2: PanasonicAcFanSpeed.MEDIUM_LOW,
        FAN_3: PanasonicAcFanSpeed.MEDIUM,
        FAN_4: PanasonicAcFanSpeed.MEDIUM_HIGH,
        FAN_5: PanasonicAcFanSpeed.HIGH,
    }.get(fan, PanasonicAcFanSpeed.AUTO)


def _map_swing_v(swing: int) -> PanasonicAcSwingAxis1:
    return {
        VDIR_AUTO: PanasonicAcSwingAxis1.AUTO,
        VDIR_SWING: PanasonicAcSwingAxis1.AUTO,
        VDIR_UP: PanasonicAcSwingAxis1.HIGHEST,
        VDIR_MUP: PanasonicAcSwingAxis1.HIGH,
        VDIR_MIDDLE: PanasonicAcSwingAxis1.MIDDLE,
        VDIR_MDOWN: PanasonicAcSwingAxis1.LOW,
        VDIR_DOWN: PanasonicAcSwingAxis1.LOWEST,
    }.get(swing, PanasonicAcSwingAxis1.AUTO)


def _map_swing_h(swing: int) -> PanasonicAcSwingAxis2:
    return {
        HDIR_AUTO: PanasonicAcSwingAxis2.AUTO,
        HDIR_SWING: PanasonicAcSwingAxis2.AUTO,
        HDIR_MIDDLE: PanasonicAcSwingAxis2.MIDDLE,
        HDIR_LEFT: PanasonicAcSwingAxis2.FULL_LEFT,
        HDIR_MLEFT: PanasonicAcSwingAxis2.LEFT,
        HDIR_MRIGHT: PanasonicAcSwingAxis2.RIGHT,
        HDIR_RIGHT: PanasonicAcSwingAxis2.FULL_RIGHT,
    }.get(swing, PanasonicAcSwingAxis2.AUTO)


class _PanasonicKaseikyoBase(HeatpumpIRBase):
    """Base for Panasonic models using the Kaseikyo (AEHA) format."""

    min_temp = 16.0
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
        powered = power != POWER_OFF

        # Clamp temperature
        temperature = max(self.min_temp, min(self.max_temp, float(temp)))

        # FAN mode has no meaningful temperature
        if mode == MODE_FAN:
            temperature = 27.0
            powered = powered  # keep intent

        return PanasonicAcCommand(
            power=powered,
            mode=_map_mode(mode),
            temperature=temperature,
            fan=_map_fan(fan),
            swing_axis1=_map_swing_v(swing_v),
            swing_axis2=_map_swing_h(swing_h),
        )


class PanasonicDKEHeatpumpIR(_PanasonicKaseikyoBase):
    model_id = "panasonic_dke"
    display_name = "Panasonic DKE"


class PanasonicEKEHeatpumpIR(_PanasonicKaseikyoBase):
    model_id = "panasonic_eke"
    display_name = "Panasonic EKE"


class PanasonicJKEHeatpumpIR(_PanasonicKaseikyoBase):
    model_id = "panasonic_jke"
    display_name = "Panasonic JKE"


class PanasonicNKEHeatpumpIR(_PanasonicKaseikyoBase):
    model_id = "panasonic_nke"
    display_name = "Panasonic NKE"


class PanasonicLKEHeatpumpIR(_PanasonicKaseikyoBase):
    model_id = "panasonic_lke"
    display_name = "Panasonic LKE"


# ---------------------------------------------------------------------------
# Panasonic CKP (older direct-encoding format)
# Ported from PanasonicCKPHeatpumpIR.cpp
# ---------------------------------------------------------------------------

_CKP_HDR_MARK = 3500
_CKP_HDR_SPACE = 1750
_CKP_BIT_MARK = 435
_CKP_ONE_SPACE = 1300
_CKP_ZERO_SPACE = 435
_CKP_MSG_SPACE = 10000

# CKP codes
_CKP_MODE_AUTO = 0x06
_CKP_MODE_HEAT = 0x04
_CKP_MODE_COOL = 0x02
_CKP_MODE_DRY = 0x03

_CKP_FAN_AUTO = 0x00
_CKP_FAN1 = 0x02
_CKP_FAN2 = 0x03
_CKP_FAN3 = 0x05

_CKP_POWER_OFF = 0x00
_CKP_POWER_ON = 0x01


class PanasonicCKPHeatpumpIR(HeatpumpIRBase):
    """Panasonic CKP older format."""

    model_id = "panasonic_ckp"
    display_name = "Panasonic CKP"
    min_temp = 16.0
    max_temp = 30.0
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
        power_code = _CKP_POWER_ON if power == 1 else _CKP_POWER_OFF

        op_code = {
            MODE_AUTO: _CKP_MODE_AUTO,
            MODE_HEAT: _CKP_MODE_HEAT,
            MODE_COOL: _CKP_MODE_COOL,
            MODE_DRY: _CKP_MODE_DRY,
            MODE_FAN: _CKP_MODE_AUTO,
        }.get(mode, _CKP_MODE_AUTO)

        fan_code = {
            FAN_AUTO: _CKP_FAN_AUTO,
            FAN_1: _CKP_FAN1,
            FAN_2: _CKP_FAN2,
            FAN_3: _CKP_FAN3,
            FAN_4: _CKP_FAN3,
            FAN_5: _CKP_FAN3,
        }.get(fan, _CKP_FAN_AUTO)

        temperature = max(16, min(30, temp))

        return _send_panasonic_ckp(power_code, op_code, fan_code, temperature)


def _send_panasonic_ckp(
    power: int, op_mode: int, fan: int, temperature: int
) -> RawIRCommand:
    """Build Panasonic CKP IR signal (two identical frames)."""
    # The CKP message is 8 bytes. We reconstruct it from the original C++ logic.
    # Byte layout (from CKP analysis):
    #   [0]=0x40 [1]=0x04 [2]=0x07 [3]=0x20
    #   [4]=mode|power  [5]=fan  [6]=temp  [7]=checksum
    template = bytearray([0x40, 0x04, 0x07, 0x20, 0x00, 0x00, 0x00, 0x00])

    template[4] = (op_mode << 4) | power
    template[5] = fan
    template[6] = temperature - 16

    checksum = 0
    for b in template[:7]:
        checksum ^= b
    template[7] = checksum

    ir = IRSenderCapture()
    ir.setFrequency(38)

    for _ in range(2):
        ir.mark(_CKP_HDR_MARK)
        ir.space(_CKP_HDR_SPACE)
        for b in template:
            ir.sendIRbyte(b, _CKP_BIT_MARK, _CKP_ZERO_SPACE, _CKP_ONE_SPACE)
        ir.mark(_CKP_BIT_MARK)
        ir.space(_CKP_MSG_SPACE)

    ir.mark(_CKP_BIT_MARK)
    ir.space(0)
    return RawIRCommand.from_sender(ir)
