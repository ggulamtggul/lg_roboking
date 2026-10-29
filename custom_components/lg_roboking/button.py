"""Button platform for LG Roboking AI All-in-One controls via official ThinQ Web API."""
from __future__ import annotations

import logging
from homeassistant.components.button import ButtonEntity
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
    """Set up all LG Roboking Button entities from a config entry."""
    coordinator: LGRobokingCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        # Cleaning Control Buttons
        LGRobokingStartCleanButton(coordinator, entry),
        LGRobokingPauseButton(coordinator, entry),
        LGRobokingStopButton(coordinator, entry),
        LGRobokingHomingButton(coordinator, entry),
        LGRobokingLocateButton(coordinator, entry),
        LGRobokingSpotCleanButton(coordinator, entry),

        # All-in-One Station Control Buttons
        LGRobokingDustCollectStartButton(coordinator, entry),
        LGRobokingDustCollectStopButton(coordinator, entry),
        LGRobokingMopWashStartButton(coordinator, entry),
        LGRobokingMopWashStopButton(coordinator, entry),
        LGRobokingMopDryStartButton(coordinator, entry),
        LGRobokingMopDryStopButton(coordinator, entry),

        # System & Utility Buttons
        LGRobokingWakeUpButton(coordinator, entry),
        LGRobokingSyncButton(coordinator, entry),
    ])


class LGRobokingBaseButton(CoordinatorEntity[LGRobokingCoordinator], ButtonEntity):
    """Base class for LG Roboking button entities."""

    _attr_has_entity_name = False

    def __init__(self, coordinator: LGRobokingCoordinator, entry: ConfigEntry) -> None:
        """Initialize the base button."""
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


# ==========================================
# 1. Cleaning Control Buttons
# ==========================================

class LGRobokingStartCleanButton(LGRobokingBaseButton):
    """Button to start cleaning."""

    _attr_name = "로보킹 청소 시작"
    _attr_icon = "mdi:play-circle"

    def __init__(self, coordinator: LGRobokingCoordinator, entry: ConfigEntry) -> None:
        """Initialize button."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{self._device_id}_btn_clean_start"
        self.entity_id = "button.lg_roboking_clean_start"

    async def async_press(self) -> None:
        """Handle button press."""
        await self.coordinator.async_clean_start()


class LGRobokingPauseButton(LGRobokingBaseButton):
    """Button to pause cleaning."""

    _attr_name = "로보킹 청소 일시정지"
    _attr_icon = "mdi:pause-circle"

    def __init__(self, coordinator: LGRobokingCoordinator, entry: ConfigEntry) -> None:
        """Initialize button."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{self._device_id}_btn_clean_pause"
        self.entity_id = "button.lg_roboking_clean_pause"

    async def async_press(self) -> None:
        """Handle button press."""
        await self.coordinator.async_clean_pause()


class LGRobokingStopButton(LGRobokingBaseButton):
    """Button to stop cleaning."""

    _attr_name = "로보킹 청소 정지"
    _attr_icon = "mdi:stop-circle"

    def __init__(self, coordinator: LGRobokingCoordinator, entry: ConfigEntry) -> None:
        """Initialize button."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{self._device_id}_btn_clean_stop"
        self.entity_id = "button.lg_roboking_clean_stop"

    async def async_press(self) -> None:
        """Handle button press."""
        await self.coordinator.async_clean_stop()


class LGRobokingHomingButton(LGRobokingBaseButton):
    """Button to return robot vacuum to base dock."""

    _attr_name = "로보킹 충전 복귀"
    _attr_icon = "mdi:home-import-outline"

    def __init__(self, coordinator: LGRobokingCoordinator, entry: ConfigEntry) -> None:
        """Initialize button."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{self._device_id}_btn_homing"
        self.entity_id = "button.lg_roboking_return_home"

    async def async_press(self) -> None:
        """Handle button press."""
        await self.coordinator.async_homing()


class LGRobokingLocateButton(LGRobokingBaseButton):
    """Button to trigger location sound on robot vacuum."""

    _attr_name = "로보킹 위치 찾기 (소리)"
    _attr_icon = "mdi:crosshairs-gps"

    def __init__(self, coordinator: LGRobokingCoordinator, entry: ConfigEntry) -> None:
        """Initialize button."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{self._device_id}_btn_locate"
        self.entity_id = "button.lg_roboking_locate"

    async def async_press(self) -> None:
        """Handle button press."""
        await self.coordinator.async_where_is_robot()


class LGRobokingSpotCleanButton(LGRobokingBaseButton):
    """Button to start spot/focus cleaning around current location."""

    _attr_name = "로보킹 집중 청소"
    _attr_icon = "mdi:target"

    def __init__(self, coordinator: LGRobokingCoordinator, entry: ConfigEntry) -> None:
        """Initialize button."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{self._device_id}_btn_clean_spot"
        self.entity_id = "button.lg_roboking_clean_spot"

    async def async_press(self) -> None:
        """Handle button press."""
        await self.coordinator.async_clean_spot()


