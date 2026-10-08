"""Leak-free feature engineering. Every feature at row t uses only data at times <= t."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import ALERT_THRESHOLD, CITIES, DIWALI, HORIZONS, PROC_DIR

LAGS = [1, 2, 3, 6, 12, 24, 48, 72, 168]
WINDOWS = [6, 24, 72, 168]
CITY_CODES = {c: i for i, c in enumerate(CITIES)}
TARGETS = [f"pm25_t+{h}h" for h in HORIZONS]
SEASONS = {12: 0, 1: 0, 2: 0, 3: 1, 4: 1, 5: 1, 6: 2, 7: 2, 8: 2, 9: 2, 10: 3, 11: 3}
# 0 winter, 1 pre-monsoon, 2 monsoon, 3 post-monsoon

_DIWALI = pd.to_datetime(DIWALI)


def _per_city(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("city", sort=False)
    out = {}
    pm = g["pm2_5"]
    for l in LAGS:
        out[f"pm25_lag_{l}"] = pm.shift(l)
    for w in WINDOWS:
        r = pm.rolling(w, min_periods=max(2, w // 2))
        out[f"pm25_mean_{w}"] = r.mean().reset_index(level=0, drop=True)
        out[f"pm25_std_{w}"] = r.std().reset_index(level=0, drop=True)
        out[f"pm25_min_{w}"] = r.min().reset_index(level=0, drop=True)
        out[f"pm25_max_{w}"] = r.max().reset_index(level=0, drop=True)
    for c, short in [("pm10", "pm10"), ("nitrogen_dioxide", "no2"), ("carbon_monoxide", "co")]:
        out[f"{short}_mean_24"] = (g[c].rolling(24, min_periods=12).mean()
                                   .reset_index(level=0, drop=True))
    out["pm25_diff_24"] = df["pm2_5"] - out["pm25_lag_24"]
    out["pm25_diff_6"] = df["pm2_5"] - out["pm25_lag_6"]
    out["pm25_slope_6"] = (df["pm2_5"] - out["pm25_lag_6"]) / 6.0
    out["pm25_ratio_24"] = df["pm2_5"] / (out["pm25_mean_24"] + 1.0)
    out["rain_24h"] = g["precipitation"].rolling(24, min_periods=12).sum().reset_index(level=0, drop=True)
    out["rain_72h"] = g["precipitation"].rolling(72, min_periods=36).sum().reset_index(level=0, drop=True)
    out["wind_mean_24"] = g["wind_speed_10m"].rolling(24, min_periods=12).mean().reset_index(level=0, drop=True)
    out["temp_change_24"] = df["temperature_2m"] - g["temperature_2m"].shift(24)
    out["pressure_change_24"] = df["surface_pressure"] - g["surface_pressure"].shift(24)
    out["pm25_lag_24_to_1_ratio"] = out["pm25_lag_24"] / (out["pm25_lag_1"] + 1.0)
    return pd.DataFrame(out, index=df.index)


def _targets(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("city", sort=False)["pm2_5"]
    out = {f"pm25_t+{h}h": g.shift(-h) for h in HORIZONS}
    fwd24 = g.rolling(24, min_periods=24).mean().reset_index(level=0, drop=True)  # mean of t-23..t
    # mean over t+1..t+24 == trailing mean at t+24
    fwd24 = fwd24.groupby(df["city"], sort=False).shift(-24)
    out["pm25_fwd24_mean"] = fwd24
    out["alert_24h"] = (fwd24 > ALERT_THRESHOLD).astype(float).where(fwd24.notna())
    return pd.DataFrame(out, index=df.index)


def build_features(clean: pd.DataFrame, with_targets: bool = True) -> pd.DataFrame:
    """clean: output of ml.clean (columns city, timestamp, ...). Rows must be hourly-contiguous per city."""
    df = clean.sort_values(["city", "timestamp"]).reset_index(drop=True)
    feats = _per_city(df)
    ts = df["timestamp"]
    cal = pd.DataFrame({
        "hour": ts.dt.hour, "dow": ts.dt.dayofweek, "month": ts.dt.month,
        "doy": ts.dt.dayofyear, "is_weekend": (ts.dt.dayofweek >= 5).astype(int),
    }, index=df.index)
    cal["hour_sin"] = np.sin(2 * np.pi * cal["hour"] / 24)
    cal["hour_cos"] = np.cos(2 * np.pi * cal["hour"] / 24)
    cal["month_sin"] = np.sin(2 * np.pi * cal["month"] / 12)
    cal["month_cos"] = np.cos(2 * np.pi * cal["month"] / 12)
    cal["season"] = cal["month"].map(SEASONS)
    days = ts.dt.normalize().values[:, None].astype("datetime64[D]") - _DIWALI.values[None, :].astype("datetime64[D]")
    days = days.astype(int)
    cal["diwali_window"] = ((days >= -3) & (days <= 5)).any(axis=1).astype(int)

    base_cols = ["pm2_5", "pm10", "carbon_monoxide", "nitrogen_dioxide", "sulphur_dioxide", "ozone",
                 "aerosol_optical_depth", "dust", "temperature_2m", "relative_humidity_2m", "dew_point_2m",
                 "surface_pressure", "precipitation", "cloud_cover", "wind_speed_10m",
                 "wind_dir_sin", "wind_dir_cos"]
    out = pd.concat([df[["city", "timestamp"]], df[base_cols], feats, cal], axis=1)
    out["humid_temp"] = out["relative_humidity_2m"] * out["temperature_2m"] / 100.0
    out["stagnation"] = (out["surface_pressure"] / 1000.0) / (out["wind_speed_10m"] + 1.0)
    out["pm25_pm10_ratio"] = out["pm2_5"] / (out["pm10"] + 1.0)
    out["no2_co_ratio"] = out["nitrogen_dioxide"] / (out["carbon_monoxide"] + 1.0)
    out["city_code"] = out["city"].map(CITY_CODES)
    out["lat"] = out["city"].map(lambda c: CITIES[c][0])
    out["lon"] = out["city"].map(lambda c: CITIES[c][1])
    if with_targets:
        out = pd.concat([out, _targets(df)], axis=1)
    return out


FEATURE_EXCLUDE = {"city", "timestamp", "pm25_fwd24_mean", "alert_24h", *TARGETS}


def feature_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c not in FEATURE_EXCLUDE]


def main() -> None:
    clean = pd.read_parquet(PROC_DIR / "clean.parquet")
    f = build_features(clean)
    lag_cols = [c for c in f.columns if "lag_168" in c or c == "pm25_mean_168"]
    f = f.dropna(subset=lag_cols + TARGETS + ["alert_24h"]).reset_index(drop=True)
    f.to_parquet(PROC_DIR / "features.parquet")
    print("shape:", f.shape, "| features:", len(feature_columns(f)))
    nn = f[feature_columns(f)].isna().mean()
    print("NaN share (cols with any):\n", nn[nn > 0].round(4).to_string() or "none")
    print("alert rate:", f["alert_24h"].mean().round(3))


if __name__ == "__main__":
    main()
