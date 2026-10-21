# [KR] LG 코드제로 로보킹 AI 올인원 (B95) - Home Assistant 커스텀 통합구성요소

공식 `lg_thinq` 통합구성요소에서 지원하지 않는 **LG 코드제로 로보킹 AI 올인원(B-95AW.CKOR 등)**의 **실시간 맵 스트리밍, 흡입 세기, 물 공급량, 청소 간격(꼼꼼 청소), 스마트 터보 및 청소 방식**을 완벽하게 제어하고 동기화하는 HACS 커스텀 통합구성요소입니다.

---

## 🚀 v1.2.0 주요 신규 기능

1. **실시간 맵 카메라 (`camera.roboking_map`)**:
   - LG ThinQ 전용 `RTMAP HEARTBEAT` 프로토콜 기반 실시간 맵 세션 유지.
   - 방 구획별 파스텔 컬러, 벽/장애물 테두리, 금지구역(가상벽/금지영역), 충전 도크 위치, 로봇 실시간 좌표 및 진행 방향 화살표, 주행 궤적을 고해상도로 네이티브 렌더링.
   - 대기/충전 중에는 마지막 맵 이미지를 캐싱하고 하트비트를 중단하여 불필요한 배터리/클라우드 트래픽 방지.
   - 청소 중 실시간 맵 갱신 주기를 사용자가 5초~60초(기본 10초)로 자유롭게 설정 가능.
2. **흡입 세기 제어 (`select.lg_roboking_suction_power`)**:
   - `조용히` (`QUIET`), `표준` (`STANDARD`), `강하게` (`STRONG`), `최대(터보)` (`MAX`).
3. **청소 간격 / 꼼꼼 청소 제어 (`select.lg_roboking_clean_distance`)**:
   - `보통` (`NORMAL`), `꼼꼼` (`DEEP`), `꼼꼼하고 천천히` (`DEEPSLOW`).
4. **물걸레 물 공급량 제어 (`select.lg_roboking_water_level`)**:
   - `마른 걸레` (`DRY`), `적게 - 1단계` (`LOW`), `보통 - 2단계` (`LOW1`), `많이 - 3단계` (`HIGH`).
5. **스마트 터보 토글 (`switch.lg_roboking_smart_turbo`)**:
   - 카펫 감지 시 자동으로 흡입력을 터보로 높여주는 스마트 터보 기능 ON/OFF.
6. **네이티브 청소 방식 제어 (`select.lg_roboking_mode`)**:
   - `먼지 흡입 + 물걸레` (`ALL`), `먼지 흡입` (`SUCTION`), `물걸레` (`MOP`).
7. **원격 절전 해제 (`button.lg_roboking_wake_up`)**:
   - 공식 `WakeUp` API 호출로 딥 슬립 상태의 청소기를 즉시 기상시켜 자동화 실패 방지.

---

## 📦 제공 엔티티 및 서비스

| 구분 | Entity ID | 설명 |
| :--- | :--- | :--- |
| **Camera** | `camera.roboking_map` | 실시간 청소 맵 (방 구획, 로봇 위치/방향, 도크, 금지구역, 궤적) |
| **Select** | `select.lg_roboking_mode` | 청소 방식: `먼지 흡입 + 물걸레`, `먼지 흡입`, `물걸레` |
| **Select** | `select.lg_roboking_suction_power` | 흡입 세기: `조용히`, `표준`, `강하게`, `최대(터보)` |
| **Select** | `select.lg_roboking_clean_distance` | 청소 간격: `보통`, `꼼꼼`, `꼼꼼하고 천천히` |
| **Select** | `select.lg_roboking_water_level` | 물 공급량: `마른 걸레`, `적게 (1단계)`, `보통 (2단계)`, `많이 (3단계)` |
| **Switch** | `switch.lg_roboking_smart_turbo` | 카펫 감지 자동 스마트 터보 ON / OFF |
| **Button** | `button.lg_roboking_wake_up` | 절전 모드 해제 (WakeUp) |
| **Button** | `button.lg_roboking_sync_from_cloud` | LG ThinQ 클라우드에서 최신 설정값 즉시 수동 동기화 |

### 제공 서비스 (Services)

- `lg_roboking.wake_up`: 기기 기상 명령 전송.
- `lg_roboking.set_clean_mode`: `mode: ALL / SUCTION / MOP` (청소 방식 변경).
- `lg_roboking.set_suction_level`: `level: QUIET / STANDARD / STRONG / MAX` (흡입 세기 변경).
- `lg_roboking.set_zz_dist`: `level: NORMAL / DEEP / DEEPSLOW` (청소 간격 변경).
- `lg_roboking.set_water_level`: `level: DRY / LOW / LOW1 / HIGH` (물 공급량 변경).
- `lg_roboking.set_smart_turbo`: `enabled: true / false` (스마트 터보 토글).

---

## 🛠️ HACS 설치 및 업데이트 방법

1. Home Assistant의 **HACS → 통합구성요소** 메뉴로 이동합니다.
2. 기존 설치자의 경우 `lg_roboking`의 **업데이트(v1.2.0)** 버튼을 누르고 **Home Assistant 재시작**을 진행합니다.
3. 신규 설치자의 경우:
   - 우측 상단 점 3개(`⋮`) → **사용자 지정 저장소** 클릭
   - `https://github.com/ggulamtggul/lg_roboking` 입력 후 카테고리 **통합구성요소** 선택
   - **LG 로보킹 AI 올인원** 다운로드 후 HA 재시작
   - **설정 → 기기 및 서비스 → 통합구성요소 추가**에서 **LG 로보킹 AI 올인원** 추가

---

## 💡 대시보드 Lovelace 카드 구성 예시

### 실시간 맵 카드
```yaml
type: picture-entity
entity: camera.roboking_map
show_state: false
show_name: true
name: 우리집 청소 현황
```

### 올인원 제어 카드 (Entities 카드)
```yaml
type: entities
title: 로보킹 세부 제어
entities:
  - entity: select.lg_roboking_mode
  - entity: select.lg_roboking_suction_power
  - entity: select.lg_roboking_clean_distance
  - entity: select.lg_roboking_water_level
  - entity: switch.lg_roboking_smart_turbo
  - entity: button.lg_roboking_wake_up
```

---

## ⚠️ 주의사항

- **주행 중 모드/방식 변경 불가**: 청소기가 스테이션을 벗어나 주행 중일 때 청소 방식을 변경하면 LG 서버가 에러코드(`0111`)를 반환합니다. 반드시 충전대(도킹) 상태에서 모드를 변경한 뒤 청소를 시작하세요.
