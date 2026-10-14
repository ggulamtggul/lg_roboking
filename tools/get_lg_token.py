#!/usr/bin/env python3
"""
LG ThinQ Web (my.lgthinq.com) 팝업 로그인 기반 Refresh Token & Device ID 자동 추출 도구
사용법:
  pip install playwright
  playwright install chromium
  python3 get_lg_token.py
"""
import asyncio
import json
import sys

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("이 스크립트는 playwright가 필요합니다. 아래 명령어를 먼저 실행해 주세요:")
    print("  pip install playwright && playwright install chromium")
    sys.exit(1)


async def main() -> None:
    print("=" * 65)
    print(" [LG 로보킹 AI 올인원] LG ThinQ 로그인 팝업 토큰 자동 추출기")
    print("=" * 65)
    print("1. 잠시 후 열리는 크롬 팝업창에서 LG 계정으로 로그인해 주세요.")
    print("2. 로그인이 완료되어 ThinQ 홈 화면이 뜨면 토큰과 기기 ID를 자동으로 추출합니다.\n")

    refresh_token = None
    device_id = None

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        async def handle_response(response):
            nonlocal device_id
            if "kic-service.lgthinq.com" in response.url and "/devices/" in response.url:
                parts = response.url.split("/devices/")
                if len(parts) > 1:
                    candidate = parts[1].split("/")[0].split("?")[0]
                    if len(candidate) >= 20:
                        device_id = candidate

        page.on("response", handle_response)
        await page.goto("https://my.lgthinq.com")

        for _ in range(300):  # 최대 5분 대기
            cookies = await context.cookies()
            for c in cookies:
                if c.get("name") == "refresh_token" and c.get("value", "").startswith("eyJ"):
                    refresh_token = c["value"]
                    break
            if refresh_token:
                await asyncio.sleep(3)
                break
            await asyncio.sleep(1)

        await browser.close()

    if not refresh_token:
        print("\n[실패] 시간 내에 refresh_token 쿠키를 찾지 못했습니다.")
        sys.exit(1)

    result = {
        "device_id": device_id or "자동 탐색 (비워두어도 무방)",
        "refresh_token": refresh_token,
    }
    print("\n" + "=" * 65)
    print(" [성공] 아래 Refresh Token을 Home Assistant 통합구성요소 설정창에 붙여넣으세요!")
    print("=" * 65)
    print(f"\n[Device ID]:\n{result['device_id']}")
    print(f"\n[Refresh Token]:\n{refresh_token}\n")


if __name__ == "__main__":
    asyncio.run(main())
