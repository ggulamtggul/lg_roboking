"""Sensor platform for LG Roboking AI All-in-One via official ThinQ Web API."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_DEVICE_ID, DOMAIN
from .coordinator import LGRobokingCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up LG Roboking sensor entities from a config entry."""
    coordinator: LGRobokingCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([LGRobokingBatterySensor(coordinator, entry)])


class LGRobokingBatterySensor(CoordinatorEntity[LGRobokingCoordinator], SensorEntity):
    """Battery level of the robot (BATT_P in the ThinQ snapshot).

    Home Assistant dropped the vacuum entity's own battery property in 2025.8, so the
    level is exposed as a separate battery sensor on the same device.
    """

    _attr_has_entity_name = False
    _attr_name = "로보킹 배터리"
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, coordinator: LGRobokingCoordinator, entry: ConfigEntry) -> None:
        """Initialize the battery sensor."""
        super().__init__(coordinator)
        self._device_id = entry.data[CONF_DEVICE_ID]
        self._attr_unique_id = f"{self._device_id}_battery"
        self.entity_id = "sensor.lg_roboking_battery"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device registry information."""
        model = (self.coordinator.data or {}).get("model_name", "B-95AW.CKOR")
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name="LG 코드제로 로보킹 AI 올인원",
            manufacturer="LG Electronics",
            model=model,
        )

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        if self.coordinator.data and "snapshot" in self.coordinator.data:
            return True
        return self.coordinator.last_update_success

    @property
    def native_value(self) -> int | None:
        """Return the battery percentage, or None when the snapshot has none yet."""
        data = self.coordinator.data or {}
        snapshot = data.get("snapshot") if isinstance(data.get("snapshot"), dict) else data
        value = snapshot.get("BATT_P") or data.get("battery_percent")
        try:
            level = int(float(value))
        except (TypeError, ValueError):
            return None
        return level if 0 <= level <= 100 else None
