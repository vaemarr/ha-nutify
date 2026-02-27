"""Constants for the Nutify Link UPS Monitor integration."""

DOMAIN = "nutify_link"
PLATFORMS = ["sensor", "binary_sensor"]

# Configuration keys
CONF_HOST = "host"
CONF_PORT = "port"
CONF_USE_SSL = "use_ssl"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_SCAN_INTERVAL = "scan_interval"

# Defaults
DEFAULT_PORT = 5050
DEFAULT_USE_SSL = False
DEFAULT_SCAN_INTERVAL = 30  # seconds

# API paths
API_LOGIN = "/auth/api/login"
API_AUTH_STATUS = "/auth/api/status"
API_DATA_ALL = "/api/data/all"
API_BATTERY_METRICS = "/api/battery/metrics"
API_POWER_METRICS = "/api/power/metrics"
API_VOLTAGE_METRICS = "/api/voltage/metrics"

# Future API key support (header name when Nutify adds key-based auth)
API_KEY_HEADER = "X-API-Key"

# UPS status code to human-readable display mapping
UPS_STATUS_MAP: dict[str, str] = {
    "OL": "Online",
    "OB": "On Battery",
    "LB": "Low Battery",
    "HB": "High Battery",
    "RB": "Replace Battery",
    "CHRG": "Charging",
    "DISCHRG": "Discharging",
    "BYPASS": "Bypass",
    "CAL": "Calibrating",
    "OFF": "Offline",
    "OVER": "Overloaded",
    "TRIM": "Trimming",
    "BOOST": "Boosting",
}
