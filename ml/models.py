"""Model factories + a leak-free time-series stacking ensemble."""
from __future__ import annotations

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier, LGBMRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

from .config import SEED

LGBM_DEFAULT = dict(n_estimators=600, learning_rate=0.04, num_leaves=63, min_child_samples=40,
                    subsample=0.8, subsample_freq=1, colsample_bytree=0.7, reg_lambda=1.0)
XGB_DEFAULT = dict(n_estimators=500, learning_rate=0.05, max_depth=7, min_child_weight=5,
                   subsample=0.8, colsample_bytree=0.7, reg_lambda=1.0)


def make_ridge():
    return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), Ridge(alpha=10.0, random_state=SEED))


def make_rf(n_estimators=150):
    return make_pipeline(SimpleImputer(strategy="median"),
                         RandomForestRegressor(n_estimators=n_estimators, max_depth=16, min_samples_leaf=8,
                                               max_features=0.4, max_samples=0.3, n_jobs=-1, random_state=SEED))


def make_lgbm(params=None, **kw):
    p = {**LGBM_DEFAULT, **(params or {}), **kw}
    return LGBMRegressor(random_state=SEED, n_jobs=-1, verbose=-1, **p)


def make_xgb(params=None, **kw):
    p = {**XGB_DEFAULT, **(params or {}), **kw}
    return XGBRegressor(random_state=SEED, n_jobs=-1, tree_method="hist", **p)


def make_quantile(alpha: float, params=None):
    return make_lgbm(params, objective="quantile", alpha=alpha)


def make_classifier(params=None):
    p = {**LGBM_DEFAULT, **(params or {})}
    p["n_estimators"] = 400
    return LGBMClassifier(random_state=SEED, n_jobs=-1, verbose=-1, class_weight="balanced", **p)


class StackedRegressor:
    """RF + XGBoost + LightGBM base learners, Ridge meta-learner.

    Meta-learner is fitted on out-of-fold predictions from expanding-window
    time-series folds (with a gap) so it never sees in-sample base predictions.
    Rows must be sorted by time. Base learners are finally refit on all rows.
    """

    def __init__(self, lgbm_params=None, xgb_params=None, n_folds=3, gap=72, rf_trees=120):
        self.lgbm_params, self.xgb_params = lgbm_params, xgb_params
        self.n_folds, self.gap, self.rf_trees = n_folds, gap, rf_trees

    def _bases(self):
        return [make_rf(self.rf_trees), make_xgb(self.xgb_params), make_lgbm(self.lgbm_params)]

    def fit(self, X: pd.DataFrame, y: np.ndarray, times: pd.Series):
        order = np.argsort(times.values, kind="stable")
        X, y, times = X.iloc[order], np.asarray(y)[order], times.iloc[order]
        uniq = np.sort(times.unique())
        cuts = [uniq[min(int(len(uniq) * (0.4 + 0.6 * i / self.n_folds)), len(uniq) - 1)] for i in range(self.n_folds)]
        cuts.append(uniq[-1] + np.timedelta64(1, "h"))
        gap = np.timedelta64(self.gap, "h")
        oof_idx, oof_pred = [], []
        for i in range(self.n_folds):
            tr = (times.values < cuts[i] - gap)
            va = (times.values >= cuts[i]) & (times.values < cuts[i + 1] if i < self.n_folds - 1 else True)
            preds = [m.fit(X[tr], y[tr]).predict(X[va]) for m in self._bases()]
            oof_idx.append(np.where(va)[0]); oof_pred.append(np.column_stack(preds))
        P = np.vstack(oof_pred); yy = y[np.concatenate(oof_idx)]
        self.meta_ = Ridge(alpha=1.0, positive=True, random_state=SEED).fit(P, yy)
        self.bases_ = [m.fit(X, y) for m in self._bases()]
        self.weights_ = self.meta_.coef_.tolist()
        return self

    def predict(self, X):
        P = np.column_stack([m.predict(X) for m in self.bases_])
        return self.meta_.predict(P)

