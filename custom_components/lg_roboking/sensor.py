"""Sensor platform for LG Roboking AI All-in-One via official ThinQ Web API.

These values are already in the ThinQ snapshot the coordinator polls; before this
platform they were either unused or only visible as vacuum attributes.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfArea, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_DEVICE_ID, DOMAIN
from .coordinator import LGRobokingCoordinator

# Official app wording for ROBOT_STATE (modelJson Value + Korean language pack).
ROBOT_STATE_LABELS = {
    "STANDBY": "대기 중", "PAUSE": "일시 정지", "PAUSE_EDGE": "일시정지 중",
    "PAUSE_SPIRAL": "일시정지 중", "PAUSE_ZIGZAG": "일시정지 중", "PAUSE_SELECT": "일시정지 중",
    "PAUSE_LEARNING": "일시 정지", "PAUSE_SELECT_GOZONE": "일시 정지", "HOMING_PAUSE": "일시정지 중",
    "BACKMOVING_JOY": "준비 중", "BACKMOVING_INIT": "준비 중", "MONITORING": "준비 중",
    "INITAILIZING": "준비 중", "RECOVERY_WORKING": "준비 중", "REPOSITIONING": "위치 확인 중",
    "CHARGING": "충전 중", "FINISHED_CHARGING": "충전 완료",
    "HOMING": "충전대로 이동 중", "HOMING_LEARNING": "충전대로 이동 중", "DOCKING": "충전대로 이동 중",
    "RECOVERY_HOMING": "충전대로 이동 중",
    "WORKING": "청소 중", "CLEAN_EDGE": "꼼꼼 청소 중", "CLEAN_SPIRAL": "집중청소 중",
    "CLEAN_SELECT": "선택한 방 청소 중", "CLEAN_SPECIFIED": "선택한 구역 청소 중",
    "CLEAN_SELECT_GOZONE": "선택한 구역 청소 중", "CLEAN_ZIGZAG": "퀵 청소 중",
    "CLEAN_LEARNING": "새 도면 그리는 중", "CLEAN_MYSPOT": "구역 청소 중",
    "DIAGNOSIS": "스마트 진단 중", "MONITORING_POSITIONING": "홈가드 위치 지정 중",
    "MONITORING_MOVING": "지정된 위치로 이동 중", "MONITORING_DETECTING": "홈가드 중",
    "SETDATE": "리모컨 사용 중", "MACROSECTOR": "리모컨 사용 중", "RESERVATION": "리모컨 사용 중",
    "SLEEP": "절전 모드 실행 중", "WATER_REMOVAL": "잔수 제거 중", "MYSPOT_RECORDING": "구역 녹화 중",
    "STATION": "먼지통 비우는 중", "STATION_MOP": "물걸레 세척 중", "STATION_DRY": "물걸레 건조 중",
    "WATER_INJECTION": "물 채우는 중",
}
VOLUME_LABELS = {"MUTE": "무음", "LOW": "작게", "MEDIUM": "보통", "HIGH": "크게"}


def _snapshot(data: dict[str, Any]) -> dict[str, Any]:
    return data.get("snapshot") if isinstance(data.get("snapshot"), dict) else data


def _int(value: Any) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _battery(s: dict[str, Any]) -> int | None:
    level = _int(s.get("BATT_P"))
    return level if level is not None and 0 <= level <= 100 else None


def _maint(key: str) -> Callable[[dict[str, Any]], int | None]:
    """Remaining life in % from MAINT_* = "used|limit" (the app's consumable gauge)."""
    def value(s: dict[str, Any]) -> int | None:
        parts = str(s.get(key) or "").split("|")
        used, limit = (_int(parts[0]), _int(parts[1])) if len(parts) == 2 else (None, None)
        if used is None or not limit or limit <= 0:
            return None
        return max(0, min(100, round(100 - used * 100 / limit)))
    return value


def _maint_attrs(key: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def attrs(s: dict[str, Any]) -> dict[str, Any]:
        parts = str(s.get(key) or "").split("|")
        if len(parts) != 2:
            return {}
        return {"used": _int(parts[0]), "limit": _int(parts[1])}
    return attrs


def _dry_end(s: dict[str, Any]) -> datetime | None:
    """Mop drying finish time, only while the station is drying (the app's countdown)."""
    if str(s.get("ROBOT_STATE") or "").upper() != "STATION_DRY":
        return None
    info = s.get("MOPDRY_INFO") or {}
    start, hours = _int(info.get("START_TIME")), _int(info.get("TIME"))
    if not start or not hours or start < 1_000_000_000:
        return None
    return datetime.fromtimestamp(start, tz=timezone.utc) + timedelta(hours=hours)


def _dnd(s: dict[str, Any]) -> str | None:
    info = s.get("DND_INFO") or {}
    if not info:
        return None
    if str(info.get("SET", "")).upper() != "ON":
        return "꺼짐"
    return f"{info.get('START_TIME', '?')}~{info.get('END_TIME', '?')}"


@dataclass(frozen=True, kw_only=True)
class RobokingSensorDescription(SensorEntityDescription):
    """A sensor read from the ThinQ snapshot."""

    value_fn: Callable[[dict[str, Any]], Any]
    attrs_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


SENSORS: tuple[RobokingSensorDescription, ...] = (
    RobokingSensorDescription(
        key="battery", name="로보킹 배터리",
        device_class=SensorDeviceClass.BATTERY, state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE, value_fn=_battery,
    ),
    RobokingSensorDescription(
        key="status", name="로보킹 상태", icon="mdi:robot-vacuum",
        value_fn=lambda s: ROBOT_STATE_LABELS.get(str(s.get("ROBOT_STATE") or "").upper(), s.get("ROBOT_STATE")),
        attrs_fn=lambda s: {"raw": s.get("ROBOT_STATE"), "station_state": s.get("STATION_STATE")},
    ),
    RobokingSensorDescription(
        key="mop_dry_end", name="로보킹 물걸레 건조 완료 예정",
        device_class=SensorDeviceClass.TIMESTAMP, icon="mdi:weather-windy", value_fn=_dry_end,
    ),
    RobokingSensorDescription(
        key="mop_dry_hours", name="로보킹 물걸레 건조 시간 설정",
        native_unit_of_measurement=UnitOfTime.HOURS, icon="mdi:timer-cog-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: _int((s.get("MOPDRY_INFO") or {}).get("TIME")),
    ),
    RobokingSensorDescription(
        key="clean_time", name="로보킹 청소 시간",
        native_unit_of_measurement=UnitOfTime.MINUTES, icon="mdi:timer-outline",
        value_fn=lambda s: _int(s.get("CLEAN_TIME")),
    ),
    RobokingSensorDescription(
        key="clean_area", name="로보킹 청소 면적",
        native_unit_of_measurement=UnitOfArea.SQUARE_METERS, icon="mdi:texture-box",
        value_fn=lambda s: _int((s.get("RT_MAP") or {}).get("SWEEP_AREA")),
    ),
    *(
        RobokingSensorDescription(
            key=f"maint_{name}", name=f"로보킹 {label} 남은 수명",
            native_unit_of_measurement=PERCENTAGE, state_class=SensorStateClass.MEASUREMENT,
            icon=icon, value_fn=_maint(f"MAINT_{key}"), attrs_fn=_maint_attrs(f"MAINT_{key}"),
        )
        for name, key, label, icon in (
            ("dustbag", "DUSTBAG", "먼지봉투", "mdi:delete-variant"),
            ("filter", "FILTER", "필터", "mdi:air-filter"),
            ("main_brush", "MAINBRUSH", "메인 브러시", "mdi:brush"),
            ("side_brush", "SIDEBRUSH", "사이드 브러시", "mdi:broom"),
            ("mop", "MOP", "물걸레", "mdi:water-outline"),
        )
    ),
    RobokingSensorDescription(
        key="volume", name="로보킹 음량", icon="mdi:volume-medium",
        value_fn=lambda s: VOLUME_LABELS.get(str(s.get("VOLUME_LEVEL") or "").upper(), s.get("VOLUME_LEVEL")),
    ),
    RobokingSensorDescription(
        key="do_not_disturb", name="로보킹 방해 금지", icon="mdi:sleep", value_fn=_dnd,
    ),
    RobokingSensorDescription(
        key="firmware", name="로보킹 펌웨어 버전", icon="mdi:chip",
        entity_category=EntityCategory.DIAGNOSTIC, value_fn=lambda s: s.get("VERSION"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up LG Roboking sensor entities from a config entry."""
    coordinator: LGRobokingCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(LGRobokingSensor(coordinator, entry, d) for d in SENSORS)


class LGRobokingSensor(CoordinatorEntity[LGRobokingCoordinator], SensorEntity):
    """A value from the ThinQ snapshot."""

    _attr_has_entity_name = False
    entity_description: RobokingSensorDescription

    def __init__(
        self,
        coordinator: LGRobokingCoordinator,
        entry: ConfigEntry,
        description: RobokingSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._device_id = entry.data[CONF_DEVICE_ID]
        self._attr_unique_id = f"{self._device_id}_{description.key}"
        self.entity_id = f"sensor.lg_roboking_{description.key}"

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
    def native_value(self) -> Any:
        """Return the value from the current snapshot."""
        return self.entity_description.value_fn(_snapshot(self.coordinator.data or {}))

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return raw details where they help (consumable counters, raw state)."""
        if self.entity_description.attrs_fn is None:
            return None
        return self.entity_description.attrs_fn(_snapshot(self.coordinator.data or {}))