# ==========================================
# 2. All-in-One Station Control Buttons
# ==========================================

class LGRobokingDustCollectStartButton(LGRobokingBaseButton):
    """Button to start station dust collection."""

    _attr_name = "로보킹 먼지통 비움 시작"
    _attr_icon = "mdi:delete-sweep"

    def __init__(self, coordinator: LGRobokingCoordinator, entry: ConfigEntry) -> None:
        """Initialize button."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{self._device_id}_btn_dust_start"
        self.entity_id = "button.lg_roboking_station_dust_start"

    async def async_press(self) -> None:
        """Handle button press."""
        await self.coordinator.async_station_dust_collect(start=True)


class LGRobokingDustCollectStopButton(LGRobokingBaseButton):
    """Button to stop station dust collection."""

    _attr_name = "로보킹 먼지통 비움 정지"
    _attr_icon = "mdi:delete-off"

    def __init__(self, coordinator: LGRobokingCoordinator, entry: ConfigEntry) -> None:
        """Initialize button."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{self._device_id}_btn_dust_stop"
        self.entity_id = "button.lg_roboking_station_dust_stop"

    async def async_press(self) -> None:
        """Handle button press."""
        await self.coordinator.async_station_dust_collect(start=False)


class LGRobokingMopWashStartButton(LGRobokingBaseButton):
    """Button to start mop washing at all-in-one station."""

    _attr_name = "로보킹 물걸레 세척 시작"
    _attr_icon = "mdi:washing-machine"

    def __init__(self, coordinator: LGRobokingCoordinator, entry: ConfigEntry) -> None:
        """Initialize button."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{self._device_id}_btn_mop_wash_start"
        self.entity_id = "button.lg_roboking_mop_wash_start"

    async def async_press(self) -> None:
        """Handle button press."""
        await self.coordinator.async_mop_wash(start=True)


class LGRobokingMopWashStopButton(LGRobokingBaseButton):
    """Button to stop mop washing at all-in-one station."""

    _attr_name = "로보킹 물걸레 세척 정지"
    _attr_icon = "mdi:washing-machine-off"

    def __init__(self, coordinator: LGRobokingCoordinator, entry: ConfigEntry) -> None:
        """Initialize button."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{self._device_id}_btn_mop_wash_stop"
        self.entity_id = "button.lg_roboking_mop_wash_stop"

    async def async_press(self) -> None:
        """Handle button press."""
        await self.coordinator.async_mop_wash(start=False)


class LGRobokingMopDryStartButton(LGRobokingBaseButton):
    """Button to start mop hot-air drying at station."""

    _attr_name = "로보킹 물걸레 열풍건조 시작"
    _attr_icon = "mdi:weather-sunny"

    def __init__(self, coordinator: LGRobokingCoordinator, entry: ConfigEntry) -> None:
        """Initialize button."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{self._device_id}_btn_mop_dry_start"
        self.entity_id = "button.lg_roboking_mop_dry_start"

    async def async_press(self) -> None:
        """Handle button press."""
        await self.coordinator.async_mop_dry(start=True)


class LGRobokingMopDryStopButton(LGRobokingBaseButton):
    """Button to stop mop hot-air drying at station."""

    _attr_name = "로보킹 물걸레 열풍건조 정지"
    _attr_icon = "mdi:weather-sunny-off"

    def __init__(self, coordinator: LGRobokingCoordinator, entry: ConfigEntry) -> None:
        """Initialize button."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{self._device_id}_btn_mop_dry_stop"
        self.entity_id = "button.lg_roboking_mop_dry_stop"

    async def async_press(self) -> None:
        """Handle button press."""
        await self.coordinator.async_mop_dry(start=False)


# ==========================================
# 3. System & Utility Buttons
# ==========================================

class LGRobokingWakeUpButton(LGRobokingBaseButton):
    """Button to wake up LG Roboking from sleep mode."""

    _attr_name = "로보킹 절전 해제"
    _attr_icon = "mdi:power-sleep"

    def __init__(self, coordinator: LGRobokingCoordinator, entry: ConfigEntry) -> None:
        """Initialize the wake up button."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{self._device_id}_wake_up"
        self.entity_id = "button.lg_roboking_wake_up"

    async def async_press(self) -> None:
        """Handle the button press to wake up LG Roboking."""
        await self.coordinator.async_wake_up()


class LGRobokingSyncButton(LGRobokingBaseButton):
    """Button to trigger an immediate sync from LG ThinQ cloud."""

    _attr_name = "로보킹 클라우드 동기화"
    _attr_icon = "mdi:cloud-refresh"

    def __init__(self, coordinator: LGRobokingCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sync button."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{self._device_id}_sync_cloud"
        self.entity_id = "button.lg_roboking_sync_from_cloud"

    async def async_press(self) -> None:
        """Handle the button press to sync latest status from LG cloud."""
        await self.coordinator.async_request_refresh()
