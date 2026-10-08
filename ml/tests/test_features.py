"""Leakage test: features at time t must not change when data after t is perturbed."""
import numpy as np
import pandas as pd

from ml.config import CITIES
from ml.features import build_features, feature_columns


def _synthetic(n=600, seed=0):
    rng = np.random.default_rng(seed)
    ts = pd.date_range("2024-01-01", periods=n, freq="h")
    frames = []
    for city in list(CITIES)[:2]:
        d = pd.DataFrame({"city": city, "timestamp": ts})
        for c in ["pm2_5", "pm10", "carbon_monoxide", "nitrogen_dioxide", "sulphur_dioxide", "ozone",
                  "aerosol_optical_depth", "dust", "temperature_2m", "relative_humidity_2m", "dew_point_2m",
                  "surface_pressure", "precipitation", "cloud_cover", "wind_speed_10m",
                  "wind_dir_sin", "wind_dir_cos"]:
            d[c] = rng.random(n) * 50 + 1
        frames.append(d)
    return pd.concat(frames, ignore_index=True)


def test_no_future_leakage():
    df = _synthetic()
    t0 = pd.Timestamp("2024-01-20 00:00")
    a = build_features(df)
    df2 = df.copy()
    future = df2["timestamp"] > t0
    num = df2.select_dtypes("number").columns
    df2.loc[future, num] = df2.loc[future, num] * 7 + 100
    b = build_features(df2)
    cols = feature_columns(a)
    ma = a[a["timestamp"] <= t0][cols].reset_index(drop=True)
    mb = b[b["timestamp"] <= t0][cols].reset_index(drop=True)
    pd.testing.assert_frame_equal(ma, mb)


def test_target_is_future_value():
    df = _synthetic()
    f = build_features(df)
    g = f[f["city"] == f["city"].iloc[0]].reset_index(drop=True)
    assert g.loc[10, "pm25_t+24h"] == g.loc[34, "pm2_5"]
    assert np.isclose(g.loc[10, "pm25_fwd24_mean"], g.loc[11:34, "pm2_5"].mean())
