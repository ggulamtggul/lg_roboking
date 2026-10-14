"""Config flow for LG Roboking AI All-in-One integration."""
from __future__ import annotations

import json
import logging
import os
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

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


def _load_legacy_config() -> dict[str, Any]:
    """Read existing lg_roboking_config.json if available to pre-fill the UI form."""
    for path in LEGACY_CONFIG_PATHS:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict) and data.get("refresh_token"):
                    return data
            except Exception as err:
                _LOGGER.debug("Could not read legacy config at %s: %s", path, err)
    return {}


class LGRobokingConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for LG Roboking AI All-in-One."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        legacy = await self.hass.async_add_executor_job(_load_legacy_config)

        if user_input is not None:
            refresh_token = user_input[CONF_REFRESH_TOKEN].strip()
            device_id = (user_input.get(CONF_DEVICE_ID) or "").strip()
            scan_interval = int(user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))

            api = LGRobokingAPI(
                hass=self.hass,
                refresh_token=refresh_token,
                device_id=device_id,
                client_id=legacy.get("client_id", DEFAULT_CLIENT_ID),
                api_key=legacy.get("api_key", DEFAULT_API_KEY),
                app_version=legacy.get("app_version", DEFAULT_APP_VERSION),
            )

            try:
                if not device_id:
                    discovered = await api.async_discover_roboking_devices()
                    if discovered:
                        device_id = discovered[0]["device_id"]
                        api.device_id = device_id
                    else:
                        errors["base"] = "no_device_found"

                if not errors:
                    status = await api.async_get_device_status(force_token_refresh=True)
                    # Use potentially rotated refresh_token
                    latest_token = api.refresh_token
                    await self.async_set_unique_id(device_id)
                    self._abort_if_unique_id_configured()

                    title = status.get("alias") or f"LG 로보킹 ({device_id[:8]})"
                    return self.async_create_entry(
                        title=title,
                        data={
                            CONF_DEVICE_ID: device_id,
                            CONF_REFRESH_TOKEN: latest_token,
                            CONF_CLIENT_ID: legacy.get("client_id", DEFAULT_CLIENT_ID),
                            CONF_API_KEY: legacy.get("api_key", DEFAULT_API_KEY),
                            CONF_APP_VERSION: legacy.get("app_version", DEFAULT_APP_VERSION),
                            CONF_SCAN_INTERVAL: scan_interval,
                            CONF_SYNC_LEGACY_JSON: True,
                        },
                    )
            except LGRobokingAuthError as err:
                _LOGGER.error("Authentication failed during setup: %s", err)
                errors["base"] = "invalid_auth"
            except LGRobokingApiError as err:
                _LOGGER.error("API error during setup: %s", err)
                errors["base"] = "cannot_connect"
            except Exception as err:
                _LOGGER.exception("Unexpected error during setup: %s", err)
                errors["base"] = "unknown"
            finally:
                await api.async_close()

        default_token = (
            user_input.get(CONF_REFRESH_TOKEN)
            if user_input
            else legacy.get("refresh_token", "")
        )
        default_device_id = (
            user_input.get(CONF_DEVICE_ID)
            if user_input
            else legacy.get("device_id", "")
        )

        schema = vol.Schema(
            {
                vol.Required(CONF_REFRESH_TOKEN, default=default_token): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                        multiline=True,
                    )
                ),
                vol.Optional(CONF_DEVICE_ID, default=default_device_id): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=60,
                        step=1,
                        unit_of_measurement="분",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "legacy_detected": "감지됨 (자동 입력 완료)" if legacy.get("refresh_token") else "없음 (직접 입력)"
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> LGRobokingOptionsFlowHandler:
        """Get the options flow for this handler."""
        return LGRobokingOptionsFlowHandler(config_entry)


class LGRobokingOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow (updating Refresh Token or polling interval)."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            new_token = user_input[CONF_REFRESH_TOKEN].strip()
            scan_interval = int(user_input[CONF_SCAN_INTERVAL])
            sync_legacy = bool(user_input.get(CONF_SYNC_LEGACY_JSON, True))

            if new_token != self._config_entry.data.get(CONF_REFRESH_TOKEN):
                # Validate new token before saving
                api = LGRobokingAPI(
                    hass=self.hass,
                    refresh_token=new_token,
                    device_id=self._config_entry.data[CONF_DEVICE_ID],
                )
                try:
                    await api.async_get_access_token(force_refresh=True)
                    new_token = api.refresh_token
                except Exception:
                    errors["base"] = "invalid_auth"
                finally:
                    await api.async_close()

            if not errors:
                self.hass.config_entries.async_update_entry(
                    self._config_entry,
                    data={
                        **self._config_entry.data,
                        CONF_REFRESH_TOKEN: new_token,
                        CONF_SCAN_INTERVAL: scan_interval,
                        CONF_SYNC_LEGACY_JSON: sync_legacy,
                    },
                )
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_SCAN_INTERVAL: scan_interval,
                        CONF_SYNC_LEGACY_JSON: sync_legacy,
                    },
                )

        current_token = self._config_entry.data.get(CONF_REFRESH_TOKEN, "")
        current_interval = self._config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self._config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        current_sync = self._config_entry.options.get(
            CONF_SYNC_LEGACY_JSON,
            self._config_entry.data.get(CONF_SYNC_LEGACY_JSON, True),
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_REFRESH_TOKEN, default=current_token): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.TEXT,
                            multiline=True,
                        )
                    ),
                    vol.Required(CONF_SCAN_INTERVAL, default=current_interval): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1,
                            max=60,
                            step=1,
                            unit_of_measurement="분",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Optional(CONF_SYNC_LEGACY_JSON, default=current_sync): bool,
                }
            ),
            errors=errors,
        )
