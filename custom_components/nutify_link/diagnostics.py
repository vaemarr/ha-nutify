"""Diagnostics support for Nutify Link."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_PASSWORD, DOMAIN
from .coordinator import NutifyCoordinator


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: NutifyCoordinator = hass.data[DOMAIN][entry.entry_id]

    config_data = dict(entry.data)
    config_data.pop(CONF_PASSWORD, None)  # Redact password

    return {
        "config": config_data,
        "options": dict(entry.options),
        "coordinator_data": coordinator.data,
    }
