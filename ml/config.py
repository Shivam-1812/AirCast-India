"""Central configuration for AirCast India."""
from pathlib import Path

SEED = 42
ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROC_DIR = ROOT / "data" / "processed"
MODEL_DIR = ROOT / "models"
REPORT_DIR = ROOT / "reports"
FIG_DIR = REPORT_DIR / "figures"
for _d in (RAW_DIR, PROC_DIR, MODEL_DIR, FIG_DIR):
    _d.mkdir(parents=True, exist_ok=True)

START_DATE = "2022-08-01"  # CAMS global AQ in Open-Meteo is reliable from mid-2022
TIMEZONE = "Asia/Kolkata"

CITIES = {
    "Pune": (18.5204, 73.8567),
    "Mumbai": (19.0760, 72.8777),
    "Delhi": (28.6139, 77.2090),
    "Bengaluru": (12.9716, 77.5946),
    "Chennai": (13.0827, 80.2707),
    "Kolkata": (22.5726, 88.3639),
    "Hyderabad": (17.3850, 78.4867),
    "Ahmedabad": (23.0225, 72.5714),
    "Lucknow": (26.8467, 80.9462),
    "Nagpur": (21.1458, 79.0882),
}

AQ_VARS = ["pm2_5", "pm10", "carbon_monoxide", "nitrogen_dioxide",
           "sulphur_dioxide", "ozone", "aerosol_optical_depth", "dust", "us_aqi"]
WX_VARS = ["temperature_2m", "relative_humidity_2m", "dew_point_2m",
           "surface_pressure", "precipitation", "cloud_cover",
           "wind_speed_10m", "wind_direction_10m"]

# Horizons: 6/24/48/72 are the headline ones; the rest give a smooth hourly curve.
HEADLINE_HORIZONS = [6, 24, 48, 72]
HORIZONS = [6, 12, 24, 36, 48, 60, 72]
ALERT_THRESHOLD = 90.0  # ug/m3 24h-mean PM2.5 -> NAQI "Poor" or worse (>90)

# NAQI PM2.5 categories: (upper bound, name, colour)
NAQI = [
    (30, "Good", "#00b050"),
    (60, "Satisfactory", "#92d050"),
    (90, "Moderate", "#ffd966"),
    (120, "Poor", "#ff9900"),
    (250, "Very Poor", "#ff0000"),
    (float("inf"), "Severe", "#7f0000"),
]


def naqi_category(pm25: float) -> str:
    for ub, name, _ in NAQI:
        if pm25 <= ub:
            return name
    return "Severe"


DIWALI = ["2022-10-24", "2023-11-12", "2024-11-01", "2025-10-20", "2026-11-08"]
