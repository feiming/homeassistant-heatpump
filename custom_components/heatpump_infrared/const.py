"""Constants for the HeatpumpIR integration."""

from __future__ import annotations

DOMAIN = "heatpump_infrared"

CONF_MODEL = "model"
CONF_INFRARED_ENTITY_ID = "infrared_entity_id"
CONF_DEVICE_TYPE = "device_type"
CONF_TEMPERATURE_SENSOR_ID = "temperature_sensor_entity_id"
CONF_CONTROL_STRATEGY = "control_strategy"
CONF_CONTROL_DEADBAND = "control_deadband"

# Values for CONF_CONTROL_STRATEGY — what to do when the feedback sensor says
# the target has been reached. Requires CONF_TEMPERATURE_SENSOR_ID to be set.
CONTROL_NONE = "none"  # display only, never override the unit (default)
CONTROL_POWER = "power"  # send power-off, resume on the previous mode
CONTROL_SETPOINT = "setpoint"  # push the setpoint to min/max, restore on demand

DEFAULT_CONTROL_STRATEGY = CONTROL_NONE
DEFAULT_CONTROL_DEADBAND = 0.5

# Values for CONF_DEVICE_TYPE. Entries created before this key existed have no
# device_type and are treated as climate for backward compatibility.
DEVICE_TYPE_CLIMATE = "climate"
DEVICE_TYPE_FAN = "fan"
