"""Constants for the HeatpumpIR integration."""

from __future__ import annotations

DOMAIN = "heatpump_infrared"

CONF_MODEL = "model"
CONF_INFRARED_ENTITY_ID = "infrared_entity_id"
CONF_DEVICE_TYPE = "device_type"
CONF_TEMPERATURE_SENSOR_ID = "temperature_sensor_entity_id"

# Values for CONF_DEVICE_TYPE. Entries created before this key existed have no
# device_type and are treated as climate for backward compatibility.
DEVICE_TYPE_CLIMATE = "climate"
DEVICE_TYPE_FAN = "fan"
