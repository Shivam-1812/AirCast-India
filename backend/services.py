"""Data refresh, caching and prediction for the API."""
from __future__ import annotations

import json
import logging
import threading
from datetime import datetime

import numpy as np
import pandas as pd

from ml import clean as ml_clean
from ml import explain as ml_explain
from ml import ingest as ml_ingest
from ml.config import CITIES, MODEL_DIR, NAQI, PROC_DIR, REPORT_DIR, naqi_category
from ml.predict import Predictor

log = logging.getLogger("aircast")
COLORS = {name: color for _, name, color in NAQI}

ADVISORY = {
    "Good": ("Air quality is good. Enjoy outdoor activity.", {
        "general": "No precautions needed. Good day to open windows and air out your home.",
        "children": "Normal outdoor play and school sports are fine.",
        "asthma_elderly": "Normal activity. Keep your usual medication handy.",
        "exercise": "Great conditions for outdoor running, cycling and sport."}),
    "Satisfactory": ("Minor breathing discomfort is possible for very sensitive people.", {
        "general": "Most people can go about their day normally.",
        "children": "Outdoor play is fine.",
        "asthma_elderly": "Sensitive people may notice mild discomfort; carry reliever medication.",
        "exercise": "Fine for exercise; very sensitive people may prefer lighter effort."}),
    "Moderate": ("Breathing discomfort for people with lung or heart disease, children and older adults.", {
        "general": "Reduce prolonged or heavy outdoor exertion if you feel any symptoms.",
        "children": "Limit long, intense outdoor activity.",
        "asthma_elderly": "Reduce outdoor time; keep medication close.",
        "exercise": "Prefer shorter sessions or move indoors if you notice coughing."}),
    "Poor": ("Breathing discomfort on prolonged exposure for most people.", {
        "general": "Avoid long outdoor stays. A well-fitted N95/FFP2 mask helps outdoors.",
        "children": "Move strenuous play and sports indoors.",
        "asthma_elderly": "Stay indoors where possible and follow your doctor's action plan.",
        "exercise": "Shift workouts indoors or to the cleanest time window."}),
    "Very Poor": ("Respiratory illness on prolonged exposure; avoid outdoor exertion.", {
        "general": "Avoid outdoor exertion. Wear an N95/FFP2 mask if you must go out; use an air purifier indoors.",
        "children": "Keep children indoors; consider checking school advisories.",
        "asthma_elderly": "Stay indoors with windows closed and purifier on; seek care if symptoms worsen.",
        "exercise": "Skip outdoor exercise."}),
    "Severe": ("Serious health effects even for healthy people.", {
        "general": "Stay indoors, keep windows closed, run a purifier, and avoid all outdoor exertion.",
        "children": "Keep children indoors.",
        "asthma_elderly": "Remain indoors and contact a doctor early if you have symptoms.",
        "exercise": "No outdoor exercise."}),
}


