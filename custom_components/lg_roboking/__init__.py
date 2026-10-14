"""The LG Roboking AI All-in-One custom integration."""
from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
import homeassistant.helpers.config_validation as cv

from .const import (
    ATTR_MODE,
    CLEAN_TYPE_TO_LABEL,
    DOMAIN,
    LABEL_TO_CLEAN_TYPE,
    PLATFORMS,
    SERVICE_SET_CLEAN_MODE,
)
from .coordinator import LGRobokingCoordinator
from . import select, button

_LOGGER = logging.getLogger(__name__)

SERVICE_SET_MODE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MODE): cv.string,
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up LG Roboking AI All-in-One from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    coordinator = LGRobokingCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    if not hass.services.has_service(DOMAIN, SERVICE_SET_CLEAN_MODE):
        async def async_handle_set_clean_mode(call: ServiceCall) -> None:
            raw_input = call.data[ATTR_MODE].strip()
            api_code = LABEL_TO_CLEAN_TYPE.get(raw_input, raw_input.upper())
            if api_code not in CLEAN_TYPE_TO_LABEL:
                raise ValueError(
                    f"유효하지 않은 모드입니다: {raw_input} (ALL, SUCTION, MOP 중 하나여야 합니다)"
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
        await coordinator.api.async_close()
    return unload_ok
