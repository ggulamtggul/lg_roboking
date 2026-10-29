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
        LGRobokingLightSwitch(coordinator, entry),
        LGRobokingAiDetectionSwitch(coordinator, entry),
        LGRobokingButtonLockSwitch(coordinator, entry),
        LGRobokingReCleanSwitch(coordinator, entry),
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

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        if self.coordinator.data and "snapshot" in self.coordinator.data:
            return True
        return self.coordinator.last_update_success


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
        return bool(str(snapshot.get("SMART_TURBO", "")).lower() == "true" or data.get("smart_turbo", False))

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on Smart Turbo mode."""
        _LOGGER.info("Enabling LG Roboking Smart Turbo")
        await self.coordinator.async_set_smart_turbo(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off Smart Turbo mode."""
        _LOGGER.info("Disabling LG Roboking Smart Turbo")
        await self.coordinator.async_set_smart_turbo(False)


class LGRobokingLightSwitch(LGRobokingBaseSwitch):
    """Switch for Robot Front Light (LIGHT)."""

    _attr_name = "로보킹 라이트"
    _attr_icon = "mdi:lightbulb"

    def __init__(self, coordinator: LGRobokingCoordinator, entry: ConfigEntry) -> None:
        """Initialize switch."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{self._device_id}_light"
        self.entity_id = "switch.lg_roboking_light"

    @property
    def is_on(self) -> bool:
        """Return True if front light is currently enabled."""
        data = self.coordinator.data or {}
        snapshot = data.get("snapshot") if isinstance(data.get("snapshot"), dict) else data
        val = snapshot.get("LIGHT")
        if isinstance(val, bool):
            return val
        return str(val).lower() == "true"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on Front Light."""
        _LOGGER.info("Enabling LG Roboking Front Light")
        await self.coordinator.async_set_light(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off Front Light."""
        _LOGGER.info("Disabling LG Roboking Front Light")
        await self.coordinator.async_set_light(False)


class LGRobokingAiDetectionSwitch(LGRobokingBaseSwitch):
    """Switch for AI Obstacle Detection (AI_DETECTION)."""

    _attr_name = "로보킹 AI 장애물 감지"
    _attr_icon = "mdi:eye-check"

    def __init__(self, coordinator: LGRobokingCoordinator, entry: ConfigEntry) -> None:
        """Initialize switch."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{self._device_id}_ai_detection"
        self.entity_id = "switch.lg_roboking_ai_detection"

    @property
    def is_on(self) -> bool:
        """Return True if AI obstacle detection is currently enabled."""
        data = self.coordinator.data or {}
        snapshot = data.get("snapshot") if isinstance(data.get("snapshot"), dict) else data
        val = snapshot.get("AI_DETECTION")
        if isinstance(val, bool):
            return val
        return str(val).lower() == "true"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on AI Detection."""
        _LOGGER.info("Enabling LG Roboking AI Detection")
        await self.coordinator.async_set_ai_detection(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off AI Detection."""
        _LOGGER.info("Disabling LG Roboking AI Detection")
        await self.coordinator.async_set_ai_detection(False)


class LGRobokingButtonLockSwitch(LGRobokingBaseSwitch):
    """Switch for Hardware Button Lock / Child Lock (BUTTON_LOCK)."""

    _attr_name = "로보킹 버튼 잠금"
    _attr_icon = "mdi:lock"

    def __init__(self, coordinator: LGRobokingCoordinator, entry: ConfigEntry) -> None:
        """Initialize switch."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{self._device_id}_button_lock"
        self.entity_id = "switch.lg_roboking_button_lock"

    @property
    def is_on(self) -> bool:
        """Return True if button lock is currently enabled."""
        data = self.coordinator.data or {}
        snapshot = data.get("snapshot") if isinstance(data.get("snapshot"), dict) else data
        val = snapshot.get("BUTTON_LOCK")
        if isinstance(val, bool):
            return val
        return str(val).lower() == "true"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on Button Lock."""
        _LOGGER.info("Enabling LG Roboking Button Lock")
        await self.coordinator.async_set_button_lock(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off Button Lock."""
        _LOGGER.info("Disabling LG Roboking Button Lock")
        await self.coordinator.async_set_button_lock(False)


class LGRobokingReCleanSwitch(LGRobokingBaseSwitch):
    """Switch for Resume Cleaning After Recharge (TOGGLE_RECLEAN)."""

    _attr_name = "로보킹 충전 후 청소 재개"
    _attr_icon = "mdi:battery-sync"

    def __init__(self, coordinator: LGRobokingCoordinator, entry: ConfigEntry) -> None:
        """Initialize switch."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{self._device_id}_reclean"
        self.entity_id = "switch.lg_roboking_reclean"

    @property
    def is_on(self) -> bool:
        """Return True if resume clean after recharge is enabled."""
        data = self.coordinator.data or {}
        snapshot = data.get("snapshot") if isinstance(data.get("snapshot"), dict) else data
        val = snapshot.get("TOGGLE_RECLEAN") or snapshot.get("RECLEAN")
        if isinstance(val, bool):
            return val
        return str(val).lower() == "true"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on Resume Cleaning."""
        _LOGGER.info("Enabling LG Roboking Resume Clean")
        await self.coordinator.async_set_toggle_reclean(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off Resume Cleaning."""
        _LOGGER.info("Disabling LG Roboking Resume Clean")
        await self.coordinator.async_set_toggle_reclean(False)
