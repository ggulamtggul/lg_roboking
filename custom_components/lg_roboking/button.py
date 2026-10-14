"""Button platform for manual cloud synchronization of LG Roboking."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
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
    """Set up the LG Roboking Button entity."""
    coordinator: LGRobokingCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([LGRobokingSyncButton(coordinator, entry)])


class LGRobokingSyncButton(CoordinatorEntity[LGRobokingCoordinator], ButtonEntity):
    """Button to trigger an immediate sync from LG ThinQ cloud."""

    _attr_has_entity_name = False
    _attr_name = "로보킹 클라우드 상태 동기화"
    _attr_icon = "mdi:cloud-refresh"

    def __init__(self, coordinator: LGRobokingCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sync button."""
        super().__init__(coordinator)
        self._device_id = entry.data[CONF_DEVICE_ID]
        self._attr_unique_id = f"{self._device_id}_sync_cloud"
        self.entity_id = "button.lg_roboking_sync_from_cloud"

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

    async def async_press(self) -> None:
        """Handle the button press to sync latest CLEAN_TYPE from LG cloud."""
        await self.coordinator.async_request_refresh()
