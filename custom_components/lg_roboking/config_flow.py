"""Config flow for LG Roboking AI All-in-One integration."""
from __future__ import annotations

import json
import logging
import os
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import AbortFlow, FlowResult
from homeassistant.helpers import selector

import aiohttp

from .api import LGRobokingAPI, LGRobokingApiError, LGRobokingAuthError
from .qr_login import QrLoginError, ThinQQrLogin
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

_LOGGER = logging.getLogger(__name__)


def _qr_data_uri(text: str) -> str:
    """QR code as an SVG data URI for the config flow description (same approach as HA's Tuya)."""
    import segno  # noqa: PLC0415 - installed from manifest requirements

    return segno.make(text, error="m").svg_data_uri(scale=6, border=2, dark="#000000", light="#ffffff")


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

    def __init__(self) -> None:
        """Initialize the flow."""
        self._qr: ThinQQrLogin | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Choose how to sign in: QR in the ThinQ app (recommended) or a pasted token."""
        return self.async_show_menu(step_id="user", menu_options=["qr", "token"])

    async def async_step_qr(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show a QR code + PIN; the user approves it in the LG ThinQ app, then submits."""
        errors: dict[str, str] = {}
        try:
            if self._qr is None:
                self._qr = ThinQQrLogin()
            if user_input is not None:
                if await self._qr.wait(3):
                    token = await self._qr.finish()
                    await self._async_drop_qr()
                    result, errors = await self._async_create_from_token(
                        token, "", DEFAULT_SCAN_INTERVAL, DEFAULT_MAP_REFRESH_INTERVAL, {}
                    )
                    if result is not None:
                        return result
                    self._qr = ThinQQrLogin()
                else:
                    errors["base"] = "qr_expired" if self._qr.expired else "qr_not_approved"
            if not self._qr.qr_text or self._qr.expired:
                await self._qr.start()
        except (QrLoginError, aiohttp.ClientError, TimeoutError) as err:
            _LOGGER.warning("LG ThinQ QR login failed: %s", err)
            await self._async_drop_qr()
            return self.async_abort(reason="qr_failed", description_placeholders={"error": str(err)})

        qr_image = await self.hass.async_add_executor_job(_qr_data_uri, self._qr.qr_text)
        return self.async_show_form(
            step_id="qr",
            data_schema=vol.Schema({}),
            errors=errors,
            description_placeholders={"qr": qr_image, "pin": self._qr.pin},
        )

    async def _async_drop_qr(self) -> None:
        if self._qr is not None:
            await self._qr.close()
            self._qr = None

    @callback
    def async_remove(self) -> None:
        """Close the QR login session when the flow is abandoned."""
        if self._qr is not None:
            self.hass.async_create_task(self._async_drop_qr())

    async def async_step_token(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Paste a refresh token copied from my.lgthinq.com (fallback)."""
        errors: dict[str, str] = {}
        legacy = await self.hass.async_add_executor_job(_load_legacy_config)

        if user_input is not None:
            result, errors = await self._async_create_from_token(
                user_input[CONF_REFRESH_TOKEN].strip(),
                (user_input.get(CONF_DEVICE_ID) or "").strip(),
                int(user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)),
                int(user_input.get(CONF_MAP_REFRESH_INTERVAL, DEFAULT_MAP_REFRESH_INTERVAL)),
                legacy,
            )
            if result is not None:
                return result

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
        return self._token_form(default_token, default_device_id, legacy, errors)

    async def _async_create_from_token(
        self,
        refresh_token: str,
        device_id: str,
        scan_interval: int,
        map_refresh: int,
        legacy: dict[str, Any],
    ) -> tuple[FlowResult | None, dict[str, str]]:
        """Validate the token, find the vacuum and create the entry. Returns (result, errors)."""
        errors: dict[str, str] = {}
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
                        CONF_MAP_REFRESH_INTERVAL: map_refresh,
                        CONF_SYNC_LEGACY_JSON: True,
                    },
                ), errors
        except AbortFlow:
            raise
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
        return None, errors

    def _token_form(
        self, default_token: str, default_device_id: str, legacy: dict[str, Any], errors: dict[str, str]
    ) -> FlowResult:
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
                vol.Optional(
                    CONF_MAP_REFRESH_INTERVAL, default=DEFAULT_MAP_REFRESH_INTERVAL
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=3,
                        max=60,
                        step=1,
                        unit_of_measurement="초",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="token",
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
    """Handle options flow (updating Refresh Token, intervals, etc.)."""

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
            map_refresh = int(user_input[CONF_MAP_REFRESH_INTERVAL])
            sync_legacy = bool(user_input.get(CONF_SYNC_LEGACY_JSON, True))

            if new_token != self._config_entry.data.get(CONF_REFRESH_TOKEN):
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
                        CONF_MAP_REFRESH_INTERVAL: map_refresh,
                        CONF_SYNC_LEGACY_JSON: sync_legacy,
                    },
                )
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_SCAN_INTERVAL: scan_interval,
                        CONF_MAP_REFRESH_INTERVAL: map_refresh,
                        CONF_SYNC_LEGACY_JSON: sync_legacy,
                    },
                )

        current_token = self._config_entry.data.get(CONF_REFRESH_TOKEN, "")
        current_interval = self._config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self._config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        current_map_refresh = self._config_entry.options.get(
            CONF_MAP_REFRESH_INTERVAL,
            self._config_entry.data.get(CONF_MAP_REFRESH_INTERVAL, DEFAULT_MAP_REFRESH_INTERVAL),
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
                    vol.Required(CONF_MAP_REFRESH_INTERVAL, default=current_map_refresh): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=3,
                            max=60,
                            step=1,
                            unit_of_measurement="초",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Optional(CONF_SYNC_LEGACY_JSON, default=current_sync): bool,
                }
            ),
            errors=errors,
        )
