"""Registry of all supported heatpump IR protocol implementations."""

from __future__ import annotations

from .aux import AUXHeatpumpIR
from .ballu import BalluHeatpumpIR
from .base import FAN_AUTO, HDIR_AUTO, POWER_OFF, POWER_ON, VDIR_AUTO, HeatpumpIRBase
from .bgh import BGHHeatpumpIR
from .carrier import CarrierMCAHeatpumpIR, CarrierNQVHeatpumpIR
from .daikin import DaikinHeatpumpIR
from .daikin_arc417 import DaikinARC417HeatpumpIR
from .daikin_arc480 import DaikinARC480HeatpumpIR
from .electrolux import ElectroluxYALHeatpumpIR
from .fuego import AIRWAYHeatpumpIR, FuegoHeatpumpIR
from .fujitsu import FujitsuAWYZHeatpumpIR
from .gree import (
    GreeGenericHeatpumpIR,
    GreeYAAHeatpumpIR,
    GreeYACHeatpumpIR,
    GreeYANHeatpumpIR,
    GreeYTHeatpumpIR,
)
from .hisense import HisenseHeatpumpIR
from .hitachi import HitachiHeatpumpIR
from .hyundai import HyundaiHeatpumpIR
from .midea import MideaHeatpumpIR
from .mitsubishi import (
    MitsubishiFAHeatpumpIR,
    MitsubishiFDHeatpumpIR,
    MitsubishiFEHeatpumpIR,
    MitsubishiKJHeatpumpIR,
    MitsubishiMSYHeatpumpIR,
)
from .mitsubishi_heavy import (
    MitsubishiHeavyFDTCHeatpumpIR,
    MitsubishiHeavyZEAHeatpumpIR,
    MitsubishiHeavyZJHeatpumpIR,
    MitsubishiHeavyZMHeatpumpIR,
)
from .mitsubishi_msc import MitsubishiMSCHeatpumpIR, MitsubishiSEZHeatpumpIR
from .nibe import NibeHeatpumpIR
from .olimpia import OlimpiaSplendidMaestroHeatpumpIR
from .panasonic import (
    PanasonicCKPHeatpumpIR,
    PanasonicDKEHeatpumpIR,
    PanasonicEKEHeatpumpIR,
    PanasonicJKEHeatpumpIR,
    PanasonicLKEHeatpumpIR,
    PanasonicNKEHeatpumpIR,
)
from .panasonic_fan import PanasonicCeilingFanIR
from .philco import PhilcoPHS32HeatpumpIR
from .samsung import SamsungAQVHeatpumpIR, SamsungFJMHeatpumpIR
from .sharp import IVTHeatpumpIR, SharpHeatpumpIR
from .toshiba import ToshibaDaiseikaiHeatpumpIR, ToshibaHeatpumpIR

__all__ = [
    "MODELS",
    "create_model",
    "HeatpumpIRBase",
    "FAN_MODELS",
    "create_fan_model",
    "PanasonicCeilingFanIR",
]

