"""Get a my.lgthinq.com refresh token by approving a QR code in the LG ThinQ app.

No browser and no password: this replays what my.lgthinq.com does when you pick
"QR코드 로그인" on the LG account page.

1. nscreen /v1/auth/login → LG account (Keycloak) login page, gives kc_state/nonce
2. websocket-accounts.lgthinq.com "qr-login" → QR text + 6-digit PIN (valid ~60 s);
   once the user approves in the app, the same socket sends an LG account refresh token
3. lgemembers recentAct → kcCode → postSignin (userInfo, signInComplete) → decryptTokenUrl
   → Keycloak → nscreen /v1/auth/callback, which sets the `refresh_token` cookie we want

LG does not document any of this; if they change the login pages this breaks and
the manual token entry in the config flow is the fallback.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from typing import Any

import aiohttp
from yarl import URL

from .const import AUTH_REFRESH_URL, DEFAULT_API_KEY, DEFAULT_APP_VERSION, DEFAULT_CLIENT_ID

_LOGGER = logging.getLogger(__name__)

NSCREEN_LOGIN_URL = AUTH_REFRESH_URL.rsplit("/", 1)[0] + "/login"
QR_SOCKET_URL = "wss://websocket-accounts.lgthinq.com"
QR_CLIENT_ID = "9b0dccb855e24f6a9b576d3e0681ba57"
QR_REDIRECT_URI = "https://account.lge.com/lgacc/front/v1/signin/qrCode"
CALLBACK_URL = "https://my.lgthinq.com"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


class QrLoginError(Exception):
    """The QR login could not be completed."""


class ThinQQrLogin:
    """One QR login attempt. Call start(), show qr/pin, then wait() and finish()."""

    def __init__(self, country: str = "KR", language: str = "ko-KR") -> None:
        self._country = country
        self._language = language
        self._session = aiohttp.ClientSession(
            cookie_jar=aiohttp.CookieJar(unsafe=True), headers={"User-Agent": UA}
        )
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._reader: asyncio.Task | None = None
        self._members = ""
        self._kc_state = ""
        self._nonce = ""
        self._account_token: asyncio.Future[str] | None = None
        self.qr_text = ""
        self.pin = ""
        self.expires_at = 0.0

    def _nscreen_headers(self) -> dict[str, str]:
        return {
            "Origin": "https://my.lgthinq.com",
            "Referer": "https://my.lgthinq.com/",
            "Accept": "application/json",
            "x-thinq-app-type": "WEB",
            "x-client-id": DEFAULT_CLIENT_ID,
            "x-api-key": DEFAULT_API_KEY,
            "x-service-code": "SVC202",
            "x-country-code": self._country,
            "x-language-code": self._language,
            "x-service-phase": "OP",
            "x-thinq-app-ver": DEFAULT_APP_VERSION,
            "x-thinq-app-os": "browser",
            "x-message-id": str(uuid.uuid4()),
        }

    async def start(self) -> None:
        """Open the LG login session (once) and request a fresh QR code."""
        if not self._kc_state:
            async with self._session.get(
                NSCREEN_LOGIN_URL,
                headers=self._nscreen_headers(),
                params={"country": self._country, "language": self._language,
                        "svc_code": "SVC202", "callback_url": CALLBACK_URL},
            ) as resp:
                redirect = ((await resp.json(content_type=None)).get("result") or {}).get("redirectUrl")
            if not redirect:
                raise QrLoginError("ThinQ 로그인 시작 주소를 받지 못했습니다.")
            async with self._session.get(redirect) as resp:
                page = await resp.text()
                self._members = f"{resp.url.scheme}://{resp.url.host}"
            kc_state = re.search(r'kc_state: "([^"]+)"', page)
            nonce = re.search(r'nonce: "([^"]*)"', page)
            if not kc_state:
                raise QrLoginError("LG 계정 로그인 페이지 형식이 바뀌었습니다.")
            self._kc_state, self._nonce = kc_state.group(1), nonce.group(1) if nonce else ""

        await self._close_socket()
        loop = asyncio.get_running_loop()
        self._account_token = loop.create_future()
        qr_ready: asyncio.Future[dict[str, Any]] = loop.create_future()
        self._ws = await self._session.ws_connect(QR_SOCKET_URL, headers={"Origin": self._members})
        await self._ws.send_str(json.dumps({
            "action": "qr-login", "redirect_uri": QR_REDIRECT_URI, "return_type": "token",
            "state": "Y", "client_id": QR_CLIENT_ID,
        }))
        self._reader = asyncio.create_task(self._read(self._ws, qr_ready, self._account_token))
        try:
            msg = await asyncio.wait_for(asyncio.shield(qr_ready), 15)
        except asyncio.TimeoutError as err:
            raise QrLoginError("QR 코드를 받지 못했습니다.") from err
        self.qr_text = msg["qrCode"]
        self.pin = str(msg.get("pinCode") or "")
        self.expires_at = loop.time() + int(msg.get("ttl") or 60)

    @staticmethod
    async def _read(ws, qr_ready: asyncio.Future, token: asyncio.Future) -> None:
        async for msg in ws:
            if msg.type != aiohttp.WSMsgType.TEXT:
                break
            data = json.loads(msg.data)
            if data.get("qrCode") and not qr_ready.done():
                qr_ready.set_result(data)
            elif data.get("refresh_token") and not token.done():
                token.set_result(data["refresh_token"])
                break

    @property
    def expired(self) -> bool:
        return asyncio.get_running_loop().time() >= self.expires_at

    async def wait(self, timeout: float) -> bool:
        """Return True once the user has approved the QR in the app."""
        if self._account_token is None:
            return False
        try:
            await asyncio.wait_for(asyncio.shield(self._account_token), timeout)
        except asyncio.TimeoutError:
            return False
        return True

    async def finish(self) -> str:
        """Turn the approved login into a my.lgthinq.com refresh token."""
        if self._account_token is None or not self._account_token.done():
            raise QrLoginError("아직 앱에서 승인되지 않았습니다.")
        account_token = self._account_token.result()
        await self._close_socket()
        members = self._members
        xhr = {"X-Requested-With": "XMLHttpRequest"}

        async with self._session.post(
            f"{members}/lgacc/service/v1/signin/recentAct",
            data={"refreshToken": account_token, "svcCode": "SVC709", "itgTermsUseFlag": "N", "reqType": "QR"},
            headers={**xhr, "Referer": f"{members}/lgacc/front/v1/signin/qrCode"},
        ) as resp:
            acc = await resp.json(content_type=None)
        if not acc or not acc.get("userNo"):
            raise QrLoginError(f"LG 계정 확인 실패: {str((acc or {}).get('error'))[:120]}")

        last, body = await self._follow(f"{members}/lgacc/service/v1/keycloak/kcCode", {
            "kc_state": self._kc_state, "nonce": self._nonce, "userNo": acc.get("userNo"),
            "userID": acc.get("userID"), "userIDType": acc.get("userIDType"),
            "email": acc.get("displayUserID") or acc.get("email") or "", "auto_login_yn": "",
            "country": acc.get("country"), "language": acc.get("language"),
            "lastLognDate": acc.get("lastLognDate") or "",
        })
        if "postSignin" in last:
            post_token = re.search(r"post_signin_token', '([^']+)'", body)
            if not post_token:
                raise QrLoginError("LG 로그인 마무리 페이지 형식이 바뀌었습니다.")
            async with self._session.post(
                f"{members}/lgacc/service/v1/keycloak/userInfo", data={}, headers={**xhr, "Referer": last}
            ) as resp:
                account = ((await resp.json(content_type=None)) or {}).get("account") or {}
            device = uuid.uuid4().hex
            async with self._session.post(
                f"{members}/lgacc/front/v1/signin/signInComplete",
                data={"loginSessionID": account.get("loginSessionID") or "", "uuid": device,
                      "svcCode": "SVC202", "serviceYn": "Y", "deviceId": device,
                      "autoYn": "N", "ipadYn": "N"},
                headers={**xhr, "Referer": last},
            ) as resp:
                done = (await resp.json(content_type=None)) or {}
            if done.get("code") != "SUCCESS":
                raise QrLoginError(f"LG 로그인 완료 처리 실패: {done.get('code')}")
            await self._follow(f"{members}/lgacc/service/v1/keycloak/decryptTokenUrl",
                               {"token": post_token.group(1)})

        token = next((c.value for c in self._session.cookie_jar if c.key == "refresh_token"), None)
        if not token:
            raise QrLoginError("ThinQ 토큰을 받지 못했습니다. LG 로그인 과정이 바뀌었을 수 있습니다.")
        return token

    async def _follow(self, url: str, data: dict[str, Any]) -> tuple[str, str]:
        """POST, then follow redirects only, stopping at my.lgthinq.com. Returns (last url, body)."""
        method: str = "POST"
        payload: dict[str, Any] | None = data
        for _ in range(10):
            async with self._session.request(method, url, data=payload, allow_redirects=False) as resp:
                location = resp.headers.get("Location")
                if not location:
                    return str(resp.url), await resp.text()
                url = str(resp.url.join(URL(location)))
            method, payload = "GET", None
            if URL(url).host == "my.lgthinq.com":
                return url, ""
        raise QrLoginError("LG 로그인 리다이렉트가 너무 깁니다.")

    async def _close_socket(self) -> None:
        if self._reader and not self._reader.done():
            self._reader.cancel()
        if self._ws and not self._ws.closed:
            await self._ws.close()
        self._reader = self._ws = None

    async def close(self) -> None:
        await self._close_socket()
        await self._session.close()
