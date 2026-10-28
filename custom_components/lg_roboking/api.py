"""Asynchronous LG ThinQ Web API Client for LG Roboking AI All-in-One."""
from __future__ import annotations

import base64
import json
import logging
import os
import random
import string
import time
import uuid
from typing import Any, Callable

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import (
    AUTH_REFRESH_URL,
    DASHBOARD_URL,
    DEFAULT_API_KEY,
    DEFAULT_APP_VERSION,
    DEFAULT_CLIENT_ID,
    DEVICE_BASE_URL,
)

_LOGGER = logging.getLogger(__name__)


def _extract_claims_from_jwt(token: str) -> dict[str, Any]:
    """Decode JWT payload without signature verification."""
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return {}
        payload_part = parts[1]
        payload_part += "=" * (-len(payload_part) % 4)
        decoded = base64.urlsafe_b64decode(payload_part.encode("utf-8")).decode("utf-8")
        return json.loads(decoded)
    except Exception as err:
        _LOGGER.debug("Failed to decode JWT payload: %s", err)
        return {}


def _make_random_message_id(length: int = 22) -> str:
    """Generate a 22-character alphanumeric message ID."""
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(length))


class LGRobokingAuthError(HomeAssistantError):
    """Error indicating authentication or token refresh failure."""


class LGRobokingApiError(HomeAssistantError):
    """Error indicating an API call failure."""


