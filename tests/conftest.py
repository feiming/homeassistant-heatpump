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
     STATE_UNKNOWN="unknown",
     STATE_UNAVAILABLE="unavailable",
     UnitOfTemperature=_UnitOfTemperature)

# ── homeassistant.core ────────────────────────────────────────────────────
class _HomeAssistant: pass

class _State:
    def __init__(self, state, attributes=None):
        self.state = state
        self.attributes = attributes or {}

class _Event:
    def __init__(self, data=None):
        self.data = data or {}

class _EventStateChangedData: pass

def _callback(func):
    """Identity decorator, matching homeassistant.core.callback."""
    return func

_mod("homeassistant.core",
     HomeAssistant=_HomeAssistant,
     State=_State,
     Event=_Event,
     EventStateChangedData=_EventStateChangedData,
     callback=_callback)

# ── homeassistant.config_entries ──────────────────────────────────────────
class _ConfigEntry:
    entry_id = "test"
    data = {}
    options = {}

class _ConfigFlow: pass
class _ConfigFlowResult: pass
class _OptionsFlowWithConfigEntry:
    def __init__(self, config_entry):
        self._config_entry = config_entry
        self.options = dict(config_entry.options)

    @property
    def config_entry(self):
        return self._config_entry

_mod("homeassistant.config_entries",
     ConfigEntry=_ConfigEntry,
     ConfigFlow=_ConfigFlow,
     ConfigFlowResult=_ConfigFlowResult,
     OptionsFlowWithConfigEntry=_OptionsFlowWithConfigEntry)

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

class _HVACAction:
    OFF = "off"
    IDLE = "idle"
    HEATING = "heating"
    COOLING = "cooling"
    DRYING = "drying"
    FAN = "fan"

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
     HVACAction=_HVACAction,
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
_mod("homeassistant.helpers.event",
     async_track_state_change_event=lambda hass, entity_ids, cb: (lambda: None))
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
vol.Optional = lambda x, **kw: x
