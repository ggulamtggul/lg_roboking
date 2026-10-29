"""StateVacuum platform for LG Roboking AI All-in-One via official ThinQ Web API."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.vacuum import (
    StateVacuumEntity,
    VacuumActivity,
    VacuumEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_DEVICE_ID,
    DOMAIN,
    LABEL_TO_SUCTION_LEVEL,
    SUCTION_LEVEL_OPTIONS,
    SUCTION_LEVEL_TO_LABEL,
)
from .coordinator import LGRobokingCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the LG Roboking Vacuum entity from a config entry."""
    coordinator: LGRobokingCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([LGRobokingVacuum(coordinator, entry)])


class LGRobokingVacuum(CoordinatorEntity[LGRobokingCoordinator], StateVacuumEntity):
    """Representation of the LG Roboking Robot Vacuum cleaner."""

    _attr_has_entity_name = False
    _attr_name = "LG 코드제로 로보킹 AI 올인원"
    _attr_icon = "mdi:robot-vacuum"

    _attr_supported_features = (
        VacuumEntityFeature.START
        | VacuumEntityFeature.PAUSE
        | VacuumEntityFeature.STOP
        | VacuumEntityFeature.RETURN_HOME
        | VacuumEntityFeature.FAN_SPEED
        | VacuumEntityFeature.LOCATE
        | VacuumEntityFeature.CLEAN_SPOT
    )

    def __init__(self, coordinator: LGRobokingCoordinator, entry: ConfigEntry) -> None:
        """Initialize the robot vacuum entity."""
        super().__init__(coordinator)
        self._device_id = entry.data[CONF_DEVICE_ID]
        self._attr_unique_id = f"{self._device_id}_vacuum"
        self.entity_id = "vacuum.lg_roboking"

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
    def activity(self) -> VacuumActivity | None:
        """Return current vacuum activity matching LG official state."""
        data = self.coordinator.data or {}
        snapshot = data.get("snapshot") if isinstance(data.get("snapshot"), dict) else data
        state = str(snapshot.get("ROBOT_STATE") or data.get("robot_state") or "").upper().strip()

        # Cleaning states
        if state in (
            "CLEAN_ZIGZAG",
            "CLEAN_EDGE",
            "CLEAN_SPIRAL",
            "CLEAN_SELECT",
            "CLEAN_SPECIFIED",
            "CLEAN_LEARNING",
            "CLEAN_MYSPOT",
            "WORKING",
            "RECOVERY_WORKING",
            "WATER_REMOVAL",
        ):
            return VacuumActivity.CLEANING

        # Paused states
        if state in (
            "PAUSE",
            "PAUSE_EDGE",
            "PAUSE_SPIRAL",
            "PAUSE_ZIGZAG",
            "PAUSE_SELECT",
            "PAUSE_LEARNING",
            "HOMING_PAUSE",
        ):
            return VacuumActivity.PAUSED

        # Returning to base / docking
        if state in ("HOMING", "DOCKING", "RECOVERY_HOMING", "HOMING_LEARNING"):
            return VacuumActivity.RETURNING

        # Docked at station / charging
        if state in ("CHARGING", "FINISHED_CHARGING", "STANDBY", "STATION", "STATION_MOP", "STATION_DRY"):
            return VacuumActivity.DOCKED

        # Sleeping or idle
        if state in ("SLEEP", "POWER_OFF", ""):
            return VacuumActivity.IDLE

        # Error
        if "ERROR" in state or "EMERGENCY" in state:
            return VacuumActivity.ERROR

        # Default fallback: if station is working, docked
        station_state = str(snapshot.get("STATION_STATE", "")).upper().strip()
        if station_state in ("START", "WORKING"):
            return VacuumActivity.DOCKED

        return VacuumActivity.IDLE

    @property
    def battery_level(self) -> int | None:
        """Return the battery level of the vacuum cleaner."""
        data = self.coordinator.data or {}
        snapshot = data.get("snapshot") if isinstance(data.get("snapshot"), dict) else data
        batt_str = snapshot.get("BATT_P") or data.get("battery_percent")
        if batt_str is not None:
            try:
                return int(float(batt_str))
            except (ValueError, TypeError):
                pass
        return None

    @property
    def fan_speed_list(self) -> list[str]:
        """Return the list of available fan speed / suction power levels."""
        return SUCTION_LEVEL_OPTIONS

    @property
    def fan_speed(self) -> str | None:
        """Return current fan speed / suction power level in Korean."""
        data = self.coordinator.data or {}
        snapshot = data.get("snapshot") if isinstance(data.get("snapshot"), dict) else data
        raw_code = snapshot.get("SUCTION_LEVEL") or data.get("suction_level", "STANDARD")
        return SUCTION_LEVEL_TO_LABEL.get(raw_code, "표준")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return detailed status attributes matching official LG ThinQ Web."""
        data = self.coordinator.data or {}
        snapshot = data.get("snapshot") if isinstance(data.get("snapshot"), dict) else data
        rt_map = snapshot.get("RT_MAP") or {}

        return {
            "robot_state_raw": snapshot.get("ROBOT_STATE"),
            "clean_mode": snapshot.get("CLEAN_TYPE"),
            "clean_distance": snapshot.get("ZZ_DIST"),
            "water_supply_level": snapshot.get("WATERSUPPLY_LEVEL"),
            "doorsill_climbing": snapshot.get("DOORSILLCLIMBING"),
            "repeat_clean": snapshot.get("REPEAT"),
            "smart_turbo": snapshot.get("SMART_TURBO"),
            "sweep_area_m2": rt_map.get("SWEEP_AREA"),
            "clean_time": snapshot.get("CLEAN_TIME"),
            "current_room_id": rt_map.get("CUR_ROOMID"),
            "station_state": snapshot.get("STATION_STATE"),
            "device_id": self._device_id,
        }

    async def async_start(self) -> None:
        """Start or resume cleaning."""
        _LOGGER.info("Starting LG Roboking cleaning via official ThinQ Web API")
        await self.coordinator.async_clean_start()

    async def async_pause(self) -> None:
        """Pause cleaning."""
        _LOGGER.info("Pausing LG Roboking cleaning via official ThinQ Web API")
        await self.coordinator.async_clean_pause()

    async def async_stop(self, **kwargs: Any) -> None:
        """Stop cleaning."""
        _LOGGER.info("Stopping LG Roboking cleaning via official ThinQ Web API")
        await self.coordinator.async_clean_stop()

    async def async_return_to_base(self, **kwargs: Any) -> None:
        """Return robot to base station (homing)."""
        _LOGGER.info("Returning LG Roboking to charging dock via official ThinQ Web API")
        await self.coordinator.async_homing()

    async def async_locate(self, **kwargs: Any) -> None:
        """Trigger robot locate announcement sound."""
        _LOGGER.info("Locating LG Roboking (triggering WHERE_IS_ROBOT sound)")
        await self.coordinator.async_where_is_robot()

    async def async_clean_spot(self, **kwargs: Any) -> None:
        """Start spot/focus cleaning."""
        _LOGGER.info("Starting LG Roboking spot cleaning (CLEAN_START_SPOT)")
        await self.coordinator.async_clean_spot()

    async def async_set_fan_speed(self, fan_speed: str, **kwargs: Any) -> None:
        """Set fan speed / suction power level."""
        api_code = LABEL_TO_SUCTION_LEVEL.get(fan_speed)
        if not api_code:
            if fan_speed.upper() in SUCTION_LEVEL_TO_LABEL:
                api_code = fan_speed.upper()
            else:
                raise ValueError(f"유효하지 않은 흡입력 옵션입니다: {fan_speed}")

        _LOGGER.info("Setting LG Roboking suction level to %s (%s)", fan_speed, api_code)
        await self.coordinator.async_set_suction_level(api_code)
