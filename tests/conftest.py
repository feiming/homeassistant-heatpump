"""Stub out homeassistant modules so IR tests run without a full HA install."""

import sys
import types


def _mod(name, **attrs):
    m = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules[name] = m
    return m


class _Stub:
    """Generic stub that absorbs any attribute access."""
    def __init__(self, *a, **kw): pass
    def __call__(self, *a, **kw): return self
    def __getattr__(self, name): return self


# ── homeassistant.const ────────────────────────────────────────────────────
class _Platform:
    CLIMATE = "climate"

class _UnitOfTemperature:
    CELSIUS = "°C"

_mod("homeassistant.const",
     Platform=_Platform,
     ATTR_TEMPERATURE="temperature",
     UnitOfTemperature=_UnitOfTemperature)

# ── homeassistant.core ────────────────────────────────────────────────────
class _HomeAssistant: pass

_mod("homeassistant.core", HomeAssistant=_HomeAssistant)

# ── homeassistant.config_entries ──────────────────────────────────────────
class _ConfigEntry:
    entry_id = "test"
    data = {}

class _ConfigFlow: pass
class _ConfigFlowResult: pass

_mod("homeassistant.config_entries",
     ConfigEntry=_ConfigEntry,
     ConfigFlow=_ConfigFlow,
     ConfigFlowResult=_ConfigFlowResult)

# ── homeassistant.components.climate ─────────────────────────────────────
class _ClimateEntityFeature:
    TARGET_TEMPERATURE = 1
    FAN_MODE = 2
    SWING_MODE = 4
    TURN_ON = 8
    TURN_OFF = 16

class _HVACMode:
    OFF = "off"
    HEAT = "heat"
    COOL = "cool"
    DRY = "dry"
    FAN_ONLY = "fan_only"
    HEAT_COOL = "heat_cool"

_mod("homeassistant.components.climate",
     FAN_AUTO="auto",
     FAN_DIFFUSE="diffuse",
     FAN_HIGH="high",
     FAN_LOW="low",
     FAN_MEDIUM="medium",
     SWING_BOTH="both",
     SWING_HORIZONTAL="horizontal",
     SWING_OFF="off",
     SWING_VERTICAL="vertical",
     ClimateEntity=_Stub,
     ClimateEntityFeature=_ClimateEntityFeature,
     HVACMode=_HVACMode)

# ── homeassistant.components.infrared ────────────────────────────────────
class _InfraredEmitterConsumerEntity:
    _infrared_emitter_entity_id = None
    async def _send_command(self, cmd): pass
    async def async_added_to_hass(self): pass

_mod("homeassistant.components.infrared",
     DOMAIN="infrared",
     async_get_emitters=lambda hass: [],
     InfraredEmitterConsumerEntity=_InfraredEmitterConsumerEntity)

# ── homeassistant.components (parent) ────────────────────────────────────
_mod("homeassistant.components")

# ── homeassistant.helpers.* ───────────────────────────────────────────────
class _RestoreEntity:
    async def async_get_last_state(self): return None

_mod("homeassistant.helpers.restore_state", RestoreEntity=_RestoreEntity)
_mod("homeassistant.helpers.entity_platform",
     AddConfigEntryEntitiesCallback=object)
_mod("homeassistant.helpers.device_registry", DeviceInfo=dict)
_mod("homeassistant.helpers.entity_registry", async_get=lambda hass: None)
_mod("homeassistant.helpers.selector",
     EntitySelector=_Stub,
     EntitySelectorConfig=_Stub,
     SelectOptionDict=dict,
     SelectSelector=_Stub,
     SelectSelectorConfig=_Stub,
     SelectSelectorMode=type("SelectSelectorMode", (), {"DROPDOWN": "dropdown"}))
_mod("homeassistant.helpers")

# ── homeassistant (root) ─────────────────────────────────────────────────
_mod("homeassistant")

# ── voluptuous ────────────────────────────────────────────────────────────
vol = _mod("voluptuous")
vol.Schema = lambda x, **kw: x
vol.Required = lambda x, **kw: x
