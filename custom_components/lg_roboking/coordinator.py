"""DataUpdateCoordinator for LG Roboking AI All-in-One."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import json
import logging
import os
import time
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
    CONF_MAP_REFRESH_INTERVAL,
    CONF_REFRESH_TOKEN,
    CONF_SCAN_INTERVAL,
    CONF_SYNC_LEGACY_JSON,
    DEFAULT_API_KEY,
    DEFAULT_APP_VERSION,
    DEFAULT_CLIENT_ID,
    DEFAULT_MAP_REFRESH_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LEGACY_CONFIG_PATHS,
)
from .map_renderer import render_roboking_map

_LOGGER = logging.getLogger(__name__)


class LGRobokingCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage polling, map streaming, and token rotation for LG Roboking."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        scan_minutes = entry.options.get(
            CONF_SCAN_INTERVAL,
            entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )

        self.map_refresh_seconds = int(
            entry.options.get(
                CONF_MAP_REFRESH_INTERVAL,
                entry.data.get(CONF_MAP_REFRESH_INTERVAL, DEFAULT_MAP_REFRESH_INTERVAL),
            )
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

        self.last_rendered_map_png: bytes | None = None
        self.last_map_update_timestamp: float = 0.0
        self._map_loop_task: asyncio.Task | None = None
        self._is_closed = False

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.data[CONF_DEVICE_ID]}",
            update_interval=timedelta(minutes=int(scan_minutes)),
        )

    @callback
    def _handle_token_rotation(self, new_refresh_token: str) -> None:
        """Persist rotated refresh token into ConfigEntry and legacy JSON."""
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
            status = await self.api.async_get_device_status(force_token_refresh=True)
            snapshot = status.get("snapshot", {})

            if "RT_MAP" in snapshot:
                try:
                    self.last_rendered_map_png = await self.hass.async_add_executor_job(
                        render_roboking_map, snapshot
                    )
                    self.last_map_update_timestamp = time.time()
                except Exception as err:
                    _LOGGER.warning("Error rendering Roboking map image: %s", err)

            self._check_map_heartbeat_loop(status)
            return status
        except (LGRobokingAuthError, LGRobokingApiError) as err:
            raise UpdateFailed(str(err)) from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error communicating with LG ThinQ: {err}") from err

    def is_robot_active(self, status: dict[str, Any] | None = None) -> bool:
        """Return True if robot is actively cleaning or moving."""
        data = status or self.data or {}
        snapshot = data.get("snapshot", {})
        robot_state = str(snapshot.get("ROBOT_STATE", "")).upper().strip()
        inactive_states = ("STANDBY", "CHARGING", "SLEEP", "POWER_OFF", "")
        return robot_state not in inactive_states

    def _check_map_heartbeat_loop(self, status: dict[str, Any]) -> None:
        """Start or stop the real-time map heartbeat loop based on robot state."""
        if self._is_closed:
            return

        if self.is_robot_active(status):
            if self._map_loop_task is None or self._map_loop_task.done():
                _LOGGER.info(
                    "Starting LG Roboking real-time map heartbeat loop (interval: %ds)",
                    self.map_refresh_seconds,
                )
                self._map_loop_task = self.hass.async_create_background_task(
                    self._run_map_heartbeat_loop(),
                    name=f"lg_roboking_map_loop_{self.entry.entry_id}",
                )
        else:
            if self._map_loop_task and not self._map_loop_task.done():
                _LOGGER.info("Stopping LG Roboking real-time map heartbeat loop (robot is inactive)")
                self._map_loop_task.cancel()
                self._map_loop_task = None

    async def _run_map_heartbeat_loop(self) -> None:
        """Send UPDATE_DATA + RTMAP heartbeat and fetch updated coordinates while robot is active."""
        try:
            # First activate streaming session on LG cloud
            try:
                await self.api.async_start_map_stream(0, 0)
            except Exception as err:
                _LOGGER.debug("Initial async_start_map_stream error: %s", err)

            while not self._is_closed:
                try:
                    await self.api.async_send_map_heartbeat()
                    status = await self.api.async_get_device_status(force_token_refresh=False)
                    snapshot = status.get("snapshot", {})
                    if "RT_MAP" in snapshot:
                        self.last_rendered_map_png = await self.hass.async_add_executor_job(
                            render_roboking_map, snapshot
                        )
                        self.last_map_update_timestamp = time.time()
                    self.async_set_updated_data(status)

                    if not self.is_robot_active(status):
                        _LOGGER.info("Robot finished cleaning, ending map heartbeat loop.")
                        break

                except asyncio.CancelledError:
                    break
                except Exception as err:
                    _LOGGER.debug("Map heartbeat loop cycle exception: %s", err)

                await asyncio.sleep(self.map_refresh_seconds)
        except asyncio.CancelledError:
            pass
        finally:
            self._map_loop_task = None

    async def async_refresh_live_map(self) -> bytes:
        """On-demand live map refresh triggered by Camera requests."""
        try:
            # Ensure session active
            if self.is_robot_active():
                await self.api.async_send_map_heartbeat()
            status = await self.api.async_get_device_status(force_token_refresh=False)
            snapshot = status.get("snapshot", {})
            if "RT_MAP" in snapshot:
                self.last_rendered_map_png = await self.hass.async_add_executor_job(
                    render_roboking_map, snapshot
                )
                self.last_map_update_timestamp = time.time()
            self.async_set_updated_data(status)
            self._check_map_heartbeat_loop(status)
        except Exception as err:
            _LOGGER.debug("On-demand map refresh error: %s", err)

        return self.last_rendered_map_png or b""

    async def async_get_or_render_map(self) -> bytes:
        """Return latest map PNG bytes, refreshing on-demand if cache is stale."""
        now = time.time()
        # If cache is older than map_refresh_seconds and robot is active, refresh immediately
        if (now - self.last_map_update_timestamp) >= self.map_refresh_seconds:
            await self.async_refresh_live_map()

        if self.last_rendered_map_png:
            return self.last_rendered_map_png

        snapshot = (self.data or {}).get("snapshot", {})
        self.last_rendered_map_png = await self.hass.async_add_executor_job(
            render_roboking_map, snapshot
        )
        self.last_map_update_timestamp = time.time()
        return self.last_rendered_map_png

    async def async_set_clean_type(self, clean_type: str) -> None:
        """Send clean mode command to LG ThinQ cloud and optimistically update state."""
        await self.api.async_set_clean_type(clean_type)
        current = dict(self.data or {})
        current["clean_type"] = clean_type.upper()
        if "snapshot" in current and isinstance(current["snapshot"], dict):
            current["snapshot"] = {**current["snapshot"], "CLEAN_TYPE": clean_type.upper()}
        self.async_set_updated_data(current)

    async def async_set_suction_level(self, suction_level: str) -> None:
        """Send suction level command to LG ThinQ cloud and optimistically update state."""
        await self.api.async_set_suction_level(suction_level)
        current = dict(self.data or {})
        current["suction_level"] = suction_level.upper()
        if "snapshot" in current and isinstance(current["snapshot"], dict):
            current["snapshot"] = {**current["snapshot"], "SUCTION_LEVEL": suction_level.upper()}
        self.async_set_updated_data(current)

    async def async_set_smart_turbo(self, enable: bool) -> None:
        """Send smart turbo command to LG ThinQ cloud and optimistically update state."""
        await self.api.async_set_smart_turbo(enable)
        current = dict(self.data or {})
        current["smart_turbo"] = enable
        if "snapshot" in current and isinstance(current["snapshot"], dict):
            current["snapshot"] = {**current["snapshot"], "SMART_TURBO": "true" if enable else "false"}
        self.async_set_updated_data(current)

    async def async_set_zz_dist(self, zz_dist: str) -> None:
        """Send clean spacing command to LG ThinQ cloud and optimistically update state."""
        await self.api.async_set_zz_dist(zz_dist)
        current = dict(self.data or {})
        current["zz_dist"] = zz_dist.upper()
        if "snapshot" in current and isinstance(current["snapshot"], dict):
            current["snapshot"] = {**current["snapshot"], "ZZ_DIST": zz_dist.upper()}
        self.async_set_updated_data(current)

    async def async_set_water_supply_level(self, water_level: str) -> None:
        """Send water supply level command to LG ThinQ cloud and optimistically update state."""
        await self.api.async_set_water_supply_level(water_level)
        current = dict(self.data or {})
        current["water_supply_level"] = water_level.upper()
        if "snapshot" in current and isinstance(current["snapshot"], dict):
            current["snapshot"] = {**current["snapshot"], "WATERSUPPLY_LEVEL": water_level.upper()}
        self.async_set_updated_data(current)

    async def async_wake_up(self) -> None:
        """Send WakeUp command to LG ThinQ cloud to wake the robot vacuum."""
        await self.api.async_wake_up()

    async def async_close(self) -> None:
        """Clean up background tasks and close API session."""
        self._is_closed = True
        if self._map_loop_task and not self._map_loop_task.done():
            self._map_loop_task.cancel()
            self._map_loop_task = None
        await self.api.async_close()
