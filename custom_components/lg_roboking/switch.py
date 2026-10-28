"""Switch platform for LG Roboking AI All-in-One settings via official ThinQ Web API."""
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
    """Set up all LG Roboking switch entities from a config entry."""
    coordinator: LGRobokingCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        LGRobokingSmartTurboSwitch(coordinator, entry),
        LGRobokingDoorsillSwitch(coordinator, entry),
        LGRobokingRepeatSwitch(coordinator, entry),
    ])


class LGRobokingBaseSwitch(CoordinatorEntity[LGRobokingCoordinator], SwitchEntity):
    """Base class for LG Roboking switch entities."""

    _attr_has_entity_name = False

    def __init__(self, coordinator: LGRobokingCoordinator, entry: ConfigEntry) -> None:
        """Initialize switch entity."""
        super().__init__(coordinator)
        self._device_id = entry.data[CONF_DEVICE_ID]

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


class LGRobokingSmartTurboSwitch(LGRobokingBaseSwitch):
    """Switch for Smart Turbo (Carpet Boost) mode."""

    _attr_name = "로보킹 스마트 터보"
    _attr_icon = "mdi:car-turbocharger"

    def __init__(self, coordinator: LGRobokingCoordinator, entry: ConfigEntry) -> None:
        """Initialize switch."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{self._device_id}_smart_turbo"
        self.entity_id = "switch.lg_roboking_smart_turbo"

    @property
    def is_on(self) -> bool:
        """Return True if smart turbo mode is currently enabled."""
        data = self.coordinator.data or {}
        snapshot = data.get("snapshot") if isinstance(data.get("snapshot"), dict) else data
        return bool(snapshot.get("SMART_TURBO") == "true" or data.get("smart_turbo", False))

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on Smart Turbo mode."""
        _LOGGER.info("Enabling LG Roboking Smart Turbo")
        await self.coordinator.async_set_smart_turbo(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off Smart Turbo mode."""
        _LOGGER.info("Disabling LG Roboking Smart Turbo")
        await self.coordinator.async_set_smart_turbo(False)


class LGRobokingDoorsillSwitch(LGRobokingBaseSwitch):
    """Switch for Doorsill Climbing mode."""

    _attr_name = "로보킹 문턱 넘기"
    _attr_icon = "mdi:stairs"

    def __init__(self, coordinator: LGRobokingCoordinator, entry: ConfigEntry) -> None:
        """Initialize switch."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{self._device_id}_doorsill_climbing"
        self.entity_id = "switch.lg_roboking_doorsill_climbing"

    @property
    def is_on(self) -> bool:
        """Return True if doorsill climbing is currently enabled."""
        data = self.coordinator.data or {}
        snapshot = data.get("snapshot") if isinstance(data.get("snapshot"), dict) else data
        return bool(snapshot.get("DOORSILLCLIMBING") in ("true", True, "On", "on"))

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on Doorsill Climbing mode."""
        _LOGGER.info("Enabling LG Roboking Doorsill Climbing")
        await self.coordinator.async_set_doorsill_climbing(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off Doorsill Climbing mode."""
        _LOGGER.info("Disabling LG Roboking Doorsill Climbing")
        await self.coordinator.async_set_doorsill_climbing(False)


class LGRobokingRepeatSwitch(LGRobokingBaseSwitch):
    """Switch for Repeat Cleaning mode."""

    _attr_name = "로보킹 반복 청소"
    _attr_icon = "mdi:repeat"

    def __init__(self, coordinator: LGRobokingCoordinator, entry: ConfigEntry) -> None:
        """Initialize switch."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{self._device_id}_repeat_clean"
        self.entity_id = "switch.lg_roboking_repeat_clean"

    @property
    def is_on(self) -> bool:
        """Return True if repeat clean is currently enabled."""
        data = self.coordinator.data or {}
        snapshot = data.get("snapshot") if isinstance(data.get("snapshot"), dict) else data
        return bool(snapshot.get("REPEAT") in ("true", True, "On", "on"))

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on Repeat Cleaning mode."""
        _LOGGER.info("Enabling LG Roboking Repeat Clean")
        await self.coordinator.async_set_repeat(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off Repeat Cleaning mode."""
        _LOGGER.info("Disabling LG Roboking Repeat Clean")
        await self.coordinator.async_set_repeat(False)
