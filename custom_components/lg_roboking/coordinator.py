"""DataUpdateCoordinator for LG Roboking AI All-in-One."""
from __future__ import annotations

from datetime import timedelta
import json
import logging
import os
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import LGRobokingAPI, LGRobokingApiError, LGRobokingAuthError
from .const import (
    CONF_API_KEY,
    CONF_APP_VERSION,
    CONF_CLIENT_ID,
    CONF_DEVICE_ID,
    CONF_REFRESH_TOKEN,
    CONF_SCAN_INTERVAL,
    CONF_SYNC_LEGACY_JSON,
    DEFAULT_API_KEY,
    DEFAULT_APP_VERSION,
    DEFAULT_CLIENT_ID,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LEGACY_CONFIG_PATHS,
)

_LOGGER = logging.getLogger(__name__)


class LGRobokingCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage polling and token rotation for LG Roboking."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        scan_minutes = entry.options.get(
            CONF_SCAN_INTERVAL,
            entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )

        self.api = LGRobokingAPI(
            hass=hass,
            refresh_token=entry.data[CONF_REFRESH_TOKEN],
            device_id=entry.data[CONF_DEVICE_ID],
            client_id=entry.data.get(CONF_CLIENT_ID, DEFAULT_CLIENT_ID),
            api_key=entry.data.get(CONF_API_KEY, DEFAULT_API_KEY),
            app_version=entry.data.get(CONF_APP_VERSION, DEFAULT_APP_VERSION),
            token_update_callback=self._handle_token_rotation,
        )

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.data[CONF_DEVICE_ID]}",
            update_interval=timedelta(minutes=int(scan_minutes)),
        )

    @callback
    def _handle_token_rotation(self, new_refresh_token: str) -> None:
        """Persist rotated refresh token into ConfigEntry (and legacy JSON if enabled)."""
        if self.entry.data.get(CONF_REFRESH_TOKEN) == new_refresh_token:
            return

        new_data = {**self.entry.data, CONF_REFRESH_TOKEN: new_refresh_token}
        self.hass.config_entries.async_update_entry(self.entry, data=new_data)
        _LOGGER.info("LG Roboking Refresh Token rotated and saved to Home Assistant storage.")

        sync_legacy = self.entry.options.get(
            CONF_SYNC_LEGACY_JSON,
            self.entry.data.get(CONF_SYNC_LEGACY_JSON, True),
        )
        if sync_legacy:
            self.hass.async_add_executor_job(self._sync_legacy_json_file, new_refresh_token)

    def _sync_legacy_json_file(self, new_refresh_token: str) -> None:
        """Keep /config/www/lg_roboking_config.json updated if present on disk."""
        for path in LEGACY_CONFIG_PATHS:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                    cfg["refresh_token"] = new_refresh_token
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(cfg, f, indent=2)
                except Exception as err:
                    _LOGGER.debug("Failed to update legacy config %s: %s", path, err)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch latest status from LG ThinQ cloud."""
        try:
            # Force token refresh on periodic poll so refresh_token stays actively rotated
            return await self.api.async_get_device_status(force_token_refresh=True)
        except (LGRobokingAuthError, LGRobokingApiError) as err:
            raise UpdateFailed(str(err)) from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error communicating with LG ThinQ: {err}") from err

    async def async_set_clean_type(self, clean_type: str) -> None:
        """Send clean mode command to LG ThinQ cloud and optimistically update state."""
        await self.api.async_set_clean_type(clean_type)
        current = dict(self.data or {})
        current["clean_type"] = clean_type.upper()
        if "snapshot" in current and isinstance(current["snapshot"], dict):
            current["snapshot"] = {**current["snapshot"], "CLEAN_TYPE": clean_type.upper()}
        self.async_set_updated_data(current)
