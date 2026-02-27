"""Binary sensor platform for the Nutify Link UPS Monitor integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NutifyCoordinator
from .sensor import build_device_info


# ---------------------------------------------------------------------------
# Extended entity description
# ---------------------------------------------------------------------------


@dataclass(frozen=True, kw_only=True)
class NutifyBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Extends BinarySensorEntityDescription with a value extraction function."""

    value_fn: Callable[[dict[str, Any]], bool | None]


# ---------------------------------------------------------------------------
# Helper: check whether a NUT status code is present in ups_status
# ---------------------------------------------------------------------------


def _status_contains(code: str) -> Callable[[dict[str, Any]], bool | None]:
    """Return a function that checks if a NUT status code is active."""
    def _check(data: dict[str, Any]) -> bool | None:
        raw = data.get("ups_status")
        if raw is None:
            return None
        return code in str(raw).split()
    return _check


# ---------------------------------------------------------------------------
# Binary sensor definitions
# ---------------------------------------------------------------------------

BINARY_SENSORS: tuple[NutifyBinarySensorEntityDescription, ...] = (
    NutifyBinarySensorEntityDescription(
        key="ups_online",
        name="Online",
        device_class=BinarySensorDeviceClass.POWER,
        value_fn=_status_contains("OL"),
    ),
    NutifyBinarySensorEntityDescription(
        key="ups_on_battery",
        name="On Battery",
        value_fn=_status_contains("OB"),
    ),
    NutifyBinarySensorEntityDescription(
        key="ups_low_battery",
        name="Low Battery",
        device_class=BinarySensorDeviceClass.BATTERY,
        value_fn=_status_contains("LB"),
    ),
    NutifyBinarySensorEntityDescription(
        key="ups_charging",
        name="Charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        value_fn=_status_contains("CHRG"),
    ),
    NutifyBinarySensorEntityDescription(
        key="ups_replace_battery",
        name="Replace Battery",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=_status_contains("RB"),
    ),
    NutifyBinarySensorEntityDescription(
        key="ups_overloaded",
        name="Overloaded",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=_status_contains("OVER"),
    ),
)


# ---------------------------------------------------------------------------
# Platform setup
# ---------------------------------------------------------------------------


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Nutify binary sensors from a config entry."""
    coordinator: NutifyCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        NutifyBinarySensor(coordinator, entry, description)
        for description in BINARY_SENSORS
    )


# ---------------------------------------------------------------------------
# Binary sensor entity
# ---------------------------------------------------------------------------


class NutifyBinarySensor(CoordinatorEntity[NutifyCoordinator], BinarySensorEntity):
    """A single Nutify UPS binary sensor derived from ups_status flags."""

    entity_description: NutifyBinarySensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NutifyCoordinator,
        entry: ConfigEntry,
        description: NutifyBinarySensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._entry = entry

    @property
    def device_info(self) -> DeviceInfo:
        return build_device_info(self.coordinator, self._entry)

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