# Registry mapping model_id → implementation class
_REGISTRY: dict[str, type[HeatpumpIRBase]] = {
    # AUX
    "aux": AUXHeatpumpIR,
    # Airway
    "airway": AIRWAYHeatpumpIR,
    # Ballu
    "ballu": BalluHeatpumpIR,
    # BGH
    "bgh_aud": BGHHeatpumpIR,
    # Carrier
    "carrier_nqv": CarrierNQVHeatpumpIR,
    "carrier_mca": CarrierMCAHeatpumpIR,
    # Daikin
    "daikin": DaikinHeatpumpIR,
    "daikin_arc417": DaikinARC417HeatpumpIR,
    "daikin_arc480": DaikinARC480HeatpumpIR,
    # Electrolux
    "electrolux_yal": ElectroluxYALHeatpumpIR,
    # Fuego
    "fuego": FuegoHeatpumpIR,
    # Fujitsu
    "fujitsu_awyz": FujitsuAWYZHeatpumpIR,
    # Gree
    "gree_generic": GreeGenericHeatpumpIR,
    "gree_yan": GreeYANHeatpumpIR,
    "gree_yaa": GreeYAAHeatpumpIR,
    "gree_yac": GreeYACHeatpumpIR,
    "gree_yt": GreeYTHeatpumpIR,
    # Hisense
    "hisense_aud": HisenseHeatpumpIR,
    # Hitachi
    "hitachi": HitachiHeatpumpIR,
    # Hyundai
    "hyundai": HyundaiHeatpumpIR,
    # IVT (Sharp-based)
    "ivt": IVTHeatpumpIR,
    # Midea
    "midea": MideaHeatpumpIR,
    # Mitsubishi Electric
    "mitsubishi_fd": MitsubishiFDHeatpumpIR,
    "mitsubishi_fe": MitsubishiFEHeatpumpIR,
    "mitsubishi_msy": MitsubishiMSYHeatpumpIR,
    "mitsubishi_fa": MitsubishiFAHeatpumpIR,
    "mitsubishi_kj": MitsubishiKJHeatpumpIR,
    # Mitsubishi Heavy
    "mitsubishi_heavy_zj": MitsubishiHeavyZJHeatpumpIR,
    "mitsubishi_heavy_zea": MitsubishiHeavyZEAHeatpumpIR,
    "mitsubishi_heavy_zm": MitsubishiHeavyZMHeatpumpIR,
    "mitsubishi_heavy_fdtc": MitsubishiHeavyFDTCHeatpumpIR,
    # Mitsubishi MSC / SEZ
    "mitsubishi_msc": MitsubishiMSCHeatpumpIR,
    "mitsubishi_sez": MitsubishiSEZHeatpumpIR,
    # Nibe
    "nibe": NibeHeatpumpIR,
    # Olimpia Splendid
    "olimpia": OlimpiaSplendidMaestroHeatpumpIR,
    # Panasonic
    "panasonic_ckp": PanasonicCKPHeatpumpIR,
    "panasonic_dke": PanasonicDKEHeatpumpIR,
    "panasonic_eke": PanasonicEKEHeatpumpIR,
    "panasonic_jke": PanasonicJKEHeatpumpIR,
    "panasonic_nke": PanasonicNKEHeatpumpIR,
    "panasonic_lke": PanasonicLKEHeatpumpIR,
    # Philco
    "philco_phs32": PhilcoPHS32HeatpumpIR,
    # Samsung
    "samsung_aqv": SamsungAQVHeatpumpIR,
    "samsung_fjm": SamsungFJMHeatpumpIR,
    # Sharp
    "sharp": SharpHeatpumpIR,
    # Toshiba
    "toshiba": ToshibaHeatpumpIR,
    "toshiba_daiseikai": ToshibaDaiseikaiHeatpumpIR,
}

