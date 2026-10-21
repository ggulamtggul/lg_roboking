"""Camera platform for LG Roboking AI All-in-One real-time map."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.camera import Camera
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
    """Set up the LG Roboking Map Camera entity from a config entry."""
    coordinator: LGRobokingCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([LGRobokingMapCamera(coordinator, entry)])


class LGRobokingMapCamera(CoordinatorEntity[LGRobokingCoordinator], Camera):
    """Representation of the LG Roboking Live Map Camera."""

    _attr_has_entity_name = False
    _attr_name = "로보킹 맵"
    _attr_icon = "mdi:map-legend"
    _attr_content_type = "image/png"

    def __init__(self, coordinator: LGRobokingCoordinator, entry: ConfigEntry) -> None:
        """Initialize the map camera entity."""
        CoordinatorEntity.__init__(self, coordinator)
        Camera.__init__(self)
        self._device_id = entry.data[CONF_DEVICE_ID]
        self._attr_unique_id = f"{self._device_id}_map_camera"
        self.entity_id = "camera.roboking_map"

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

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return bytes of the latest rendered map PNG image."""
        try:
            return await self.coordinator.async_get_or_render_map()
        except Exception as err:
            _LOGGER.error("Failed to generate Roboking map image: %s", err)
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return map metadata and robot navigation telemetry."""
        data = self.coordinator.data or {}
        snapshot = data.get("snapshot", {})
        rt_map = snapshot.get("RT_MAP", {})
        rt_pose = snapshot.get("RT_POSE", {})
        vw = snapshot.get("VW", {})

        return {
            "current_room_id": rt_map.get("CUR_ROOMID"),
            "sweep_area_m2": rt_map.get("SWEEP_AREA"),
            "robot_position": rt_pose.get("CUR_POS"),
            "dock_position": rt_map.get("HOME_POS"),
            "restricted_zones_count": vw.get("NUM", 0),
            "is_cleaning": self.coordinator.is_robot_active(),
            "device_id": self._device_id,
        }
