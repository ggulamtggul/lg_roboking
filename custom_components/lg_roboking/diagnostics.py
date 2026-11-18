"""Diagnostics for LG Roboking: the raw ThinQ snapshot behind the entities and map."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_API_KEY, CONF_CLIENT_ID, CONF_DEVICE_ID, CONF_REFRESH_TOKEN, DOMAIN

TO_REDACT = {CONF_REFRESH_TOKEN, CONF_CLIENT_ID, CONF_API_KEY, CONF_DEVICE_ID, "deviceId", "SN", "MAC"}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    """Return the entry config (secrets redacted) and the latest device status."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "options": dict(entry.options),
        "status": async_redact_data(coordinator.data or {}, TO_REDACT),
    }
