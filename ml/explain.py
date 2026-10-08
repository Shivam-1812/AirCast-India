"""SHAP explanations for the 24 h PM2.5 forecast (dedicated LightGBM explainer model)."""
from __future__ import annotations

import json
import re

import joblib
import numpy as np
import pandas as pd
import shap

from .config import FIG_DIR, MODEL_DIR, PROC_DIR
from .features import feature_columns
from .models import make_lgbm

H = 24
EXPLAIN_PATH = MODEL_DIR / "explain_lgbm_24h.joblib"

LABELS = {
    "pm2_5": "current PM2.5", "pm10": "current PM10", "carbon_monoxide": "carbon monoxide", "nitrogen_dioxide": "NO2",
    "sulphur_dioxide": "SO2", "ozone": "ozone", "aerosol_optical_depth": "aerosol load", "dust": "airborne dust",
    "temperature_2m": "temperature", "relative_humidity_2m": "humidity", "dew_point_2m": "dew point",
    "surface_pressure": "air pressure", "precipitation": "current rain", "cloud_cover": "cloud cover",
    "wind_speed_10m": "wind speed", "wind_dir_sin": "wind direction", "wind_dir_cos": "wind direction",
    "rain_24h": "rain in the last 24 h", "rain_72h": "rain in the last 3 days", "wind_mean_24": "average wind over the last day",
    "stagnation": "air stagnation (calm, high pressure)", "humid_temp": "humidity-temperature mix",
    "temp_change_24": "24 h temperature change", "pressure_change_24": "24 h pressure change",
    "hour": "time of day", "hour_sin": "time of day", "hour_cos": "time of day", "dow": "day of week", "is_weekend": "weekend",
    "month": "time of year", "month_sin": "time of year", "month_cos": "time of year", "doy": "time of year",
    "season": "season", "diwali_window": "Diwali period", "city_code": "city", "lat": "city location", "lon": "city location",
    "pm25_pm10_ratio": "fine-to-coarse particle ratio", "no2_co_ratio": "NO2/CO ratio",
}


def label(feat: str) -> str:
    if feat in LABELS:
        return LABELS[feat]
    m = re.match(r"pm25_lag_(\d+)$", feat)
    if m:
        h = int(m.group(1))
        return f"PM2.5 {h} h ago" if h < 24 else f"PM2.5 {h // 24} day{'s' if h > 24 else ''} ago"
    m = re.match(r"pm25_(mean|std|min|max)_(\d+)$", feat)
    if m:
        w = int(m.group(2)); w = f"{w} h" if w < 24 else f"{w // 24} day{'s' if w > 24 else ''}"
        return {"mean": "average", "std": "variability of", "min": "lowest", "max": "peak"}[m.group(1)] + f" PM2.5 over the last {w}"
    if feat.startswith("pm25_diff") or feat.startswith("pm25_slope"):
        return "recent PM2.5 trend"
    if feat == "pm25_ratio_24" or feat == "pm25_lag_24_to_1_ratio":
        return "PM2.5 relative to its daily average"
    m = re.match(r"(pm10|no2|co)_mean_24$", feat)
    if m:
        return {"pm10": "PM10", "no2": "NO2", "co": "carbon monoxide"}[m.group(1)] + " over the last day"
    return feat.replace("_", " ")


def sentence(feat: str, shap_val: float, value: float) -> str:
    verb = "raised" if shap_val > 0 else "lowered"
    lab = label(feat)
    return f"{lab[0].upper() + lab[1:]} {verb} the predicted PM2.5 by {abs(shap_val):.0f} µg/m³"


def load_explainer():
    model = joblib.load(EXPLAIN_PATH)
    return model, shap.TreeExplainer(model)


def explain_row(model, explainer, row: pd.DataFrame, top: int = 5) -> list[dict]:
    cols = list(model.feature_name_)
    sv = explainer.shap_values(row[cols])[0]
    # merge features sharing the same human label (e.g. wind sin/cos)
    merged: dict[str, dict] = {}
    for f, s, v in zip(cols, sv, row[cols].iloc[0].values):
        key = label(f)
        if key not in merged:
            merged[key] = dict(feature=f, label=key, shap=0.0, value=float(v))
        merged[key]["shap"] += float(s)
    items = sorted(merged.values(), key=lambda d: -abs(d["shap"]))[:top]
    for d in items:
        d["text"] = sentence(d["feature"], d["shap"], d["value"])
        d["direction"] = "up" if d["shap"] > 0 else "down"
    return items


def main() -> None:
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    df = pd.read_parquet(PROC_DIR / "features.parquet")
    cols = feature_columns(df)
    meta = json.loads((MODEL_DIR / "metadata.json").read_text())
    model = make_lgbm(meta["lgbm_params"]).fit(df[cols], df[f"pm25_t+{H}h"])
    joblib.dump(model, EXPLAIN_PATH)
    sample = df.sample(5000, random_state=42)
    explainer = shap.TreeExplainer(model)
    sv = explainer.shap_values(sample[cols])
    imp = pd.Series(np.abs(sv).mean(0), index=cols).sort_values(ascending=False)
    merged = imp.groupby(imp.index.map(label)).sum().sort_values(ascending=False)
    out = [{"feature": k, "importance": round(float(v), 3)} for k, v in merged.head(20).items()]
    (MODEL_DIR / "importance.json").write_text(json.dumps(out, indent=2))
    shap.summary_plot(sv, sample[cols], show=False, max_display=15)
    plt.tight_layout(); plt.savefig(FIG_DIR / "shap_beeswarm_24h.png", dpi=130); plt.close()
    shap.summary_plot(sv, sample[cols], plot_type="bar", show=False, max_display=15)
    plt.tight_layout(); plt.savefig(FIG_DIR / "shap_bar_24h.png", dpi=130); plt.close()
    ex = explain_row(model, explainer, sample.iloc[[0]])
    assert len(ex) == 5
    print(json.dumps(ex, indent=2)[:900])


if __name__ == "__main__":
    main()

