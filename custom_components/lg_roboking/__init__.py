"""The LG Roboking AI All-in-One custom integration."""
from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
import homeassistant.helpers.config_validation as cv

from .const import (
    ATTR_ENABLED,
    ATTR_LEVEL,
    ATTR_MODE,
    CLEAN_TYPE_TO_LABEL,
    DOMAIN,
    LABEL_TO_CLEAN_TYPE,
    LABEL_TO_SUCTION_LEVEL,
    LABEL_TO_WATER_SUPPLY,
    LABEL_TO_ZZ_DIST,
    PLATFORMS,
    SERVICE_SET_CLEAN_MODE,
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

SERVICE_SET_MODE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MODE): cv.string,
    }
)

SERVICE_SET_LEVEL_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_LEVEL): cv.string,
    }
)

SERVICE_SET_TURBO_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENABLED): cv.boolean,
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up LG Roboking AI All-in-One from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    coordinator = LGRobokingCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    if not hass.services.has_service(DOMAIN, SERVICE_SET_CLEAN_MODE):
        async def async_handle_set_clean_mode(call: ServiceCall) -> None:
            raw_input = call.data[ATTR_MODE].strip()
            api_code = LABEL_TO_CLEAN_TYPE.get(raw_input, raw_input.upper())
            if api_code not in CLEAN_TYPE_TO_LABEL:
                raise ValueError(
                    f"유효하지 않은 청소 방식입니다: {raw_input} (ALL, SUCTION, MOP 중 하나여야 합니다)"
                )
            for coord in hass.data.get(DOMAIN, {}).values():
                if isinstance(coord, LGRobokingCoordinator):
                    await coord.async_set_clean_type(api_code)

        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_CLEAN_MODE,
            async_handle_set_clean_mode,
            schema=SERVICE_SET_MODE_SCHEMA,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_SET_SUCTION_LEVEL):
        async def async_handle_set_suction(call: ServiceCall) -> None:
            raw_input = call.data[ATTR_LEVEL].strip()
            api_code = LABEL_TO_SUCTION_LEVEL.get(raw_input, raw_input.upper())
            if api_code not in SUCTION_LEVEL_TO_LABEL:
                raise ValueError(
                    f"유효하지 않은 흡입 세기입니다: {raw_input} ({', '.join(SUCTION_LEVEL_TO_LABEL.keys())} 중 하나여야 합니다)"
                )
            for coord in hass.data.get(DOMAIN, {}).values():
                if isinstance(coord, LGRobokingCoordinator):
                    await coord.async_set_suction_level(api_code)

        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_SUCTION_LEVEL,
            async_handle_set_suction,
            schema=SERVICE_SET_LEVEL_SCHEMA,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_SET_ZZ_DIST):
        async def async_handle_set_zz_dist(call: ServiceCall) -> None:
            raw_input = call.data[ATTR_LEVEL].strip()
            api_code = LABEL_TO_ZZ_DIST.get(raw_input, raw_input.upper())
            if api_code not in ZZ_DIST_TO_LABEL:
                raise ValueError(
                    f"유효하지 않은 청소 간격입니다: {raw_input} ({', '.join(ZZ_DIST_TO_LABEL.keys())} 중 하나여야 합니다)"
                )
            for coord in hass.data.get(DOMAIN, {}).values():
                if isinstance(coord, LGRobokingCoordinator):
                    await coord.async_set_zz_dist(api_code)

        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_ZZ_DIST,
            async_handle_set_zz_dist,
            schema=SERVICE_SET_LEVEL_SCHEMA,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_SET_WATER_LEVEL):
        async def async_handle_set_water_level(call: ServiceCall) -> None:
            raw_input = call.data[ATTR_LEVEL].strip()
            api_code = LABEL_TO_WATER_SUPPLY.get(raw_input, raw_input.upper())
            if api_code not in WATER_SUPPLY_TO_LABEL:
                raise ValueError(
                    f"유효하지 않은 물 공급량입니다: {raw_input} ({', '.join(WATER_SUPPLY_TO_LABEL.keys())} 중 하나여야 합니다)"
                )
            for coord in hass.data.get(DOMAIN, {}).values():
                if isinstance(coord, LGRobokingCoordinator):
                    await coord.async_set_water_supply_level(api_code)

        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_WATER_LEVEL,
            async_handle_set_water_level,
            schema=SERVICE_SET_LEVEL_SCHEMA,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_SET_SMART_TURBO):
        async def async_handle_set_turbo(call: ServiceCall) -> None:
            enabled = call.data[ATTR_ENABLED]
            for coord in hass.data.get(DOMAIN, {}).values():
                if isinstance(coord, LGRobokingCoordinator):
                    await coord.async_set_smart_turbo(enabled)

        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_SMART_TURBO,
            async_handle_set_turbo,
            schema=SERVICE_SET_TURBO_SCHEMA,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_WAKE_UP):
        async def async_handle_wake_up(call: ServiceCall) -> None:
            for coord in hass.data.get(DOMAIN, {}).values():
                if isinstance(coord, LGRobokingCoordinator):
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
