"""Merge AQ + weather, build a complete hourly grid, interpolate small gaps, clip."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import AQ_VARS, CITIES, PROC_DIR, RAW_DIR, WX_VARS

POLLUTANTS = ["pm2_5", "pm10", "carbon_monoxide", "nitrogen_dioxide", "sulphur_dioxide",
              "ozone", "aerosol_optical_depth", "dust"]


def now_ist() -> pd.Timestamp:
    return pd.Timestamp.now(tz="Asia/Kolkata").tz_localize(None).floor("h")


def load_city(city: str, upto: pd.Timestamp | None = None) -> pd.DataFrame:
    aq = pd.read_parquet(RAW_DIR / f"{city}_aq.parquet")
    wx = pd.read_parquet(RAW_DIR / f"{city}_weather.parquet")
    df = aq.join(wx, how="outer")
    df.index.name = "timestamp"
    upto = upto or now_ist()
    df = df[df.index <= upto]                      # drop model-forecast hours
    df = df.dropna(subset=["pm2_5"])               # CAMS history starts mid-2022
    if df.empty:
        return df
    grid = pd.date_range(df.index.min(), df.index.max(), freq="h", name="timestamp")
    df = df.reindex(grid)
    df = df.interpolate(method="linear", limit=3, limit_area="inside")
    return df


def clean_city(city: str, upto: pd.Timestamp | None = None) -> pd.DataFrame:
    df = load_city(city, upto)
    for c in POLLUTANTS + ["us_aqi", "precipitation", "wind_speed_10m"]:
        df[c] = df[c].clip(lower=0)
    df["relative_humidity_2m"] = df["relative_humidity_2m"].clip(0, 100)
    df["cloud_cover"] = df["cloud_cover"].clip(0, 100)
    rad = np.deg2rad(df["wind_direction_10m"])
    df["wind_dir_sin"], df["wind_dir_cos"] = np.sin(rad), np.cos(rad)
    df = df.drop(columns=["wind_direction_10m"])
    df.insert(0, "city", city)
    return df


def build_clean(upto: pd.Timestamp | None = None) -> pd.DataFrame:
    frames = [clean_city(c, upto) for c in CITIES]
    df = pd.concat(frames).reset_index()
    # rows that still miss the core signal (large gaps) are kept as NaN rows so
    # that time-continuity (shift by hours) stays valid; features drop them later.
    return df.sort_values(["city", "timestamp"]).reset_index(drop=True)


def main() -> None:
    df = build_clean()
    assert not df.duplicated(["city", "timestamp"]).any()
    neg = (df[POLLUTANTS] < 0).sum().sum()
    assert neg == 0, f"{neg} negative pollutant values"
    for c, g in df.groupby("city"):
        assert (g["timestamp"].diff().dropna() == pd.Timedelta("1h")).all(), c
    df.to_parquet(PROC_DIR / "clean.parquet")
    print(df.groupby("city").agg(rows=("pm2_5", "size"), missing_pm25=("pm2_5", lambda s: s.isna().sum()),
                                 start=("timestamp", "min"), end=("timestamp", "max")))


if __name__ == "__main__":
    main()