class State:
    def __init__(self):
        self.lock = threading.RLock()
        self.pred = Predictor()
        self.explainer = None
        if ml_explain.EXPLAIN_PATH.exists():
            self.explainer = ml_explain.load_explainer()
        self.clean: pd.DataFrame = pd.DataFrame()
        self.feats: pd.DataFrame = pd.DataFrame()
        self.forecasts: dict[str, dict] = {}
        self.last_refresh: str | None = None
        self.perf = self._load_perf()
        self.importance = json.loads((MODEL_DIR / "importance.json").read_text()) if (MODEL_DIR / "importance.json").exists() else []
        self.load_data()

    def _load_perf(self) -> dict:
        out = {"metadata": {k: v for k, v in self.pred.meta.items() if k != "features"}, "table": [], "alert": []}
        p = REPORT_DIR / "model_comparison.csv"
        if p.exists():
            out["table"] = json.loads(pd.read_csv(p).round(4).to_json(orient="records"))
        a = REPORT_DIR / "alert_metrics.csv"
        if a.exists():
            out["alert"] = json.loads(pd.read_csv(a).round(4).to_json(orient="records"))
        return out

    def load_data(self) -> None:
        with self.lock:
            self.clean = pd.read_parquet(PROC_DIR / "clean.parquet")
            self.feats = self.pred.latest_features(self.clean)
            self.forecasts = {}
            for i in range(len(self.feats)):
                r = self.feats.iloc[[i]]
                self.forecasts[r["city"].iloc[0]] = self.pred.forecast(r)

    def refresh(self) -> None:
        """Incremental ingest -> clean -> features -> predictions."""
        try:
            ml_ingest.ingest()
            df = ml_clean.build_clean()
            df.to_parquet(PROC_DIR / "clean.parquet")
            self.load_data()
            self.last_refresh = datetime.now().isoformat(timespec="seconds")
            log.info("refresh ok")
        except Exception:  # keep serving the cached data
            log.exception("refresh failed")

    # ------------------------------------------------------------- helpers
    def latest_ts(self, city: str) -> pd.Timestamp:
        return pd.Timestamp(self.feats.loc[self.feats.city == city, "timestamp"].iloc[0])

    def city_row(self, city: str) -> pd.Series:
        return self.feats.loc[self.feats.city == city].iloc[0]

    def forecast_points(self, city: str) -> list[dict]:
        f, t0 = self.forecasts[city], self.latest_ts(city)
        return [dict(timestamp=(t0 + pd.Timedelta(hours=int(h))).isoformat(), hour_ahead=int(h),
                     pm25=round(float(p), 1), lower=round(float(lo), 1), upper=round(float(up), 1), category=c)
                for h, p, lo, up, c in zip(f["hours"], f["pm25"], f["lower"], f["upper"], f["categories"])]

    def overview(self) -> list[dict]:
        out = []
        for city, (lat, lon) in CITIES.items():
            row, f = self.city_row(city), self.forecasts[city]
            now = float(row["pm2_5"]); p24 = float(f["pm25"][24])
            d = p24 - now
            trend = "worse" if d > max(5, 0.1 * now) else "better" if d < -max(5, 0.1 * now) else "steady"
            out.append(dict(city=city, lat=lat, lon=lon, pm25=round(now, 1), category=naqi_category(now),
                            color=COLORS[naqi_category(now)], alert_24h=bool(f["alert"]),
                            alert_score=round(f["alert_score"], 3), pred_24h=round(p24, 1),
                            pred_category_24h=naqi_category(p24), trend=trend,
                            observed_at=self.latest_ts(city).isoformat()))
        return out

    def best_time(self, city: str) -> dict:
        pts = self.forecast_points(city)
        pm = np.array([p["pm25"] for p in pts])[1:49]
        ma = np.convolve(pm, np.ones(3) / 3, mode="valid")
        i, j = int(ma.argmin()), int(ma.argmax())
        t0 = self.latest_ts(city)
        s = t0 + pd.Timedelta(hours=i + 1)
        return dict(city=city, start=s.isoformat(), end=(s + pd.Timedelta(hours=3)).isoformat(),
                    mean_pm25=round(float(ma[i]), 1), category=naqi_category(float(ma[i])),
                    worst_start=(t0 + pd.Timedelta(hours=j + 1)).isoformat(), worst_mean_pm25=round(float(ma[j]), 1))

    def explain(self, city: str) -> dict:
        if self.explainer is None:
            raise RuntimeError("explainer not available")
        model, expl = self.explainer
        row = self.feats.loc[self.feats.city == city].infer_objects()
        factors = ml_explain.explain_row(model, expl, row)
        base = float(np.ravel(expl.expected_value)[0])
        return dict(city=city, horizon_hours=24, base_value=round(base, 1),
                    factors=[dict(label=f["label"], shap=round(f["shap"], 2), direction=f["direction"], text=f["text"]) for f in factors])


_state: State | None = None


def get_state() -> State:
    global _state
    if _state is None:
        _state = State()
    return _state
