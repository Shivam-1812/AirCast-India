"""Live inference helper used by the API."""
from __future__ import annotations

import json

import joblib
import numpy as np
import pandas as pd

from .config import HORIZONS, MODEL_DIR, naqi_category
from .features import build_features

TAIL_HOURS = 400  # enough history for the 168 h lag/rolling features


class Predictor:
    def __init__(self):
        self.meta = json.loads((MODEL_DIR / "metadata.json").read_text())
        self.cols = self.meta["features"]
        self.models = {h: joblib.load(MODEL_DIR / f"reg_{h}h.joblib") for h in HORIZONS}
        self.clf = joblib.load(MODEL_DIR / "alert_clf.joblib")
        self.thr = self.meta["alert_threshold"]

    def latest_features(self, clean: pd.DataFrame) -> pd.DataFrame:
        """Last feature row per city (no targets needed)."""
        tail = (clean.sort_values(["city", "timestamp"]).groupby("city", sort=False).tail(TAIL_HOURS))
        f = build_features(tail, with_targets=False)
        return f.groupby("city", sort=False).tail(1).reset_index(drop=True)

    def _pred(self, h: int, X: pd.DataFrame) -> np.ndarray:
        m = self.models[h]
        p = m["model"].predict(X)
        return np.clip(np.expm1(p) if m["log"] else p, 0, None)

    def forecast(self, feat_row: pd.DataFrame) -> dict:
        """feat_row: single-row frame. Returns hourly 0..72 h arrays (index 0 = now)."""
        X = feat_row[self.cols]
        now = float(feat_row["pm2_5"].iloc[0])
        hs = [0] + HORIZONS
        mid, lo, hi = [now], [now], [now]
        for h in HORIZONS:
            m = self.models[h]
            p = float(self._pred(h, X)[0])
            mid.append(p)
            lo.append(max(0.0, float(m["q10"].predict(X)[0])))
            hi.append(float(m["q90"].predict(X)[0]))
        hours = np.arange(0, 73)
        pm = np.interp(hours, hs, mid)
        lower = np.minimum(np.interp(hours, hs, lo), pm)
        upper = np.maximum(np.interp(hours, hs, hi), pm)
        prob = float(self.clf.predict_proba(X)[0, 1])
        return {"hours": hours, "pm25": pm, "lower": lower, "upper": upper,
                "alert_score": prob, "alert": prob >= self.thr,
                "categories": [naqi_category(v) for v in pm]}
