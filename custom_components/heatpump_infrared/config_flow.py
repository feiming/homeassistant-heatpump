"""Config flow for the HeatpumpIR integration."""

from __future__ import annotations

from typing import Any

import probatio

from homeassistant.components.infrared import (
    DOMAIN as INFRARED_DOMAIN,
    async_get_emitters,
)
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_CONTROL_DEADBAND,
    CONF_CONTROL_INTERVAL,
    CONF_CONTROL_MAX_OFFSET,
    CONF_CONTROL_STRATEGY,
    CONF_DEVICE_TYPE,
    CONF_INFRARED_ENTITY_ID,
    CONF_MODEL,
    CONF_TEMPERATURE_SENSOR_ID,
    CONTROL_NONE,
    CONTROL_OFFSET,
    CONTROL_POWER,
    CONTROL_SETPOINT,
    DEFAULT_CONTROL_DEADBAND,
    DEFAULT_CONTROL_INTERVAL,
    DEFAULT_CONTROL_MAX_OFFSET,
    DEFAULT_CONTROL_STRATEGY,
    DEVICE_TYPE_CLIMATE,
    DEVICE_TYPE_FAN,
    DOMAIN,
)


class HeatpumpIRConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HeatpumpIR."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> HeatpumpIROptionsFlow:
        """Return the options flow for this handler."""
        return HeatpumpIROptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        from .ir import FAN_MODELS, MODELS  # noqa: PLC0415 — deferred to avoid import-time infrared_protocols dependency

        emitter_entity_ids = async_get_emitters(self.hass)
        if not emitter_entity_ids:
            return self.async_abort(reason="no_infrared_entities")

        fan_model_ids = {model_id for _, model_id, _ in FAN_MODELS}
        all_models = list(MODELS) + list(FAN_MODELS)

        errors: dict[str, str] = {}

        if user_input is not None:
            model_id = user_input[CONF_MODEL]
            emitter_id = user_input[CONF_INFRARED_ENTITY_ID]

            self._async_abort_entries_match(
                {CONF_MODEL: model_id, CONF_INFRARED_ENTITY_ID: emitter_id}
            )

            ent_reg = er.async_get(self.hass)
            entry = ent_reg.async_get(emitter_id)
            emitter_name = (
                entry.name or entry.original_name or emitter_id if entry else emitter_id
            )

            # Find the display name for the chosen model
            display_name = next(
                (dn for _, mid, dn in all_models if mid == model_id), model_id
            )

            device_type = (
                DEVICE_TYPE_FAN if model_id in fan_model_ids else DEVICE_TYPE_CLIMATE
            )

            title = f"{display_name} via {emitter_name}"
            return self.async_create_entry(
                title=title, data={**user_input, CONF_DEVICE_TYPE: device_type}
            )

        model_options = [
            SelectOptionDict(value=model_id, label=f"{brand} – {display_name}")
            for brand, model_id, display_name in all_models
        ]

        schema = probatio.Schema(
            {
                probatio.Required(CONF_MODEL): SelectSelector(
                    SelectSelectorConfig(
                        options=model_options,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                probatio.Required(CONF_INFRARED_ENTITY_ID): EntitySelector(
                    EntitySelectorConfig(
                        domain=INFRARED_DOMAIN,
                        include_entities=emitter_entity_ids,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )


class HeatpumpIROptionsFlow(OptionsFlowWithReload):
    """Handle options for a HeatpumpIR config entry.

    Only exposes the optional feedback temperature sensor — IR emitters send
    "fire and forget" commands, so this sensor is the only way to see
    whether the unit is actually responding.

    Saving changed options reloads the entry automatically.
    """

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            # Drop the sensor key entirely when cleared, so downstream `.get()`
            # sees no feedback sensor.
            if not user_input.get(CONF_TEMPERATURE_SENSOR_ID):
                user_input.pop(CONF_TEMPERATURE_SENSOR_ID, None)
            return self.async_create_entry(data=user_input)

        options = self.config_entry.options
        schema = probatio.Schema(
            {
                probatio.Optional(CONF_TEMPERATURE_SENSOR_ID): EntitySelector(
                    EntitySelectorConfig(domain="sensor", device_class="temperature")
                ),
                probatio.Required(
                    CONF_CONTROL_STRATEGY,
                    default=options.get(
                        CONF_CONTROL_STRATEGY, DEFAULT_CONTROL_STRATEGY
                    ),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            SelectOptionDict(value=CONTROL_NONE, label="Display only"),
                            SelectOptionDict(
                                value=CONTROL_OFFSET,
                                label="Offset compensation",
                            ),
                            SelectOptionDict(
                                value=CONTROL_POWER, label="Switch the unit off"
                            ),
                            SelectOptionDict(
                                value=CONTROL_SETPOINT, label="Change the setpoint"
                            ),
                        ],
                        mode=SelectSelectorMode.LIST,
                        translation_key=CONF_CONTROL_STRATEGY,
                    )
                ),
                probatio.Required(
                    CONF_CONTROL_DEADBAND,
                    default=options.get(
                        CONF_CONTROL_DEADBAND, DEFAULT_CONTROL_DEADBAND
                    ),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=0.1, max=5.0, step=0.1, mode=NumberSelectorMode.BOX
                    )
                ),
                probatio.Required(
                    CONF_CONTROL_MAX_OFFSET,
                    default=options.get(
                        CONF_CONTROL_MAX_OFFSET, DEFAULT_CONTROL_MAX_OFFSET
                    ),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=1.0, max=10.0, step=0.5, mode=NumberSelectorMode.BOX
                    )
                ),
                probatio.Required(
                    CONF_CONTROL_INTERVAL,
                    default=options.get(
                        CONF_CONTROL_INTERVAL, DEFAULT_CONTROL_INTERVAL
                    ),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=1, max=60, step=1, mode=NumberSelectorMode.BOX
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                schema,
                {CONF_TEMPERATURE_SENSOR_ID: options.get(CONF_TEMPERATURE_SENSOR_ID)},
            ),
        )
