"""Olimpia Splendid Maestro heatpump IR protocol implementation."""

from __future__ import annotations

from infrared_protocols.commands import Command

from .base import (
    FAN_1, FAN_2, FAN_3, FAN_AUTO, HDIR_AUTO, MODE_AUTO, MODE_COOL,
    MODE_DRY, MODE_FAN, MODE_HEAT, POWER_OFF, POWER_ON, VDIR_AUTO, VDIR_SWING,
    HeatpumpIRBase, IRSenderCapture, RawIRCommand,
)

_HDR_MARK = 3200
_HDR_SPACE = 1700
_BIT_MARK = 420
_ONE_SPACE = 1280
_ZERO_SPACE = 420

_NUM_BYTES = 11


class OlimpiaSplendidMaestroHeatpumpIR(HeatpumpIRBase):
    model_id = "olimpia"
    display_name = "Olimpia Splendid Maestro"
    min_temp = 15.0
    max_temp = 30.0
    fan_speeds = 3

    def get_command(self, power, mode, fan, temp, swing_v=VDIR_AUTO, swing_h=HDIR_AUTO) -> Command:
        buf = [0] * _NUM_BYTES
        buf[0] = 0x5A

        encoded_mode = 0
        if power == POWER_ON:
            mode_map = {
                MODE_COOL: 0b001, MODE_HEAT: 0b010, MODE_DRY: 0b011,
                MODE_FAN: 0b100, MODE_AUTO: 0b101,
            }
            encoded_mode = mode_map.get(mode, 0)

        fan_map = {FAN_1: 0b00, FAN_2: 0b01, FAN_3: 0b10, FAN_AUTO: 0b11}
        encoded_fan = fan_map.get(fan, 0b11)

        flap_swing = 1 if swing_v == VDIR_SWING else 0

        buf[1] = encoded_mode | (encoded_fan << 3) | (flap_swing << 5)

        if 14 < temp < 31:
            raw_temp = 2 * (temp - 15)
        else:
            raw_temp = 2 * (23 - 15)
        buf[9] = raw_temp & 0x1F

        checksum = sum(buf[:10]) & 0xFF
        buf[10] = checksum

        ir = IRSenderCapture()
        ir.setFrequency(38)
        ir.mark(_HDR_MARK)
        ir.space(_HDR_SPACE)
        for b in buf:
            ir.sendIRbyte(b, _BIT_MARK, _ZERO_SPACE, _ONE_SPACE)
        ir.mark(_BIT_MARK)
        ir.space(0)
        return RawIRCommand.from_sender(ir)
