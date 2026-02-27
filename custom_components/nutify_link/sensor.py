"""Sensor platform for the Nutify Link UPS Monitor integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricPotential,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, UPS_STATUS_MAP
from .coordinator import NutifyCoordinator


# ---------------------------------------------------------------------------
# Extended entity description
# ---------------------------------------------------------------------------


@dataclass(frozen=True, kw_only=True)
class NutifySensorEntityDescription(SensorEntityDescription):
    """Extends SensorEntityDescription with a value extraction function."""

    value_fn: Callable[[dict[str, Any]], Any]
    optional: bool = False  # If True, sensor is skipped when data field is absent


# ---------------------------------------------------------------------------
# Helper: safe numeric extraction
# ---------------------------------------------------------------------------


def _as_float(data: dict[str, Any], key: str) -> float | None:
    """Return a float from data[key], or None if missing/invalid."""
    raw = data.get(key)
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _runtime_minutes(data: dict[str, Any]) -> float | None:
    """Convert battery_runtime (seconds) to minutes."""
    seconds = _as_float(data, "battery_runtime")
    if seconds is None:
        return None
    return round(seconds / 60, 1)


def _ups_status_display(data: dict[str, Any]) -> str | None:
    """Translate NUT status codes to a human-readable string."""
    raw = data.get("ups_status")
    if raw is None:
        return None
    # Status can be space-separated flags, e.g. "OL CHRG"
    parts = str(raw).split()
    translated = [UPS_STATUS_MAP.get(p, p) for p in parts]
    return " / ".join(translated)


# ---------------------------------------------------------------------------
# Sensor definitions
# ---------------------------------------------------------------------------

SENSORS: tuple[NutifySensorEntityDescription, ...] = (
    # ---- Battery ----
    NutifySensorEntityDescription(
        key="battery_charge",
        name="Battery Charge",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _as_float(d, "battery_charge"),
    ),
    NutifySensorEntityDescription(
        key="battery_runtime",
        name="Battery Runtime",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_runtime_minutes,
    ),
    NutifySensorEntityDescription(
        key="battery_voltage",
        name="Battery Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _as_float(d, "battery_voltage"),
    ),
    NutifySensorEntityDescription(
        key="battery_temperature",
        name="Battery Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _as_float(d, "battery_temperature"),
        optional=True,
    ),
    # ---- Power ----
    NutifySensorEntityDescription(
        key="ups_load",
        name="UPS Load",
        device_class=SensorDeviceClass.POWER_FACTOR,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _as_float(d, "ups_load"),
    ),
    NutifySensorEntityDescription(
        key="ups_real_power",
        name="Real Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _as_float(d, "ups_realpower"),
    ),
    NutifySensorEntityDescription(
        key="ups_apparent_power",
        name="Apparent Power",
        device_class=SensorDeviceClass.APPARENT_POWER,
        native_unit_of_measurement="VA",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _as_float(d, "ups_power"),
    ),
    NutifySensorEntityDescription(
        key="ups_nominal_power",
        name="Nominal Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _as_float(d, "ups_realpower_nominal"),
    ),
    NutifySensorEntityDescription(
        key="ups_efficiency",
        name="UPS Efficiency",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _as_float(d, "ups_efficiency"),
    ),
    # ---- Voltage & Frequency ----
    NutifySensorEntityDescription(
        key="input_voltage",
        name="Input Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _as_float(d, "input_voltage"),
    ),
    NutifySensorEntityDescription(
        key="output_voltage",
        name="Output Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _as_float(d, "output_voltage"),
    ),
    NutifySensorEntityDescription(
        key="input_frequency",
        name="Input Frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _as_float(d, "input_frequency"),
    ),
    NutifySensorEntityDescription(
        key="output_frequency",
        name="Output Frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _as_float(d, "output_frequency"),
    ),
    # ---- Status ----
    NutifySensorEntityDescription(
        key="ups_status",
        name="UPS Status",
        value_fn=lambda d: d.get("ups_status"),
    ),
    NutifySensorEntityDescription(
        key="ups_status_display",
        name="UPS Status Display",
        value_fn=_ups_status_display,
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
    """Set up Nutify sensors from a config entry."""
    coordinator: NutifyCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        NutifySensor(coordinator, entry, description)
        for description in SENSORS
        if not description.optional or description.value_fn(coordinator.data) is not None
    )


# ---------------------------------------------------------------------------
# Sensor entity
# ---------------------------------------------------------------------------


class NutifySensor(CoordinatorEntity[NutifyCoordinator], SensorEntity):
    """A single Nutify UPS sensor."""

    entity_description: NutifySensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NutifyCoordinator,
        entry: ConfigEntry,
        description: NutifySensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Nutify Link UPS",
            manufacturer="NUT / Nutify Link",
            model=self._get_model(),
            configuration_url=(
                f"{'https' if entry.data.get('use_ssl') else 'http'}://"
                f"{entry.data['host']}:{entry.data['port']}"
            ),
        )

    def _get_model(self) -> str | None:
        """Derive UPS model name from coordinator data if available."""
        if self.coordinator.data:
            return self.coordinator.data.get("device_model") or self.coordinator.data.get("ups_model")
        return None

    @property
    def native_value(self) -> Any:
        """Return the sensor value extracted from coordinator data."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def available(self) -> bool:
        """Sensor is available when coordinator has data and the value is not None."""
        if not super().available:
            return False
        if self.coordinator.data is None:
            return False
        # For sensors that might simply not be supported by this UPS model,
        # we still return True so HA shows the entity (as "unavailable state").
        return True
