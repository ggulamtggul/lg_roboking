"""Select platform for LG Roboking AI All-in-One settings and controls."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CLEAN_TYPE_OPTIONS,
    CLEAN_TYPE_TO_LABEL,
    CONF_DEVICE_ID,
    DOMAIN,
    LABEL_TO_CLEAN_TYPE,
    LABEL_TO_SUCTION_LEVEL,
    LABEL_TO_WATER_SUPPLY,
    LABEL_TO_ZZ_DIST,
    SUCTION_LEVEL_OPTIONS,
    SUCTION_LEVEL_TO_LABEL,
    WATER_SUPPLY_OPTIONS,
    WATER_SUPPLY_TO_LABEL,
    ZZ_DIST_OPTIONS,
    ZZ_DIST_TO_LABEL,
)
from .coordinator import LGRobokingCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up all LG Roboking Select entities from a config entry."""
    coordinator: LGRobokingCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        LGRobokingCleanTypeSelect(coordinator, entry),
        LGRobokingSuctionSelect(coordinator, entry),
        LGRobokingZzDistSelect(coordinator, entry),
        LGRobokingWaterSupplySelect(coordinator, entry),
    ])


class LGRobokingBaseSelect(CoordinatorEntity[LGRobokingCoordinator], SelectEntity):
    """Base select entity with shared device info and device ID."""

    _attr_has_entity_name = False

    def __init__(self, coordinator: LGRobokingCoordinator, entry: ConfigEntry) -> None:
        """Initialize base select entity."""
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


class LGRobokingCleanTypeSelect(LGRobokingBaseSelect):
    """Representation of LG Roboking Clean Mode Select entity."""

    _attr_name = "로보킹 청소 방식"
    _attr_icon = "mdi:robot-vacuum"
    _attr_options = CLEAN_TYPE_OPTIONS

    def __init__(self, coordinator: LGRobokingCoordinator, entry: ConfigEntry) -> None:
        """Initialize clean mode select."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{self._device_id}_clean_type"
        self.entity_id = "select.lg_roboking_mode"

    @property
    def current_option(self) -> str | None:
        """Return current clean mode in Korean."""
        raw_code = (self.coordinator.data or {}).get("clean_type", "SUCTION")
        return CLEAN_TYPE_TO_LABEL.get(raw_code, "먼지 흡입")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        data = self.coordinator.data or {}
        return {
            "clean_type_code": data.get("clean_type", "SUCTION"),
            "device_id": self._device_id,
        }

    async def async_select_option(self, option: str) -> None:
        """Change the selected cleaning mode and push to LG ThinQ cloud."""
        api_code = LABEL_TO_CLEAN_TYPE.get(option)
        if not api_code:
            if option.upper() in CLEAN_TYPE_TO_LABEL:
                api_code = option.upper()
            else:
                raise ValueError(f"유효하지 않은 청소 방식 옵션입니다: {option}")

        _LOGGER.info("Setting LG Roboking clean mode to %s (%s)", option, api_code)
        await self.coordinator.async_set_clean_type(api_code)


class LGRobokingSuctionSelect(LGRobokingBaseSelect):
    """Representation of LG Roboking Suction Power Select entity."""

    _attr_name = "로보킹 흡입 세기"
    _attr_icon = "mdi:fan"
    _attr_options = SUCTION_LEVEL_OPTIONS

    def __init__(self, coordinator: LGRobokingCoordinator, entry: ConfigEntry) -> None:
        """Initialize suction level select."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{self._device_id}_suction_level"
        self.entity_id = "select.lg_roboking_suction_power"

    @property
    def current_option(self) -> str | None:
        """Return current suction level in Korean."""
        raw_code = (self.coordinator.data or {}).get("suction_level", "STANDARD")
        return SUCTION_LEVEL_TO_LABEL.get(raw_code, "표준")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        data = self.coordinator.data or {}
        return {
            "suction_level_code": data.get("suction_level", "STANDARD"),
            "device_id": self._device_id,
        }

    async def async_select_option(self, option: str) -> None:
        """Change suction level."""
        api_code = LABEL_TO_SUCTION_LEVEL.get(option)
        if not api_code:
            if option.upper() in SUCTION_LEVEL_TO_LABEL:
                api_code = option.upper()
            else:
                raise ValueError(f"유효하지 않은 흡입 세기 옵션입니다: {option}")

        _LOGGER.info("Setting LG Roboking suction level to %s (%s)", option, api_code)
        await self.coordinator.async_set_suction_level(api_code)


class LGRobokingZzDistSelect(LGRobokingBaseSelect):
    """Representation of LG Roboking Clean Spacing Select entity."""

    _attr_name = "로보킹 청소 간격"
    _attr_icon = "mdi:arrow-expand-horizontal"
    _attr_options = ZZ_DIST_OPTIONS

    def __init__(self, coordinator: LGRobokingCoordinator, entry: ConfigEntry) -> None:
        """Initialize clean spacing select."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{self._device_id}_zz_dist"
        self.entity_id = "select.lg_roboking_clean_distance"

    @property
    def current_option(self) -> str | None:
        """Return current clean spacing in Korean."""
        raw_code = (self.coordinator.data or {}).get("zz_dist", "NORMAL")
        return ZZ_DIST_TO_LABEL.get(raw_code, "기본")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        data = self.coordinator.data or {}
        return {
            "zz_dist_code": data.get("zz_dist", "NORMAL"),
            "device_id": self._device_id,
        }

    async def async_select_option(self, option: str) -> None:
        """Change cleaning spacing."""
        api_code = LABEL_TO_ZZ_DIST.get(option)
        if not api_code:
            if option.upper() in ZZ_DIST_TO_LABEL:
                api_code = option.upper()
            else:
                raise ValueError(f"유효하지 않은 청소 간격 옵션입니다: {option}")

        _LOGGER.info("Setting LG Roboking cleaning distance to %s (%s)", option, api_code)
        await self.coordinator.async_set_zz_dist(api_code)


class LGRobokingWaterSupplySelect(LGRobokingBaseSelect):
    """Representation of LG Roboking Water Supply Level Select entity."""

    _attr_name = "로보킹 물걸레 물 공급량"
    _attr_icon = "mdi:water-opacity"
    _attr_options = WATER_SUPPLY_OPTIONS

    def __init__(self, coordinator: LGRobokingCoordinator, entry: ConfigEntry) -> None:
        """Initialize water supply select."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{self._device_id}_water_supply_level"
        self.entity_id = "select.lg_roboking_water_level"

    @property
    def current_option(self) -> str | None:
        """Return current water supply level in Korean."""
        raw_code = (self.coordinator.data or {}).get("water_supply_level", "LOW1")
        return WATER_SUPPLY_TO_LABEL.get(raw_code, "보통 (2단계)")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        data = self.coordinator.data or {}
        return {
            "water_supply_code": data.get("water_supply_level", "LOW1"),
            "device_id": self._device_id,
        }

    async def async_select_option(self, option: str) -> None:
        """Change water supply level."""
        api_code = LABEL_TO_WATER_SUPPLY.get(option)
        if not api_code:
            if option.upper() in WATER_SUPPLY_TO_LABEL:
                api_code = option.upper()
            else:
                raise ValueError(f"유효하지 않은 물 공급량 옵션입니다: {option}")

        _LOGGER.info("Setting LG Roboking water supply to %s (%s)", option, api_code)
        await self.coordinator.async_set_water_supply_level(api_code)
