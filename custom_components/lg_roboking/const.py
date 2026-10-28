"""Constants for the LG Roboking AI All-in-One custom integration."""
from homeassistant.const import Platform

DOMAIN = "lg_roboking"
PLATFORMS: list[Platform] = [
    Platform.VACUUM,
    Platform.SELECT,
    Platform.BUTTON,
    Platform.SWITCH,
    Platform.CAMERA,
]

CONF_DEVICE_ID = "device_id"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_CLIENT_ID = "client_id"
CONF_API_KEY = "api_key"
CONF_APP_VERSION = "app_version"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_MAP_REFRESH_INTERVAL = "map_refresh_interval"
CONF_SYNC_LEGACY_JSON = "sync_legacy_json"

DEFAULT_CLIENT_ID = "79b237256c9129df9f43207e279b4cf240926a6f3734d960740cd2b3846f748a"
DEFAULT_API_KEY = "VGhpblEyLjAgU0VSVklDRQ=="
DEFAULT_APP_VERSION = "5.2.1200"
DEFAULT_SCAN_INTERVAL = 10  # minutes (background token/status sync)
DEFAULT_MAP_REFRESH_INTERVAL = 2  # seconds (during active cleaning)

LEGACY_CONFIG_PATHS = [
    "/config/www/lg_roboking_config.json",
    "/config/lg_roboking_config.json",
]

AUTH_REFRESH_URL = "https://kic-nscreen.lgthinq.com/v1/auth/refresh"
DEVICE_BASE_URL = "https://kic-service.lgthinq.com:46030/v1/service/devices"
DASHBOARD_URL = "https://kic-service.lgthinq.com:46030/v1/service/application/dashboard"

# Clean Type Mapping (API Code <-> Korean Label)
CLEAN_TYPE_TO_LABEL: dict[str, str] = {
    "ALL": "먼지 흡입 + 물걸레",
    "SUCTION": "먼지 흡입",
    "MOP": "물걸레",
}
LABEL_TO_CLEAN_TYPE: dict[str, str] = {v: k for k, v in CLEAN_TYPE_TO_LABEL.items()}
CLEAN_TYPE_OPTIONS: list[str] = list(CLEAN_TYPE_TO_LABEL.values())

# Suction Level Mapping (QUIET, STANDARD, STRONG, MAX)
SUCTION_LEVEL_TO_LABEL: dict[str, str] = {
    "QUIET": "조용히",
    "STANDARD": "표준",
    "STRONG": "강하게",
    "MAX": "최대(터보)",
}
LABEL_TO_SUCTION_LEVEL: dict[str, str] = {v: k for k, v in SUCTION_LEVEL_TO_LABEL.items()}
SUCTION_LEVEL_OPTIONS: list[str] = list(SUCTION_LEVEL_TO_LABEL.values())

# Cleaning Distance / Zigzag Distance (QUICK, NORMAL, DEEP, DEEPSLOW)
# Official LG ThinQ B95 App Labels: 넓게, 기본, 좁게, 꼼꼼+
ZZ_DIST_TO_LABEL: dict[str, str] = {
    "QUICK": "넓게",
    "NORMAL": "기본",
    "DEEP": "좁게",
    "DEEPSLOW": "꼼꼼+",
}
LABEL_TO_ZZ_DIST: dict[str, str] = {
    "넓게": "QUICK",
    "기본": "NORMAL",
    "보통": "NORMAL",
    "좁게": "DEEP",
    "꼼꼼": "DEEP",
    "꼼꼼+": "DEEPSLOW",
    "꼼꼼하고 천천히": "DEEPSLOW",
}
ZZ_DIST_OPTIONS: list[str] = ["넓게", "기본", "좁게", "꼼꼼+"]

# Water Supply Level (DRY, LOW, LOW1, HIGH)
WATER_SUPPLY_TO_LABEL: dict[str, str] = {
    "DRY": "마른 걸레",
    "LOW": "적게 (1단계)",
    "LOW1": "보통 (2단계)",
    "HIGH": "많이 (3단계)",
}
LABEL_TO_WATER_SUPPLY: dict[str, str] = {v: k for k, v in WATER_SUPPLY_TO_LABEL.items()}
WATER_SUPPLY_OPTIONS: list[str] = list(WATER_SUPPLY_TO_LABEL.values())

# Services
SERVICE_SET_CLEAN_MODE = "set_clean_mode"
SERVICE_WAKE_UP = "wake_up"
SERVICE_SET_SUCTION_LEVEL = "set_suction_level"
SERVICE_SET_ZZ_DIST = "set_zz_dist"
SERVICE_SET_WATER_LEVEL = "set_water_level"
SERVICE_SET_SMART_TURBO = "set_smart_turbo"

ATTR_MODE = "mode"
ATTR_LEVEL = "level"
ATTR_ENABLED = "enabled"

SERVICE_CLEAN_START = "clean_start"
SERVICE_PAUSE = "pause"
SERVICE_CLEAN_STOP = "clean_stop"
SERVICE_RETURN_TO_BASE = "return_to_base"
SERVICE_LOCATE = "locate"
SERVICE_CLEAN_SPOT = "clean_spot"
SERVICE_CLEAN_ROOMS = "clean_rooms"
SERVICE_DUST_COLLECT = "dust_collect"
SERVICE_MOP_WASH = "mop_wash"
SERVICE_MOP_DRY = "mop_dry"
SERVICE_SET_DOORSILL_CLIMBING = "set_doorsill_climbing"
SERVICE_SET_REPEAT = "set_repeat"

ATTR_ROOM_IDS = "room_ids"