# Ordered list of (brand, model_id, display_name) used in the config flow
MODELS: list[tuple[str, str, str]] = [
    ("AUX", "aux", "AUX"),
    ("Airway", "airway", "AIRWAY"),
    ("Ballu", "ballu", "Ballu"),
    ("BGH", "bgh_aud", "BGH AUD"),
    ("Carrier", "carrier_nqv", "Carrier NQV"),
    ("Carrier", "carrier_mca", "Carrier MCA"),
    ("Daikin", "daikin", "Daikin (ARC433B50)"),
    ("Daikin", "daikin_arc417", "Daikin ARC417"),
    ("Daikin", "daikin_arc480", "Daikin ARC480"),
    ("Electrolux", "electrolux_yal", "Electrolux YAL"),
    ("Fuego", "fuego", "Fuego"),
    ("Fujitsu", "fujitsu_awyz", "Fujitsu AWYZ (AR-PZ2)"),
    ("Gree", "gree_generic", "Gree (generic)"),
    ("Gree", "gree_yan", "Gree YAN"),
    ("Gree", "gree_yaa", "Gree YAA"),
    ("Gree", "gree_yac", "Gree YAC"),
    ("Gree", "gree_yt", "Gree YT"),
    ("Hisense", "hisense_aud", "Hisense AUD"),
    ("Hitachi", "hitachi", "Hitachi"),
    ("Hyundai", "hyundai", "Hyundai"),
    ("IVT", "ivt", "IVT AY-XP12FR-N"),
    ("Midea", "midea", "Midea (Ultimate Pro Plus)"),
    ("Mitsubishi Electric", "mitsubishi_fd", "Mitsubishi FD"),
    ("Mitsubishi Electric", "mitsubishi_fe", "Mitsubishi FE"),
    ("Mitsubishi Electric", "mitsubishi_msy", "Mitsubishi MSY"),
    ("Mitsubishi Electric", "mitsubishi_fa", "Mitsubishi FA"),
    ("Mitsubishi Electric", "mitsubishi_kj", "Mitsubishi KJ"),
    ("Mitsubishi Electric", "mitsubishi_msc", "Mitsubishi MSC"),
    ("Mitsubishi Electric", "mitsubishi_sez", "Mitsubishi SEZ"),
    ("Mitsubishi Heavy", "mitsubishi_heavy_zj", "Mitsubishi Heavy ZJ"),
    ("Mitsubishi Heavy", "mitsubishi_heavy_zea", "Mitsubishi Heavy ZEA"),
    ("Mitsubishi Heavy", "mitsubishi_heavy_zm", "Mitsubishi Heavy ZM"),
    ("Mitsubishi Heavy", "mitsubishi_heavy_fdtc", "Mitsubishi Heavy FDTC"),
    ("Nibe", "nibe", "Nibe"),
    ("Olimpia Splendid", "olimpia", "Olimpia Splendid Maestro"),
    ("Panasonic", "panasonic_dke", "Panasonic DKE"),
    ("Panasonic", "panasonic_eke", "Panasonic EKE"),
    ("Panasonic", "panasonic_jke", "Panasonic JKE"),
    ("Panasonic", "panasonic_nke", "Panasonic NKE"),
    ("Panasonic", "panasonic_lke", "Panasonic LKE"),
    ("Panasonic", "panasonic_ckp", "Panasonic CKP (older)"),
    ("Philco", "philco_phs32", "Philco PHS32"),
    ("Samsung", "samsung_aqv", "Samsung AQV"),
    ("Samsung", "samsung_fjm", "Samsung FJM"),
    ("Sharp", "sharp", "Sharp AY-ZP40KR"),
    ("Toshiba", "toshiba", "Toshiba"),
    ("Toshiba", "toshiba_daiseikai", "Toshiba Daiseikai"),
]


def create_model(model_id: str) -> HeatpumpIRBase:
    """Instantiate a heatpump model implementation by ID.

    Raises KeyError if the model is unknown.
    """
    cls = _REGISTRY[model_id]
    return cls()


# ---------------------------------------------------------------------------
# Fan models (separate from the climate registry above — a fan is not a
# HeatpumpIRBase and has its own single-argument get_command(speed)).
# ---------------------------------------------------------------------------

_FAN_REGISTRY: dict[str, type[PanasonicCeilingFanIR]] = {
    "panasonic_ceiling_fan": PanasonicCeilingFanIR,
}

# Ordered list of (brand, model_id, display_name) used in the config flow
FAN_MODELS: list[tuple[str, str, str]] = [
    ("Panasonic", "panasonic_ceiling_fan", "Panasonic Ceiling Fan"),
]


def create_fan_model(model_id: str) -> PanasonicCeilingFanIR:
    """Instantiate a fan model implementation by ID.

    Raises KeyError if the model is unknown.
    """
    cls = _FAN_REGISTRY[model_id]
    return cls()