class LGRobokingAPI:
    """Async client for LG ThinQ Web API (Roboking B95)."""

    def __init__(
        self,
        hass: HomeAssistant,
        refresh_token: str,
        device_id: str | None = None,
        client_id: str = DEFAULT_CLIENT_ID,
        api_key: str = DEFAULT_API_KEY,
        app_version: str = DEFAULT_APP_VERSION,
        token_update_callback: Callable[[str], None] | None = None,
    ) -> None:
        """Initialize the API client."""
        self.hass = hass
        self.refresh_token = refresh_token.strip()
        self.device_id = (device_id or "").strip()
        self.client_id = client_id
        self.api_key = api_key
        self.app_version = app_version
        self._token_update_callback = token_update_callback

        self._access_token: str | None = None
        self._user_no: str | None = None
        self._token_expires_at: float = 0.0
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Return an isolated aiohttp ClientSession with a dedicated CookieJar."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar())
        return self._session

    async def async_close(self) -> None:
        """Close the underlying aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def async_get_access_token(self, force_refresh: bool = False) -> tuple[str, str]:
        """Return a valid (access_token, user_no) tuple, refreshing via OIDC if needed."""
        now = time.time()
        if (
            not force_refresh
            and self._access_token
            and self._user_no
            and now < (self._token_expires_at - 120)
        ):
            return self._access_token, self._user_no

        session = await self._get_session()
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Origin": "https://my.lgthinq.com",
            "Referer": "https://my.lgthinq.com/",
            "Accept": "application/json",
            "x-thinq-app-type": "WEB",
            "x-client-id": self.client_id,
            "x-api-key": self.api_key,
            "x-service-code": "SVC202",
            "x-country-code": "KR",
            "x-language-code": "ko-KR",
            "x-service-phase": "OP",
            "x-thinq-app-ver": self.app_version,
            "x-thinq-app-os": "browser",
            "x-message-id": str(uuid.uuid4()),
        }
        cookies = {"refresh_token": self.refresh_token}

        try:
            async with session.post(
                AUTH_REFRESH_URL,
                headers=headers,
                cookies=cookies,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                text = await resp.text()
                if resp.status != 200:
                    raise LGRobokingAuthError(
                        f"LG ThinQ 토큰 갱신 실패 (HTTP {resp.status}): {text[:200]}"
                    )
                data = json.loads(text)
                if data.get("resultCode") != "0000":
                    raise LGRobokingAuthError(
                        f"LG ThinQ 토큰 갱신 거부 (코드 {data.get('resultCode')}): {data}"
                    )

                new_rf: str | None = None
                if "refresh_token" in resp.cookies:
                    new_rf = resp.cookies["refresh_token"].value
                else:
                    for cookie in session.cookie_jar:
                        if cookie.key == "refresh_token" and cookie.value:
                            new_rf = cookie.value
                            break

                if new_rf and new_rf != self.refresh_token:
                    _LOGGER.debug("LG ThinQ Refresh Token rotated successfully")
                    self.refresh_token = new_rf
                    if self._token_update_callback:
                        self._token_update_callback(new_rf)

                access_token = data["result"]["accessToken"]
                claims = _extract_claims_from_jwt(access_token)
                user_no = claims.get("user_no")
                exp = claims.get("exp")

                if not user_no:
                    raise LGRobokingAuthError("Access Token JWT에서 user_no를 추출할 수 없습니다.")

                self._access_token = access_token
                self._user_no = str(user_no)
                jwt_exp = float(exp) if exp else (now + 3600)
                self._token_expires_at = min(jwt_exp, now + 1500)
                return self._access_token, self._user_no

        except LGRobokingAuthError:
            raise
        except Exception as err:
            raise LGRobokingApiError(f"LG ThinQ 인증 서버 통신 오류: {err}") from err

    def _build_service_headers(self, token: str, user_no: str) -> dict[str, str]:
        """Build standard ThinQ v2 service headers."""
        return {
            "accept": "application/json",
            "accept-language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "authorization": f"Bearer {token}",
            "origin": "https://my.lgthinq.com",
            "referer": "https://my.lgthinq.com/",
            "x-api-key": self.api_key,
            "x-app-version": "LG ThinQ/5.2.12w710",
            "x-client-id": self.client_id,
            "x-country-code": "KR",
            "x-language-code": "ko-KR",
            "x-message-id": _make_random_message_id(),
            "x-origin": "app-web-browser",
            "x-service-code": "SVC202",
            "x-service-phase": "OP",
            "x-thinq-app-level": "PRD",
            "x-thinq-app-logintype": "LGE",
            "x-thinq-app-os": "browser",
            "x-thinq-app-type": "WEB",
            "x-thinq-app-ver": self.app_version,
            "x-user-no": user_no,
        }

    async def async_discover_roboking_devices(self) -> list[dict[str, Any]]:
        """Discover robot vacuum devices registered to the user's ThinQ account."""
        token, user_no = await self.async_get_access_token(force_refresh=True)
        session = await self._get_session()
        headers = self._build_service_headers(token, user_no)

        async with session.get(
            DASHBOARD_URL,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status != 200:
                return []
            data = await resp.json(content_type=None)
            items = data.get("result", {}).get("item", []) or []
            roboking_list = []
            for item in items:
                dev_type = item.get("deviceType")
                model_name = str(item.get("modelName", ""))
                alias = str(item.get("alias", "로보킹"))
                dev_id = item.get("deviceId")
                if dev_id and (dev_type in (201, "201", 501, "501") or "B-95" in model_name or "로보킹" in alias or "청소기" in alias):
                    roboking_list.append({
                        "device_id": dev_id,
                        "alias": alias,
                        "model_name": model_name,
                        "snapshot": item.get("snapshot", {}),
                    })
            if not roboking_list and items:
                for item in items:
                    if item.get("deviceId"):
                        roboking_list.append({
                            "device_id": item["deviceId"],
                            "alias": item.get("alias", item["deviceId"]),
                            "model_name": item.get("modelName", ""),
                            "snapshot": item.get("snapshot", {}),
                        })
            return roboking_list

    async def async_get_device_status(self, force_token_refresh: bool = False) -> dict[str, Any]:
        """Fetch the full device status and snapshot from LG ThinQ cloud."""
        if not self.device_id:
            raise LGRobokingApiError("Device ID가 설정되지 않았습니다.")

        token, user_no = await self.async_get_access_token(force_refresh=force_token_refresh)
        session = await self._get_session()
        url = f"{DEVICE_BASE_URL}/{self.device_id}"
        headers = self._build_service_headers(token, user_no)

        async with session.get(
            url,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status == 401 and not force_token_refresh:
                return await self.async_get_device_status(force_token_refresh=True)
            text = await resp.text()
            if resp.status != 200:
                raise LGRobokingApiError(
                    f"기기 상태 조회 실패 (HTTP {resp.status}): {text[:200]}"
                )
            data = json.loads(text)
            if data.get("resultCode") and data.get("resultCode") != "0000":
                raise LGRobokingApiError(
                    f"기기 상태 조회 오류 (코드 {data.get('resultCode')}): {data}"
                )
            result = data.get("result", {})
            snapshot = result.get("snapshot", {})
            return {
                "clean_type": snapshot.get("CLEAN_TYPE", "SUCTION"),
                "suction_level": snapshot.get("SUCTION_LEVEL", "STANDARD"),
                "zz_dist": snapshot.get("ZZ_DIST", "NORMAL"),
                "water_supply_level": snapshot.get("WATERSUPPLY_LEVEL", "LOW1"),
                "smart_turbo": str(snapshot.get("SMART_TURBO", "false")).lower() == "true",
                "robot_state": snapshot.get("ROBOT_STATE", ""),
                "snapshot": snapshot,
                "model_name": result.get("modelName", "B-95AW.CKOR"),
                "alias": result.get("alias", "LG 로보킹 AI 올인원"),
            }

    async def async_post_control(self, payload: dict[str, Any], sync: bool = True) -> dict[str, Any]:
        """Send a control command to the LG ThinQ device API."""
        token, user_no = await self.async_get_access_token()
        session = await self._get_session()
        endpoint = "control-sync" if sync else "control"
        url = f"{DEVICE_BASE_URL}/{self.device_id}/{endpoint}"
        headers = self._build_service_headers(token, user_no)
        headers["content-type"] = "application/json;charset=UTF-8"

        async with session.post(
            url,
            headers=headers,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            text = await resp.text()
            try:
                data = json.loads(text)
            except Exception:
                data = {"raw": text}

            result_code = data.get("resultCode")
            if result_code == "0111":
                raise LGRobokingApiError(
                    "청소기가 주행 중일 때는 설정을 변경할 수 없습니다 (LG 서버 코드 0111). "
                    "충전대에 도킹된 상태에서 변경해 주세요."
                )
            if resp.status != 200 or (result_code and result_code != "0000"):
                raise LGRobokingApiError(
                    f"명령 전송 실패 (HTTP {resp.status}, 코드 {result_code}): {data}"
                )
            return data

    async def async_set_clean_type(self, clean_type: str) -> dict[str, Any]:
        """Set CLEAN_TYPE ('ALL', 'SUCTION', or 'MOP')."""
        mode = clean_type.upper().strip()
        if mode not in ("ALL", "SUCTION", "MOP"):
            raise LGRobokingApiError(f"지원하지 않는 청소 모드입니다: {mode}")

        payload = {
            "ctrlKey": "Control",
            "command": "Set",
            "dataKey": None,
            "dataSetList": {"CLEAN_TYPE": mode},
            "dataGetList": None,
        }
        return await self.async_post_control(payload, sync=True)

    async def async_set_suction_level(self, suction_level: str) -> dict[str, Any]:
        """Set SUCTION_LEVEL ('QUIET', 'STANDARD', 'STRONG', 'MAX')."""
        level = suction_level.upper().strip()
        if level not in ("QUIET", "STANDARD", "STRONG", "MAX"):
            raise LGRobokingApiError(f"지원하지 않는 흡입 세기입니다: {level}")

        payload = {
            "ctrlKey": "Control",
            "command": "Set",
            "dataKey": None,
            "dataSetList": {"SUCTION_LEVEL": level},
            "dataGetList": None,
        }
        return await self.async_post_control(payload, sync=True)

    async def async_set_smart_turbo(self, enable: bool) -> dict[str, Any]:
        """Enable or disable SMART_TURBO mode."""
        val = "true" if enable else "false"
        payload = {
            "ctrlKey": "Control",
            "command": "Set",
            "dataKey": None,
            "dataSetList": {"SMART_TURBO": val},
            "dataGetList": None,
        }
        return await self.async_post_control(payload, sync=True)

    async def async_set_zz_dist(self, zz_dist: str) -> dict[str, Any]:
        """Set ZZ_DIST clean spacing ('NORMAL', 'DEEP', 'DEEPSLOW')."""
        dist = zz_dist.upper().strip()
        if dist not in ("NORMAL", "DEEP", "DEEPSLOW", "QUICK"):
            raise LGRobokingApiError(f"지원하지 않는 청소 간격입니다: {dist}")

        payload = {
            "ctrlKey": "Control",
            "command": "Set",
            "dataKey": None,
            "dataSetList": {"ZZ_DIST": dist},
            "dataGetList": None,
        }
        return await self.async_post_control(payload, sync=True)

    async def async_set_water_supply_level(self, water_level: str) -> dict[str, Any]:
        """Set WATER_SUPPLY_LEVEL ('DRY', 'LOW', 'LOW1', 'HIGH')."""
        lvl = water_level.upper().strip()
        if lvl not in ("DRY", "LOW", "LOW1", "HIGH"):
            raise LGRobokingApiError(f"지원하지 않는 물 공급량입니다: {lvl}")

        payload = {
            "ctrlKey": "Control",
            "command": "Set",
            "dataKey": None,
            "dataSetList": {"WATER_SUPPLY_LEVEL": f"WATER_SUPPLY_{lvl}"},
            "dataGetList": None,
        }
        return await self.async_post_control(payload, sync=True)

    async def async_start_map_stream(self, poscnt: int = 0, posidx: int = 0) -> dict[str, Any]:
        """Send SetR5RTMapUpdate (CMD: UPDATE_DATA) to activate live coordinate streaming on LG cloud."""
        payload = {
            "ctrlKey": "Control",
            "command": "RTMAP",
            "dataKey": None,
            "dataSetList": {
                "CMD": "UPDATE_DATA",
                "POSCNT": str(poscnt),
                "POSIDX": str(posidx),
            },
            "dataGetList": None,
        }
        return await self.async_post_control(payload, sync=False)

    async def async_send_map_heartbeat(self) -> dict[str, Any]:
        """Send RTMAP HEARTBEAT to keep the live map streaming session alive."""
        payload = {
            "ctrlKey": "Control",
            "command": "RTMAP",
            "dataKey": None,
            "dataSetList": {"CMD": "HEARTBEAT"},
            "dataGetList": None,
        }
        return await self.async_post_control(payload, sync=False)

    async def async_wake_up(self) -> dict[str, Any]:
        """Send WakeUp command to wake robot vacuum from sleep mode."""
        payload = {
            "ctrlKey": "ConfigRK",
            "command": "Set",
            "dataKey": None,
            "dataValue": "WakeUp",
            "dataGetList": None,
        }
        return await self.async_post_control(payload, sync=True)

    async def async_send_control_command(
        self,
        ctrl_key: str = "Control",
        command: str = "Set",
        data_value: str | None = None,
        data_set_list: dict[str, Any] | None = None,
        sync: bool = True,
    ) -> dict[str, Any]:
        """Send generic Control command matching official ThinQ Web (my.lgthinq.com) specification."""
        payload: dict[str, Any] = {
            "ctrlKey": ctrl_key,
            "command": command,
            "dataKey": None,
            "dataValue": data_value,
            "dataSetList": data_set_list,
            "dataGetList": None,
        }
        return await self.async_post_control(payload, sync=sync)

    async def async_clean_start(self) -> dict[str, Any]:
        """Start standard cleaning (CLEAN_START)."""
        return await self.async_send_control_command("Control", "Set", data_value="CLEAN_START")

    async def async_clean_pause(self) -> dict[str, Any]:
        """Pause cleaning (PAUSE)."""
        return await self.async_send_control_command("Control", "Set", data_value="PAUSE")

    async def async_clean_stop(self) -> dict[str, Any]:
        """Stop cleaning (CLEAN_STOP)."""
        return await self.async_send_control_command("Control", "Set", data_value="CLEAN_STOP")

    async def async_clean_resume(self) -> dict[str, Any]:
        """Resume paused cleaning (CLEAN_RESUME)."""
        return await self.async_send_control_command("Control", "Set", data_value="CLEAN_RESUME")

    async def async_homing(self) -> dict[str, Any]:
        """Return robot to charging station (HOMING)."""
        return await self.async_send_control_command("Control", "Set", data_value="HOMING")

    async def async_where_is_robot(self) -> dict[str, Any]:
        """Trigger robot location sound/announcement (WHERE_IS_ROBOT)."""
        return await self.async_send_control_command("Control", "Set", data_value="WHERE_IS_ROBOT")

    async def async_clean_start_spot(self) -> dict[str, Any]:
        """Start spot/focus cleaning around current position (CLEAN_START_SPOT)."""
        return await self.async_send_control_command("Control", "Set", data_value="CLEAN_START_SPOT")

    async def async_clean_rooms(self, room_ids: list[int | str]) -> dict[str, Any]:
        """Clean selected rooms in sequence matching official ThinQ HomeTailor API."""
        if not room_ids:
            return await self.async_clean_start()
        seq = ",".join(str(r) for r in room_ids)
        body = {
            "CMD": "CLEAN",
            "NUM": len(room_ids),
            "SEQ": seq,
        }
        return await self.async_send_control_command("Control", "HOMETAILOR", data_set_list=body)

    async def async_station_dust_collect(self, start: bool = True) -> dict[str, Any]:
        """Start or stop station dust collection (STATION_START / STATION_STOP)."""
        cmd = "STATION_START" if start else "STATION_STOP"
        return await self.async_send_control_command("Control", "Set", data_value=cmd)

    async def async_mop_wash(self, start: bool = True) -> dict[str, Any]:
        """Start or stop mop washing at station (MOPWASH_START / MOPWASH_STOP)."""
        cmd = "MOPWASH_START" if start else "MOPWASH_STOP"
        return await self.async_send_control_command("Control", "Set", data_value=cmd)

    async def async_mop_dry(self, start: bool = True) -> dict[str, Any]:
        """Start or stop mop hot-air drying at station (MOPDRY_START / MOPDRY_STOP)."""
        cmd = "MOPDRY_START" if start else "MOPDRY_STOP"
        return await self.async_send_control_command("Control", "Set", data_value=cmd)

    async def async_set_doorsill_climbing(self, enable: bool) -> dict[str, Any]:
        """Enable or disable doorsill climbing mode (DOORSILLCLIMBING:On / Off)."""
        cmd = "DOORSILLCLIMBING:On" if enable else "DOORSILLCLIMBING:Off"
        return await self.async_send_control_command("Control", "Set", data_value=cmd)

    async def async_set_repeat(self, enable: bool) -> dict[str, Any]:
        """Enable or disable repeat cleaning mode (REPEAT: 'true' / 'false')."""
        return await self.async_send_control_command("Control", "Set", data_set_list={"REPEAT": "true" if enable else "false"})
