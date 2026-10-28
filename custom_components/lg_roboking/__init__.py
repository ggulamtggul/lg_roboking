"""LG Roboking AI All-in-One Home Assistant custom integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import (
    ATTR_ENABLED,
    ATTR_LEVEL,
    ATTR_MODE,
    ATTR_ROOM_IDS,
    CLEAN_TYPE_TO_LABEL,
    DOMAIN,
    LABEL_TO_CLEAN_TYPE,
    LABEL_TO_SUCTION_LEVEL,
    LABEL_TO_WATER_SUPPLY,
    LABEL_TO_ZZ_DIST,
    PLATFORMS,
    SERVICE_CLEAN_ROOMS,
    SERVICE_CLEAN_SPOT,
    SERVICE_CLEAN_START,
    SERVICE_CLEAN_STOP,
    SERVICE_DUST_COLLECT,
    SERVICE_LOCATE,
    SERVICE_MOP_DRY,
    SERVICE_MOP_WASH,
    SERVICE_PAUSE,
    SERVICE_RETURN_TO_BASE,
    SERVICE_SET_CLEAN_MODE,
    SERVICE_SET_DOORSILL_CLIMBING,
    SERVICE_SET_REPEAT,
    SERVICE_SET_LIGHT,
    SERVICE_SET_AI_DETECTION,
    SERVICE_SET_BUTTON_LOCK,
    SERVICE_SET_TOGGLE_RECLEAN,
    SERVICE_SET_SMART_TURBO,
    SERVICE_SET_SUCTION_LEVEL,
    SERVICE_SET_WATER_LEVEL,
    SERVICE_SET_ZZ_DIST,
    SERVICE_WAKE_UP,
    SUCTION_LEVEL_TO_LABEL,
    WATER_SUPPLY_TO_LABEL,
    ZZ_DIST_TO_LABEL,
)
from .coordinator import LGRobokingCoordinator

_LOGGER = logging.getLogger(__name__)

SERVICE_SET_MODE_SCHEMA = vol.Schema({
    vol.Required(ATTR_MODE): cv.string,
})

SERVICE_SET_LEVEL_SCHEMA = vol.Schema({
    vol.Required(ATTR_LEVEL): cv.string,
})

SERVICE_SET_BOOL_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENABLED): cv.boolean,
})

SERVICE_CLEAN_ROOMS_SCHEMA = vol.Schema({
    vol.Required(ATTR_ROOM_IDS): vol.All(cv.ensure_list, [vol.Coerce(int)]),
})

SERVICE_ACTION_START_SCHEMA = vol.Schema({
    vol.Optional("start", default=True): cv.boolean,
})


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up LG Roboking AI All-in-One from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    coordinator = LGRobokingCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    def _get_coordinators() -> list[LGRobokingCoordinator]:
        return [
            c for c in hass.data.get(DOMAIN, {}).values()
            if isinstance(c, LGRobokingCoordinator)
        ]

    # 1. Clean Start
    if not hass.services.has_service(DOMAIN, SERVICE_CLEAN_START):
        async def async_handle_clean_start(_: ServiceCall) -> None:
            for coord in _get_coordinators():
                await coord.async_clean_start()
        hass.services.async_register(DOMAIN, SERVICE_CLEAN_START, async_handle_clean_start)

    # 2. Pause
    if not hass.services.has_service(DOMAIN, SERVICE_PAUSE):
        async def async_handle_pause(_: ServiceCall) -> None:
            for coord in _get_coordinators():
                await coord.async_clean_pause()
        hass.services.async_register(DOMAIN, SERVICE_PAUSE, async_handle_pause)

    # 3. Clean Stop
    if not hass.services.has_service(DOMAIN, SERVICE_CLEAN_STOP):
        async def async_handle_clean_stop(_: ServiceCall) -> None:
            for coord in _get_coordinators():
                await coord.async_clean_stop()
        hass.services.async_register(DOMAIN, SERVICE_CLEAN_STOP, async_handle_clean_stop)

    # 4. Return to Base (Homing)
    if not hass.services.has_service(DOMAIN, SERVICE_RETURN_TO_BASE):
        async def async_handle_homing(_: ServiceCall) -> None:
            for coord in _get_coordinators():
                await coord.async_homing()
        hass.services.async_register(DOMAIN, SERVICE_RETURN_TO_BASE, async_handle_homing)

    # 5. Locate Robot
    if not hass.services.has_service(DOMAIN, SERVICE_LOCATE):
        async def async_handle_locate(_: ServiceCall) -> None:
            for coord in _get_coordinators():
                await coord.async_where_is_robot()
        hass.services.async_register(DOMAIN, SERVICE_LOCATE, async_handle_locate)

    # 6. Spot Clean
    if not hass.services.has_service(DOMAIN, SERVICE_CLEAN_SPOT):
        async def async_handle_spot(_: ServiceCall) -> None:
            for coord in _get_coordinators():
                await coord.async_clean_spot()
        hass.services.async_register(DOMAIN, SERVICE_CLEAN_SPOT, async_handle_spot)

    # 7. Clean Selected Rooms
    if not hass.services.has_service(DOMAIN, SERVICE_CLEAN_ROOMS):
        async def async_handle_clean_rooms(call: ServiceCall) -> None:
            room_ids = call.data[ATTR_ROOM_IDS]
            for coord in _get_coordinators():
                await coord.async_clean_rooms(room_ids)
        hass.services.async_register(
            DOMAIN, SERVICE_CLEAN_ROOMS, async_handle_clean_rooms, schema=SERVICE_CLEAN_ROOMS_SCHEMA
        )

    # 8. Station Dust Collection
    if not hass.services.has_service(DOMAIN, SERVICE_DUST_COLLECT):
        async def async_handle_dust(call: ServiceCall) -> None:
            start = call.data.get("start", True)
            for coord in _get_coordinators():
                await coord.async_station_dust_collect(start=start)
        hass.services.async_register(
            DOMAIN, SERVICE_DUST_COLLECT, async_handle_dust, schema=SERVICE_ACTION_START_SCHEMA
        )

    # 9. Station Mop Wash
    if not hass.services.has_service(DOMAIN, SERVICE_MOP_WASH):
        async def async_handle_mop_wash(call: ServiceCall) -> None:
            start = call.data.get("start", True)
            for coord in _get_coordinators():
                await coord.async_mop_wash(start=start)
        hass.services.async_register(
            DOMAIN, SERVICE_MOP_WASH, async_handle_mop_wash, schema=SERVICE_ACTION_START_SCHEMA
        )

    # 10. Station Mop Hot-Air Dry
    if not hass.services.has_service(DOMAIN, SERVICE_MOP_DRY):
        async def async_handle_mop_dry(call: ServiceCall) -> None:
            start = call.data.get("start", True)
            for coord in _get_coordinators():
                await coord.async_mop_dry(start=start)
        hass.services.async_register(
            DOMAIN, SERVICE_MOP_DRY, async_handle_mop_dry, schema=SERVICE_ACTION_START_SCHEMA
        )

    # 11. Clean Type
    if not hass.services.has_service(DOMAIN, SERVICE_SET_CLEAN_MODE):
        async def async_handle_set_clean_mode(call: ServiceCall) -> None:
            raw_input = call.data[ATTR_MODE].strip()
            api_code = LABEL_TO_CLEAN_TYPE.get(raw_input, raw_input.upper())
            if api_code not in CLEAN_TYPE_TO_LABEL:
                raise ValueError(
                    f"유효하지 않은 청소 모드입니다: {raw_input} (ALL, SUCTION, MOP 중 하나를 선택하세요)"
                )
            for coord in _get_coordinators():
                await coord.async_set_clean_type(api_code)

        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_CLEAN_MODE,
            async_handle_set_clean_mode,
            schema=SERVICE_SET_MODE_SCHEMA,
        )

    # 12. Suction Level
    if not hass.services.has_service(DOMAIN, SERVICE_SET_SUCTION_LEVEL):
        async def async_handle_set_suction(call: ServiceCall) -> None:
            raw_input = call.data[ATTR_LEVEL].strip()
            api_code = LABEL_TO_SUCTION_LEVEL.get(raw_input, raw_input.upper())
            if api_code not in SUCTION_LEVEL_TO_LABEL:
                raise ValueError(
                    f"유효하지 않은 흡입력 레벨입니다: {raw_input} ({', '.join(SUCTION_LEVEL_TO_LABEL.keys())} 중 하나를 선택하세요)"
                )
            for coord in _get_coordinators():
                await coord.async_set_suction_level(api_code)

        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_SUCTION_LEVEL,
            async_handle_set_suction,
            schema=SERVICE_SET_LEVEL_SCHEMA,
        )

    # 13. ZZ Dist (Cleaning Spacing)
    if not hass.services.has_service(DOMAIN, SERVICE_SET_ZZ_DIST):
        async def async_handle_set_zz_dist(call: ServiceCall) -> None:
            raw_input = call.data[ATTR_LEVEL].strip()
            api_code = LABEL_TO_ZZ_DIST.get(raw_input, raw_input.upper())
            if api_code not in ZZ_DIST_TO_LABEL:
                raise ValueError(
                    f"유효하지 않은 청소 간격입니다: {raw_input} ({', '.join(ZZ_DIST_TO_LABEL.keys())} 중 하나를 선택하세요)"
                )
            for coord in _get_coordinators():
                await coord.async_set_zz_dist(api_code)

        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_ZZ_DIST,
            async_handle_set_zz_dist,
            schema=SERVICE_SET_LEVEL_SCHEMA,
        )

    # 14. Water Supply Level
    if not hass.services.has_service(DOMAIN, SERVICE_SET_WATER_LEVEL):
        async def async_handle_set_water_level(call: ServiceCall) -> None:
            raw_input = call.data[ATTR_LEVEL].strip()
            api_code = LABEL_TO_WATER_SUPPLY.get(raw_input, raw_input.upper())
            if api_code not in WATER_SUPPLY_TO_LABEL:
                raise ValueError(
                    f"유효하지 않은 물공급 레벨입니다: {raw_input} ({', '.join(WATER_SUPPLY_TO_LABEL.keys())} 중 하나를 선택하세요)"
                )
            for coord in _get_coordinators():
                await coord.async_set_water_supply_level(api_code)

        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_WATER_LEVEL,
            async_handle_set_water_level,
            schema=SERVICE_SET_LEVEL_SCHEMA,
        )

    # 15. Smart Turbo
    if not hass.services.has_service(DOMAIN, SERVICE_SET_SMART_TURBO):
        async def async_handle_set_turbo(call: ServiceCall) -> None:
            enabled = call.data[ATTR_ENABLED]
            for coord in _get_coordinators():
                await coord.async_set_smart_turbo(enabled)

        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_SMART_TURBO,
            async_handle_set_turbo,
            schema=SERVICE_SET_BOOL_SCHEMA,
        )

    # 16. Doorsill Climbing
    if not hass.services.has_service(DOMAIN, SERVICE_SET_DOORSILL_CLIMBING):
        async def async_handle_doorsill(call: ServiceCall) -> None:
            enabled = call.data[ATTR_ENABLED]
            for coord in _get_coordinators():
                await coord.async_set_doorsill_climbing(enabled)

        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_DOORSILL_CLIMBING,
            async_handle_doorsill,
            schema=SERVICE_SET_BOOL_SCHEMA,
        )

    # 17. Repeat Clean
    if not hass.services.has_service(DOMAIN, SERVICE_SET_REPEAT):
        async def async_handle_repeat(call: ServiceCall) -> None:
            enabled = call.data[ATTR_ENABLED]
            for coord in _get_coordinators():
                await coord.async_set_repeat(enabled)

        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_REPEAT,
            async_handle_repeat,
            schema=SERVICE_SET_BOOL_SCHEMA,
        )

    # 18. Light Mode
    if not hass.services.has_service(DOMAIN, SERVICE_SET_LIGHT):
        async def async_handle_light(call: ServiceCall) -> None:
            enabled = call.data[ATTR_ENABLED]
            for coord in _get_coordinators():
                await coord.async_set_light(enabled)

        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_LIGHT,
            async_handle_light,
            schema=SERVICE_SET_BOOL_SCHEMA,
        )

    # 19. AI Obstacle Detection
    if not hass.services.has_service(DOMAIN, SERVICE_SET_AI_DETECTION):
        async def async_handle_ai(call: ServiceCall) -> None:
            enabled = call.data[ATTR_ENABLED]
            for coord in _get_coordinators():
                await coord.async_set_ai_detection(enabled)

        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_AI_DETECTION,
            async_handle_ai,
            schema=SERVICE_SET_BOOL_SCHEMA,
        )

    # 20. Hardware Button Lock / Child Lock
    if not hass.services.has_service(DOMAIN, SERVICE_SET_BUTTON_LOCK):
        async def async_handle_button_lock(call: ServiceCall) -> None:
            enabled = call.data[ATTR_ENABLED]
            for coord in _get_coordinators():
                await coord.async_set_button_lock(enabled)

        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_BUTTON_LOCK,
            async_handle_button_lock,
            schema=SERVICE_SET_BOOL_SCHEMA,
        )

    # 21. Toggle Reclean (Resume after charge)
    if not hass.services.has_service(DOMAIN, SERVICE_SET_TOGGLE_RECLEAN):
        async def async_handle_toggle_reclean(call: ServiceCall) -> None:
            enabled = call.data[ATTR_ENABLED]
            for coord in _get_coordinators():
                await coord.async_set_toggle_reclean(enabled)

        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_TOGGLE_RECLEAN,
            async_handle_toggle_reclean,
            schema=SERVICE_SET_BOOL_SCHEMA,
        )

    # 22. Wake Up
    if not hass.services.has_service(DOMAIN, SERVICE_WAKE_UP):
        async def async_handle_wake_up(_: ServiceCall) -> None:
            for coord in _get_coordinators():
                await coord.async_wake_up()

        hass.services.async_register(
            DOMAIN,
            SERVICE_WAKE_UP,
            async_handle_wake_up,
        )

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: LGRobokingCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_close()
    return unload_ok
