"""Base classes for heatpump IR protocol implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod

from infrared_protocols.commands import Command

# Power state
POWER_OFF = 0
POWER_ON = 1

# Operating modes
MODE_AUTO = 1
MODE_HEAT = 2
MODE_COOL = 3
MODE_DRY = 4
MODE_FAN = 5
MODE_MAINT = 6

# Fan speeds
FAN_AUTO = 0
FAN_1 = 1
FAN_2 = 2
FAN_3 = 3
FAN_4 = 4
FAN_5 = 5
FAN_SILENT = 6

# Vertical swing
VDIR_AUTO = 0
VDIR_SWING = 1
VDIR_UP = 2
VDIR_MUP = 3
VDIR_MIDDLE = 4
VDIR_MDOWN = 5
VDIR_DOWN = 6

# Horizontal swing
HDIR_AUTO = 0
HDIR_SWING = 1
HDIR_MIDDLE = 2
HDIR_LEFT = 3
HDIR_MLEFT = 4
HDIR_MRIGHT = 5
HDIR_RIGHT = 6


class IRSenderCapture:
    """Captures mark/space timings instead of transmitting them.

    Mimics the C++ IRSender interface from arduino-heatpumpir so the brand
    implementations can be ported with minimal changes.
    """

    def __init__(self) -> None:
        """Initialize the capture buffer."""
        self._timings: list[int] = []
        self._modulation: int = 38000

    def setFrequency(self, freq_khz: int) -> None:  # noqa: N802
        """Set the carrier frequency in kHz (as in the C++ library)."""
        self._modulation = freq_khz * 1000

    def mark(self, us: int) -> None:
        """Append a pulse (mark) of the given duration in microseconds."""
        self._timings.append(us)

    def space(self, us: int) -> None:
        """Append a gap (space) of the given duration in microseconds.

        A zero-length space is silently dropped (used as a no-op terminator in
        the C++ library).
        """
        if us > 0:
            self._timings.append(-us)

    def sendIRbyte(  # noqa: N802
        self,
        byte: int,
        bit_mark: int,
        zero_space: int,
        one_space: int,
        bit_count: int = 8,
    ) -> None:
        """Send one byte LSB-first as alternating mark/space pairs."""
        for _ in range(bit_count):
            self.mark(bit_mark)
            self.space(one_space if (byte & 0x01) else zero_space)
            byte >>= 1

    @staticmethod
    def bit_reverse(x: int) -> int:
        """Reverse the bits of a byte (used by some Carrier-derived protocols)."""
        x = ((x >> 1) & 0x55) | ((x << 1) & 0xAA)
        x = ((x >> 2) & 0x33) | ((x << 2) & 0xCC)
        x = ((x >> 4) & 0x0F) | ((x << 4) & 0xF0)
        return x & 0xFF


class RawIRCommand(Command):
    """infrared_protocols Command wrapping a raw list of mark/space timings."""

    def __init__(
        self,
        timings: list[int],
        modulation: int = 38000,
        repeat_count: int = 0,
    ) -> None:
        """Create a raw IR command."""
        super().__init__(modulation=modulation, repeat_count=repeat_count)
        self._timings = timings

    def get_raw_timings(self) -> list[int]:
        """Return the captured timings."""
        return self._timings

    @classmethod
    def from_sender(
        cls, sender: IRSenderCapture, repeat_count: int = 0
    ) -> "RawIRCommand":
        """Build a command from a completed IRSenderCapture."""
        return cls(
            timings=list(sender._timings),
            modulation=sender._modulation,
            repeat_count=repeat_count,
        )


class HeatpumpIRBase(ABC):
    """Abstract base class for all heatpump IR protocol implementations."""

    #: Short identifier string, same as used in HeatpumpIRFactory
    model_id: str
    #: Human-readable name shown in the UI
    display_name: str
    #: Minimum controllable temperature (°C)
    min_temp: float = 16.0
    #: Maximum controllable temperature (°C)
    max_temp: float = 30.0
    #: Number of discrete fan speeds (excluding AUTO). 0 = AUTO only.
    fan_speeds: int = 5

    @abstractmethod
    def get_command(
        self,
        power: int,
        mode: int,
        fan: int,
        temp: int,
        swing_v: int = VDIR_AUTO,
        swing_h: int = HDIR_AUTO,
    ) -> Command:
        """Build and return the IR command for the given state."""
