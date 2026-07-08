"""Panasonic ceiling-fan IR protocol (AEHA / Kaseikyo).

Unlike the heat-pump protocols this drives a Panasonic ceiling fan with nine
discrete speeds plus off. The original capture was a table of ten fixed 13-byte
AEHA payloads; this module regenerates them algorithmically:

  * byte 4 encodes the running speed 1-9. The speed occupies the high nibble
    with its four bits reversed (AEHA is transmitted LSB-first), and the low
    nibble is fixed at 0x4;
  * the OFF frame leaves the speed nibble alone and instead flips a power bit
    in byte 3 and byte 5;
  * the final byte is an XOR checksum of the preceding twelve.

The frame is emitted exactly as ESPHome's ``remote_transmitter.transmit_aeha``
would for ``address: 0x4004`` — leader, 16-bit customer code (LSB-first), the
payload bytes (each LSB-first), then a stop mark.
"""

from __future__ import annotations

from infrared_protocols.commands import Command

from .base import IRSenderCapture, RawIRCommand

# AEHA framing (ESPHome remote_base/aeha_protocol.cpp defaults, 38 kHz)
_AEHA_HDR_MARK = 3400
_AEHA_HDR_SPACE = 1700
_AEHA_BIT_MARK = 425
_AEHA_ONE_SPACE = 1275
_AEHA_ZERO_SPACE = 425

# Customer / vendor code transmitted ahead of the payload
_AEHA_ADDRESS = 0x4004

# Fixed 12-byte payload prefix; the checksum byte is appended at build time.
# Bytes 3 (power), 4 (speed) and 5 (power) are overwritten per command below.
_TEMPLATE = [0x0B, 0x21, 0x8C, 0x40, 0x84, 0x4C, 0x02, 0xB2, 0x0E, 0x81, 0xC1, 0x1A]

# Byte 3 / byte 5 differ between running (ON) and OFF frames.
_BYTE3_OFF = 0x80
_BYTE5_OFF = 0xCC

#: Sentinel speed meaning "fan off".
SPEED_OFF = 0
#: Lowest / highest running speed the remote supports.
MIN_SPEED = 1
MAX_SPEED = 9


def _reverse_nibble(value: int) -> int:
    """Reverse the low four bits of ``value`` (AEHA transmits LSB-first)."""
    return (
        ((value & 0x1) << 3)
        | ((value & 0x2) << 1)
        | ((value & 0x4) >> 1)
        | ((value & 0x8) >> 3)
    )


def build_payload(speed: int) -> list[int]:
    """Return the 13-byte AEHA payload (checksum included) for ``speed``.

    ``speed`` is :data:`SPEED_OFF` for off, or 1-9 for a running speed.
    """
    data = list(_TEMPLATE)
    if speed == SPEED_OFF:
        data[3] = _BYTE3_OFF
        data[5] = _BYTE5_OFF
        # byte 4 keeps its speed-1 value; the unit ignores it while off
    else:
        data[4] = (_reverse_nibble(speed) << 4) | 0x04

    checksum = 0
    for byte in data:
        checksum ^= byte
    data.append(checksum)
    return data


class PanasonicCeilingFanIR:
    """Panasonic ceiling fan controlled over AEHA: nine speeds plus off."""

    model_id = "panasonic_ceiling_fan"
    display_name = "Panasonic Ceiling Fan"
    min_speed = MIN_SPEED
    max_speed = MAX_SPEED

    def get_command(self, speed: int) -> Command:
        """Build the IR command for ``speed`` (0 = off, 1-9 = running)."""
        if speed != SPEED_OFF and not (MIN_SPEED <= speed <= MAX_SPEED):
            raise ValueError(
                f"speed must be {SPEED_OFF} or {MIN_SPEED}-{MAX_SPEED}, got {speed}"
            )

        payload = build_payload(speed)

        ir = IRSenderCapture()
        ir.setFrequency(38)
        ir.mark(_AEHA_HDR_MARK)
        ir.space(_AEHA_HDR_SPACE)
        # 16-bit customer code, low byte first (LSB-first across all 16 bits)
        ir.sendIRbyte(
            _AEHA_ADDRESS & 0xFF, _AEHA_BIT_MARK, _AEHA_ZERO_SPACE, _AEHA_ONE_SPACE
        )
        ir.sendIRbyte(
            (_AEHA_ADDRESS >> 8) & 0xFF,
            _AEHA_BIT_MARK,
            _AEHA_ZERO_SPACE,
            _AEHA_ONE_SPACE,
        )
        for byte in payload:
            ir.sendIRbyte(byte, _AEHA_BIT_MARK, _AEHA_ZERO_SPACE, _AEHA_ONE_SPACE)
        # stop bit
        ir.mark(_AEHA_BIT_MARK)
        ir.space(0)
        return RawIRCommand.from_sender(ir)
