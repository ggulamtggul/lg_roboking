"""Select platform for LG Roboking AI All-in-One cleaning mode."""
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
)
from .coordinator import LGRobokingCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the LG Roboking Select entity from a config entry."""
    coordinator: LGRobokingCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([LGRobokingCleanTypeSelect(coordinator, entry)])


class LGRobokingCleanTypeSelect(CoordinatorEntity[LGRobokingCoordinator], SelectEntity):
    """Representation of LG Roboking Clean Mode Select entity."""

    _attr_has_entity_name = False
    _attr_name = "로보킹 청소 방식"
    _attr_icon = "mdi:robot-vacuum"
    _attr_options = CLEAN_TYPE_OPTIONS

    def __init__(self, coordinator: LGRobokingCoordinator, entry: ConfigEntry) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._device_id = entry.data[CONF_DEVICE_ID]
        self._attr_unique_id = f"{self._device_id}_clean_type"
        self.entity_id = "select.lg_roboking_mode"

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
    def current_option(self) -> str | None:
        """Return the current selected clean mode in Korean."""
        raw_code = (self.coordinator.data or {}).get("clean_type", "SUCTION")
        return CLEAN_TYPE_TO_LABEL.get(raw_code, "먼지 흡입")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes including raw API clean_type code."""
        data = self.coordinator.data or {}
        raw_code = data.get("clean_type", "SUCTION")
        return {
            "clean_type_code": raw_code,
            "device_id": self._device_id,
        }

    async def async_select_option(self, option: str) -> None:
        """Change the selected cleaning mode and push immediately to LG ThinQ cloud."""
        api_code = LABEL_TO_CLEAN_TYPE.get(option)
        if not api_code:
            # Also support passing raw codes ("ALL", "SUCTION", "MOP")
            if option.upper() in CLEAN_TYPE_TO_LABEL:
                api_code = option.upper()
            else:
                raise ValueError(f"유효하지 않은 청소 방식 옵션입니다: {option}")

        _LOGGER.info("Setting LG Roboking clean mode to %s (%s)", option, api_code)
        await self.coordinator.async_set_clean_type(api_code)
