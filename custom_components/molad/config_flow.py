"""Config flow for Molad."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME

from .const import DOMAIN, DEFAULT_NAME, DEFAULT_DIASPORA


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Molad config flow."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        if user_input is not None:
            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data={"diaspora": user_input["diaspora"]},
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                    vol.Required("diaspora", default=DEFAULT_DIASPORA): bool,
                }
            ),
        )
