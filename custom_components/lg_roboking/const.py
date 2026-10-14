"""Constants for the LG Roboking AI All-in-One custom integration."""
from homeassistant.const import Platform

DOMAIN = "lg_roboking"
PLATFORMS: list[Platform] = [Platform.SELECT, Platform.BUTTON]

CONF_DEVICE_ID = "device_id"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_CLIENT_ID = "client_id"
CONF_API_KEY = "api_key"
CONF_APP_VERSION = "app_version"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_SYNC_LEGACY_JSON = "sync_legacy_json"

DEFAULT_CLIENT_ID = "79b237256c9129df9f43207e279b4cf240926a6f3734d960740cd2b3846f748a"
DEFAULT_API_KEY = "VGhpblEyLjAgU0VSVklDRQ=="
DEFAULT_APP_VERSION = "5.2.1200"
DEFAULT_SCAN_INTERVAL = 10  # minutes

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

SERVICE_SET_CLEAN_MODE = "set_clean_mode"
ATTR_MODE = "mode"
