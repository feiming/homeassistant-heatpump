"""Config flow for the HeatpumpIR integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.infrared import (
    DOMAIN as INFRARED_DOMAIN,
    async_get_emitters,
)
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import CONF_INFRARED_ENTITY_ID, CONF_MODEL, DOMAIN


class HeatpumpIRConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HeatpumpIR."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        from .ir import MODELS  # noqa: PLC0415 — deferred to avoid import-time infrared_protocols dependency

        emitter_entity_ids = async_get_emitters(self.hass)
        if not emitter_entity_ids:
            return self.async_abort(reason="no_infrared_entities")

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
                (dn for _, mid, dn in MODELS if mid == model_id), model_id
            )

            title = f"{display_name} via {emitter_name}"
            return self.async_create_entry(title=title, data=user_input)

        model_options = [
            SelectOptionDict(value=model_id, label=f"{brand} – {display_name}")
            for brand, model_id, display_name in MODELS
        ]

        schema = vol.Schema(
            {
                vol.Required(CONF_MODEL): SelectSelector(
                    SelectSelectorConfig(
                        options=model_options,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(CONF_INFRARED_ENTITY_ID): EntitySelector(
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
