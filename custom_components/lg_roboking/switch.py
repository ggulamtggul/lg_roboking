"""Switch platform for LG Roboking AI All-in-One Smart Turbo."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_DEVICE_ID, DOMAIN
from .coordinator import LGRobokingCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the LG Roboking Smart Turbo switch entity."""
    coordinator: LGRobokingCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([LGRobokingSmartTurboSwitch(coordinator, entry)])


class LGRobokingSmartTurboSwitch(CoordinatorEntity[LGRobokingCoordinator], SwitchEntity):
    """Representation of the LG Roboking Smart Turbo mode switch."""

    _attr_has_entity_name = False
    _attr_name = "로보킹 스마트 터보"
    _attr_icon = "mdi:car-turbocharger"

    def __init__(self, coordinator: LGRobokingCoordinator, entry: ConfigEntry) -> None:
        """Initialize the switch entity."""
        super().__init__(coordinator)
        self._device_id = entry.data[CONF_DEVICE_ID]
        self._attr_unique_id = f"{self._device_id}_smart_turbo"
        self.entity_id = "switch.lg_roboking_smart_turbo"

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
    def is_on(self) -> bool:
        """Return True if smart turbo mode is currently enabled."""
        data = self.coordinator.data or {}
        return bool(data.get("smart_turbo", False))

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on Smart Turbo mode."""
        _LOGGER.info("Enabling LG Roboking Smart Turbo")
        await self.coordinator.async_set_smart_turbo(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off Smart Turbo mode."""
        _LOGGER.info("Disabling LG Roboking Smart Turbo")
        await self.coordinator.async_set_smart_turbo(False)
