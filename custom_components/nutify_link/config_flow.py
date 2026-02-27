"""Config flow for the Nutify Link UPS Monitor integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from .const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_USE_SSL,
    CONF_USERNAME,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_USE_SSL,
    DOMAIN,
)
from .coordinator import validate_connection

_LOGGER = logging.getLogger(__name__)


class NutifyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the multi-step config flow for Nutify."""

    VERSION = 1

    def __init__(self) -> None:
        self._connection_data: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Step 1: Connection details
    # ------------------------------------------------------------------

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial connection step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._connection_data = {
                CONF_HOST: user_input[CONF_HOST].strip(),
                CONF_PORT: user_input[CONF_PORT],
                CONF_USE_SSL: user_input[CONF_USE_SSL],
            }
            # Proceed to the authentication step
            return await self.async_step_auth()

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(
                    int, vol.Range(min=1, max=65535)
                ),
                vol.Required(CONF_USE_SSL, default=DEFAULT_USE_SSL): bool,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Step 2: Authentication credentials
    # ------------------------------------------------------------------

    async def async_step_auth(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the authentication step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            username = user_input.get(CONF_USERNAME, "").strip()
            password = user_input.get(CONF_PASSWORD, "")

            try:
                await validate_connection(
                    host=self._connection_data[CONF_HOST],
                    port=self._connection_data[CONF_PORT],
                    use_ssl=self._connection_data[CONF_USE_SSL],
                    username=username,
                    password=password,
                )
            except ConfigEntryAuthFailed:
                errors["base"] = "invalid_auth"
            except UpdateFailed:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during Nutify setup")
                errors["base"] = "unknown"
            else:
                config_data = {
                    **self._connection_data,
                    CONF_USERNAME: username,
                    CONF_PASSWORD: password,
                    CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
                }
                title = f"Nutify Link @ {self._connection_data[CONF_HOST]}"
                return self.async_create_entry(title=title, data=config_data)

        schema = vol.Schema(
            {
                vol.Optional(CONF_USERNAME, default=""): str,
                vol.Optional(CONF_PASSWORD, default=""): str,
                vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
                    int, vol.Range(min=DEFAULT_SCAN_INTERVAL, max=300)
                ),
            }
        )

        return self.async_show_form(
            step_id="auth",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "host": self._connection_data.get(CONF_HOST, ""),
            },
        )

    # ------------------------------------------------------------------
    # Re-auth flow (triggered by ConfigEntryAuthFailed)
    # ------------------------------------------------------------------

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Handle re-authentication when credentials become invalid."""
        self._connection_data = {
            CONF_HOST: entry_data[CONF_HOST],
            CONF_PORT: entry_data[CONF_PORT],
            CONF_USE_SSL: entry_data.get(CONF_USE_SSL, DEFAULT_USE_SSL),
        }
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle re-authentication confirmation."""
        errors: dict[str, str] = {}

        if user_input is not None:
            username = user_input.get(CONF_USERNAME, "").strip()
            password = user_input.get(CONF_PASSWORD, "")

            try:
                await validate_connection(
                    host=self._connection_data[CONF_HOST],
                    port=self._connection_data[CONF_PORT],
                    use_ssl=self._connection_data[CONF_USE_SSL],
                    username=username,
                    password=password,
                )
            except ConfigEntryAuthFailed:
                errors["base"] = "invalid_auth"
            except UpdateFailed:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during Nutify re-auth")
                errors["base"] = "unknown"
            else:
                entry = self.hass.config_entries.async_get_entry(
                    self.context["entry_id"]
                )
                if entry:
                    self.hass.config_entries.async_update_entry(
                        entry,
                        data={
                            **entry.data,
                            CONF_USERNAME: username,
                            CONF_PASSWORD: password,
                        },
                    )
                    await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        schema = vol.Schema(
            {
                vol.Optional(CONF_USERNAME, default=""): str,
                vol.Optional(CONF_PASSWORD, default=""): str,
            }
        )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "host": self._connection_data.get(CONF_HOST, ""),
            },
        )

    # ------------------------------------------------------------------
    # Options flow
    # ------------------------------------------------------------------

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> NutifyOptionsFlow:
        """Return the options flow handler."""
        return NutifyOptionsFlow(config_entry)


class NutifyOptionsFlow(OptionsFlow):
    """Handle options (accessible via the gear icon on the integration card)."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the integration options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self._config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self._config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )

        schema = vol.Schema(
            {
                vol.Required(CONF_SCAN_INTERVAL, default=current_interval): vol.All(
                    int, vol.Range(min=DEFAULT_SCAN_INTERVAL, max=300)
                ),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
        )
