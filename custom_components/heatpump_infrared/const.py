"""Constants for the HeatpumpIR integration."""

from __future__ import annotations

DOMAIN = "heatpump_infrared"

CONF_MODEL = "model"
CONF_INFRARED_ENTITY_ID = "infrared_entity_id"
CONF_DEVICE_TYPE = "device_type"
CONF_TEMPERATURE_SENSOR_ID = "temperature_sensor_entity_id"
CONF_CONTROL_STRATEGY = "control_strategy"
CONF_CONTROL_DEADBAND = "control_deadband"
CONF_CONTROL_MAX_OFFSET = "control_max_offset"
CONF_CONTROL_INTERVAL = "control_interval"

# Values for CONF_CONTROL_STRATEGY — how the feedback sensor influences the
# unit. Requires CONF_TEMPERATURE_SENSOR_ID to be set.
CONTROL_NONE = "none"  # display only, never override the unit
CONTROL_OFFSET = "offset"  # bias the setpoint to close the loop on the sensor
CONTROL_POWER = "power"  # send power-off, resume on the previous mode
CONTROL_SETPOINT = "setpoint"  # push the setpoint to min/max, restore on demand

# Display-only by default; the user opts in to a closed-loop strategy.
DEFAULT_CONTROL_STRATEGY = CONTROL_NONE

DEFAULT_CONTROL_DEADBAND = 0.5
# Max °C the offset strategy will bias the setpoint away from the target.
DEFAULT_CONTROL_MAX_OFFSET = 3.0
# Minutes to wait between offset adjustments, giving the room time to react.
DEFAULT_CONTROL_INTERVAL = 10

# Values for CONF_DEVICE_TYPE. Entries created before this key existed have no
# device_type and are treated as climate for backward compatibility.
DEVICE_TYPE_CLIMATE = "climate"
DEVICE_TYPE_FAN = "fan"
