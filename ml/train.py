"""Train / tune / compare models per horizon, save best models + metadata.

Splits (time-based only):
  Test A  = most recent 90 days            (train: everything before, minus a 72 h gap)
  Test B  = winter holdout Nov 2025-Feb 2026 (train: everything before Nov 2025, minus gap)
Final production models are refit on all labelled data.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime

import joblib
import numpy as np
import optuna
import pandas as pd
from sklearn.metrics import (average_precision_score, f1_score, mean_absolute_error,
                             mean_squared_error, precision_score, r2_score, recall_score,
                             roc_auc_score)

from .config import (ALERT_THRESHOLD, HEADLINE_HORIZONS, HORIZONS, MODEL_DIR, PROC_DIR, REPORT_DIR, SEED)
from .features import feature_columns
from .models import (StackedRegressor, make_classifier, make_lgbm, make_quantile, make_rf, make_ridge,
                     make_xgb)

optuna.logging.set_verbosity(optuna.logging.WARNING)
GAP = pd.Timedelta(hours=max(HORIZONS))
WINTER_START, WINTER_END = pd.Timestamp("2025-11-01"), pd.Timestamp("2026-03-01")


def rmse(y, p):
    return float(np.sqrt(mean_squared_error(y, p)))


def metrics(y, p):
    return dict(MAE=mean_absolute_error(y, p), RMSE=rmse(y, p), R2=r2_score(y, p))


def get_splits(df: pd.DataFrame):
    t = df["timestamp"]
    a_start = t.max() - pd.Timedelta(days=90) + pd.Timedelta(hours=1)
    splits = {
        "A_recent90d": (t < a_start - GAP, t >= a_start),
        "B_winter": (t < WINTER_START - GAP, (t >= WINTER_START) & (t < WINTER_END)),
    }
    return splits


def baselines(df: pd.DataFrame, h: int) -> dict[str, np.ndarray]:
    k = 24 * int(np.ceil(h / 24)) - h
    seasonal = df.groupby("city", sort=False)["pm2_5"].shift(k) if k else df["pm2_5"]
    return {"Persistence": df["pm2_5"].values,
            "SeasonalNaive": seasonal.fillna(df["pm2_5"]).values,
            "Mean7d": df["pm25_mean_168"].fillna(df["pm2_5"]).values}


# ----------------------------------------------------------------- tuning
def tune(df: pd.DataFrame, cols: list[str], target: str, n_trials: int) -> tuple[dict, dict]:
    """Optuna on expanding-window time-series CV (3 folds, 72 h gap), log1p target, h=24."""
    d = df.iloc[::3]  # subsample for speed (autocorrelated rows)
    t = d["timestamp"]
    q = t.quantile([0.55, 0.7, 0.85, 1.0]).values
    folds = [((t < q[i] - GAP), (t >= q[i]) & (t <= q[i + 1])) for i in range(3)]
    X, y = d[cols], np.log1p(d[target].values)

    def cv(make):
        def obj(trial):
            return make(trial)
        return obj

    def score(model):
        s = []
        for tr, va in folds:
            model.fit(X[tr], y[tr])
            s.append(rmse(np.expm1(y[va]), np.expm1(model.predict(X[va]))))
        return float(np.mean(s))

    def lgb_obj(tr):
        p = dict(num_leaves=tr.suggest_int("num_leaves", 15, 127), learning_rate=tr.suggest_float("learning_rate", 0.02, 0.1, log=True),
                 n_estimators=tr.suggest_int("n_estimators", 200, 800), min_child_samples=tr.suggest_int("min_child_samples", 10, 120),
                 colsample_bytree=tr.suggest_float("colsample_bytree", 0.4, 1.0), subsample=tr.suggest_float("subsample", 0.5, 1.0),
                 reg_lambda=tr.suggest_float("reg_lambda", 1e-2, 30, log=True))
        return score(make_lgbm(p))

    def xgb_obj(tr):
        p = dict(max_depth=tr.suggest_int("max_depth", 3, 10), learning_rate=tr.suggest_float("learning_rate", 0.02, 0.15, log=True),
                 n_estimators=tr.suggest_int("n_estimators", 200, 700), min_child_weight=tr.suggest_int("min_child_weight", 1, 30),
                 colsample_bytree=tr.suggest_float("colsample_bytree", 0.4, 1.0), subsample=tr.suggest_float("subsample", 0.5, 1.0),
                 reg_lambda=tr.suggest_float("reg_lambda", 1e-2, 30, log=True))
        return score(make_xgb(p))

    out = []
    for obj in (lgb_obj, xgb_obj):
        st = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=SEED))
        st.optimize(obj, n_trials=n_trials)
        print(f"  tuned {obj.__name__}: cv-RMSE {st.best_value:.2f}")
        out.append(st.best_params)
    return out[0], out[1]


# ----------------------------------------------------------------- main
def fit_eval(df, cols, h, splits, lgb_p, xgb_p, full: bool):
    """Return rows for the comparison table and test predictions."""
    target = f"pm25_t+{h}h"
    rows, preds = [], []
    for sname, (trm, tem) in splits.items():
        tr, te = df[trm], df[tem]
        if len(tr) < 10000 or len(te) == 0:
            continue
        y_tr, y_te = tr[target].values, te[target].values
        cand = {k: v for k, v in baselines(te, h).items()}
        models = {"LightGBM": (make_lgbm(lgb_p), False), "LightGBM_log": (make_lgbm(lgb_p), True)}
        if full:
            models.update({"Ridge": (make_ridge(), False), "RandomForest": (make_rf(), False),
                           "XGBoost": (make_xgb(xgb_p), False), "XGBoost_log": (make_xgb(xgb_p), True)})
        for name, (m, use_log) in models.items():
            t0 = time.time()
            m.fit(tr[cols], np.log1p(y_tr) if use_log else y_tr)
            p = m.predict(te[cols]); p = np.expm1(p) if use_log else p
            cand[name] = np.clip(p, 0, None)
            print(f"    {sname} h={h} {name}: RMSE {rmse(y_te, cand[name]):.2f} ({time.time()-t0:.0f}s)")
        if full:
            st = StackedRegressor(lgb_p, xgb_p).fit(tr[cols], np.log1p(y_tr), tr["timestamp"])
            cand["Stacking"] = np.clip(np.expm1(st.predict(te[cols])), 0, None)
            print(f"    {sname} h={h} Stacking: RMSE {rmse(y_te, cand['Stacking']):.2f}, weights {np.round(st.weights_, 2)}")
        base_rmse = rmse(y_te, cand["Persistence"])
        for name, p in cand.items():
            r = metrics(y_te, p)
            r.update(model=name, horizon=h, test=sname, n_test=len(te),
                     skill_vs_persistence=1 - r["RMSE"] / base_rmse)
            rows.append(r)
            pf = te[["city", "timestamp"]].copy(); pf["model"] = name; pf["horizon"] = h; pf["test"] = sname
            pf["y_true"] = y_te; pf["y_pred"] = p
            preds.append(pf)
    return rows, preds


def main(n_trials: int = 25) -> None:
    t_start = time.time()
    df = pd.read_parquet(PROC_DIR / "features.parquet").sort_values("timestamp").reset_index(drop=True)
    cols = feature_columns(df)
    print(f"data {df.shape}, {len(cols)} features, {df.timestamp.min()} -> {df.timestamp.max()}")
    splits = get_splits(df)

    # --- tune on the Test-A training window only (h = 24)
    trA = df[splits["A_recent90d"][0]]
    print("tuning (h=24, train window of Test A) ...")
    cache = REPORT_DIR / "tuned_params.json"
    if cache.exists():
        lgb_p, xgb_p = json.loads(cache.read_text()).values()
        print("  using cached tuned params", cache.name)
    else:
        lgb_p, xgb_p = tune(trA, cols, "pm25_t+24h", n_trials)
        cache.write_text(json.dumps({"lgbm": lgb_p, "xgb": xgb_p}, indent=2))

    rows, preds = [], []
    for h in HORIZONS:
        print(f"horizon {h}h  (full comparison: {h in HEADLINE_HORIZONS})")
        r, p = fit_eval(df, cols, h, splits, lgb_p, xgb_p, full=h in HEADLINE_HORIZONS)
        rows += r; preds += p
    comp = pd.DataFrame(rows)[["model", "horizon", "test", "n_test", "MAE", "RMSE", "R2", "skill_vs_persistence"]]
    comp.to_csv(REPORT_DIR / "model_comparison.csv", index=False)
    pd.concat(preds).to_parquet(REPORT_DIR / "test_predictions.parquet")

    # --- pick the best non-baseline model per horizon (mean RMSE over both test sets)
    ml = comp[~comp.model.isin(["Persistence", "SeasonalNaive", "Mean7d"])]
    best = ml.groupby(["horizon", "model"])["RMSE"].mean().reset_index().sort_values("RMSE").groupby("horizon").first()
    print("best per horizon:\n", best)

    # --- alert classifier: threshold tuned on the last 60 days of the Test-A train window
    print("alert classifier ...")
    trm, tem = splits["A_recent90d"]
    tr = df[trm]; cut = tr.timestamp.max() - pd.Timedelta(days=60)
    core, val = tr[tr.timestamp < cut - GAP], tr[tr.timestamp >= cut]
    clf = make_classifier(lgb_p).fit(core[cols], core["alert_24h"])
    pv = clf.predict_proba(val[cols])[:, 1]
    best_thr, best_prec = 0.5, -1
    for thr in np.arange(0.05, 0.95, 0.01):
        yhat = pv >= thr
        if recall_score(val["alert_24h"], yhat) >= 0.80:
            pr = precision_score(val["alert_24h"], yhat, zero_division=0)
            if pr > best_prec: best_prec, best_thr = pr, float(thr)
    alert_rows = []
    for sname, (trm2, tem2) in splits.items():
        te = df[tem2]
        trs = df[trm2]
        c2 = make_classifier(lgb_p).fit(trs[cols], trs["alert_24h"])
        pp = c2.predict_proba(te[cols])[:, 1]; yh = pp >= best_thr; yt = te["alert_24h"].values
        alert_rows.append(dict(test=sname, threshold=best_thr, precision=precision_score(yt, yh, zero_division=0),
                               recall=recall_score(yt, yh), f1=f1_score(yt, yh), pr_auc=average_precision_score(yt, pp),
                               roc_auc=roc_auc_score(yt, pp), base_rate=float(yt.mean())))
        pf = te[["city", "timestamp"]].copy(); pf["test"] = sname; pf["y_true"] = yt; pf["proba"] = pp
        pf.to_parquet(REPORT_DIR / f"alert_predictions_{sname}.parquet")
    pd.DataFrame(alert_rows).to_csv(REPORT_DIR / "alert_metrics.csv", index=False)
    print(pd.DataFrame(alert_rows).round(3).to_string())

    # --- quantile coverage on Test A
    print("quantile intervals ...")
    cov = {}
    for h in HEADLINE_HORIZONS:
        trA_, teA = df[splits["A_recent90d"][0]], df[splits["A_recent90d"][1]]
        lo = make_quantile(0.1, lgb_p).fit(trA_[cols], trA_[f"pm25_t+{h}h"]).predict(teA[cols])
        hi = make_quantile(0.9, lgb_p).fit(trA_[cols], trA_[f"pm25_t+{h}h"]).predict(teA[cols])
        y = teA[f"pm25_t+{h}h"].values
        cov[h] = float(np.mean((y >= lo) & (y <= hi)))
    print("80% interval coverage (Test A):", cov)

    # --- production refit on all labelled data
    print("refitting production models on all data ...")
    meta = {"trained_at": datetime.now().isoformat(timespec="seconds"), "features": cols,
            "latest_data_timestamp": str(df.timestamp.max()), "n_train_rows": len(df),
            "lgbm_params": lgb_p, "xgb_params": xgb_p, "alert_threshold": best_thr,
            "interval_coverage_testA": cov, "horizons": {}}
    for h in HORIZONS:
        name = best.loc[h, "model"] if h in best.index else "LightGBM_log"
        # extra horizons only evaluated with LightGBM variants
        use_log = name.endswith("_log") or name == "Stacking"
        target = f"pm25_t+{h}h"; y = df[target].values
        if name.startswith("Stacking"):
            model = StackedRegressor(lgb_p, xgb_p).fit(df[cols], np.log1p(y), df["timestamp"])
        elif name.startswith("XGBoost"):
            model = make_xgb(xgb_p).fit(df[cols], np.log1p(y) if use_log else y)
        elif name == "RandomForest":
            model = make_rf().fit(df[cols], y)
        elif name == "Ridge":
            model = make_ridge().fit(df[cols], y)
        else:
            model = make_lgbm(lgb_p).fit(df[cols], np.log1p(y) if use_log else y)
        q10 = make_quantile(0.1, lgb_p).fit(df[cols], y)
        q90 = make_quantile(0.9, lgb_p).fit(df[cols], y)
        joblib.dump({"model": model, "log": use_log, "q10": q10, "q90": q90, "name": name}, MODEL_DIR / f"reg_{h}h.joblib")
        m = comp[(comp.model == name) & (comp.horizon == h)]
        meta["horizons"][str(h)] = {"model": name, "log_target": use_log,
                                    "metrics": m.set_index("test")[["MAE", "RMSE", "R2", "skill_vs_persistence"]].round(4).to_dict("index")}
        print(f"  saved {h}h -> {name}")
    clf = make_classifier(lgb_p).fit(df[cols], df["alert_24h"])
    joblib.dump(clf, MODEL_DIR / "alert_clf.joblib")
    meta["alert_metrics"] = pd.DataFrame(alert_rows).round(4).to_dict("records")
    (MODEL_DIR / "metadata.json").write_text(json.dumps(meta, indent=2))
    print(f"done in {(time.time()-t_start)/60:.1f} min")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 25)

