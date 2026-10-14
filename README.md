# [KR] LG 코드제로 로보킹 AI 올인원 (B95) - Home Assistant 커스텀 통합구성요소

공식 `lg_thinq` 통합구성요소에서 지원하지 않는 **LG 코드제로 로보킹 AI 올인원(B-95AW.CKOR 등)**의 **청소 방식(`먼지 흡입 + 물걸레` / `먼지 흡입` / `물걸레`)**을 제어하고 실시간으로 동기화하는 HACS 커스텀 통합구성요소입니다.

## 주요 기능

- **네이티브 `select.lg_roboking_mode` 엔티티 제공**: 별도의 `shell_command`, `input_select`, 동기화용 `automation` 없이 단일 통합구성요소로 양방향 제어 및 10분 주기 클라우드 상태 동기화를 수행합니다.
- **기존 설정 자동 감지 및 마이그레이션**: `/config/www/lg_roboking_config.json`이 존재하면 통합구성요소 추가 시 Refresh Token과 Device ID를 자동으로 불러와 기본값으로 채워줍니다.
- **안전한 토큰 자동 로테이션(Token Rotation)**: LG OIDC 서버(`kic-nscreen.lgthinq.com`)가 새 `refresh_token` 쿠키를 반환할 때마다 Home Assistant 보안 스토리지(`.storage/core.config_entries`)에 자동 저장합니다.
- **팝업 로그인 토큰 추출 도구 포함**: 추후 토큰이 만료되었을 때 개발자 도구(F12) 없이 로그인 팝업으로 새 토큰을 뽑을 수 있는 `tools/get_lg_token.py`를 제공합니다.

## HACS 설치 방법

1. Home Assistant의 **HACS → 통합구성요소** 메뉴로 이동합니다.
2. 우측 상단 점 3개(`⋮`) 메뉴 → **사용자 지정 저장소(Custom repositories)**를 클릭합니다.
3. 저장소 URL에 `https://github.com/ggulamtggul/lg_roboking`을 입력하고, 카테고리로 **통합구성요소(Integration)**를 선택한 뒤 **추가**를 누릅니다.
4. 목록에서 **LG 로보킹 AI 올인원**을 찾아 **다운로드**한 뒤 **Home Assistant를 재시작**합니다.
5. **설정 → 기기 및 서비스 → 통합구성요소 추가**에서 **LG 로보킹 AI 올인원**을 검색해 추가합니다. (기존 `lg_roboking_config.json`이 있으면 자동으로 입력되어 있으므로 바로 **제출**을 누르면 됩니다.)

## 제공 엔티티 및 서비스

| 구분 | ID | 설명 |
| :--- | :--- | :--- |
| **Select** | `select.lg_roboking_mode` | `먼지 흡입 + 물걸레` (`ALL`), `먼지 흡입` (`SUCTION`), `물걸레` (`MOP`) 선택 및 상태 표시 |
| **Button** | `button.lg_roboking_sync_from_cloud` | LG ThinQ 클라우드에서 현재 설정된 청소 방식을 즉시 다시 읽어옴 |
| **Service** | `lg_roboking.set_clean_mode` | `mode: ALL / SUCTION / MOP` 파라미터로 청소 방식을 직접 변경 |

## 외출 자동화 예시 (화/금 물걸레+흡입, 월/수/목 흡입 전용)

```yaml
actions:
  - action: select.select_option
    target:
      entity_id: select.lg_roboking_mode
    data:
      option: "{% if now().weekday() in [1, 4] %}먼지 흡입 + 물걸레{% else %}먼지 흡입{% endif %}"
  - delay:
      seconds: 5
  - action: vacuum.start
    target:
      entity_id: vacuum.robosceongsogi
  - delay:
      seconds: 10
  - action: vacuum.start
    target:
      entity_id: vacuum.robosceongsogi
```

## 주의사항

- **주행 중 모드 변경 불가**: 청소기가 스테이션을 벗어나 주행 중일 때 청소 방식을 변경하면 LG 서버가 에러코드(`0111`)를 반환합니다. 반드시 도킹/충전 상태에서 모드를 변경한 뒤 청소를 시작하세요.
