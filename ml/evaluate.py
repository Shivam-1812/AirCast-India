"""Evaluation figures and tables from reports/test_predictions.parquet."""
from __future__ import annotations

import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.metrics import confusion_matrix, precision_recall_curve

from .config import FIG_DIR, MODEL_DIR, NAQI, REPORT_DIR, naqi_category

sns.set_theme(style="whitegrid", context="notebook")
CATS = [n for _, n, _ in NAQI]
BASE = ["Persistence", "SeasonalNaive", "Mean7d"]


def _cat(a):
    return np.array([CATS.index(naqi_category(v)) for v in a])


def main() -> None:
    comp = pd.read_csv(REPORT_DIR / "model_comparison.csv")
    pred = pd.read_parquet(REPORT_DIR / "test_predictions.parquet")
    meta = json.loads((MODEL_DIR / "metadata.json").read_text())
    chosen = {int(h): v["model"] for h, v in meta["horizons"].items()}
    out = []

    # 1. model comparison heatmap (RMSE) on Test A and B
    for t in comp.test.unique():
        piv = comp[comp.test == t].pivot_table(index="model", columns="horizon", values="RMSE")
        plt.figure(figsize=(7, 5)); sns.heatmap(piv, annot=True, fmt=".1f", cmap="viridis_r")
        plt.title(f"RMSE (ug/m3) by model and horizon, {t}"); plt.tight_layout()
        plt.savefig(FIG_DIR / f"eval_rmse_heatmap_{t}.png", dpi=130); plt.close()

    # 2. error vs horizon, chosen model vs persistence
    plt.figure(figsize=(7, 4))
    for t, ls in zip(["A_recent90d", "B_winter"], ["-", "--"]):
        m = comp[(comp.test == t)]
        mm = m[[mo == chosen.get(h) for mo, h in zip(m.model, m.horizon)]].sort_values("horizon")
        pp = m[m.model == "Persistence"].sort_values("horizon")
        plt.plot(mm.horizon, mm.RMSE, ls, marker="o", label=f"best model, {t}")
        plt.plot(pp.horizon, pp.RMSE, ls, marker="x", color="gray", label=f"persistence, {t}")
    plt.xlabel("horizon (h)"); plt.ylabel("RMSE (ug/m3)"); plt.title("Error grows with horizon"); plt.legend(fontsize=8)
    plt.tight_layout(); plt.savefig(FIG_DIR / "eval_error_vs_horizon.png", dpi=130); plt.close()

    # per-horizon chosen predictions
    sel = pred[[chosen.get(h) == m for h, m in zip(pred.horizon, pred.model)]]
    for h in (24, 72):
        for t in ("A_recent90d", "B_winter"):
            s = sel[(sel.horizon == h) & (sel.test == t)]
            if s.empty:
                continue
            # 3. actual vs predicted, two cities
            fig, axs = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
            for ax, city in zip(axs, ["Delhi", "Pune"]):
                c = s[s.city == city].sort_values("timestamp")
                ax.plot(c.timestamp, c.y_true, label="actual", lw=1); ax.plot(c.timestamp, c.y_pred, label="predicted", lw=1)
                ax.set_title(f"{city} - PM2.5 {h} h ahead ({t})"); ax.set_ylabel("ug/m3"); ax.legend()
            plt.tight_layout(); plt.savefig(FIG_DIR / f"eval_actual_vs_pred_{h}h_{t}.png", dpi=130); plt.close()
            # 4. residual histogram
            plt.figure(figsize=(6, 4)); sns.histplot(s.y_pred - s.y_true, bins=60, kde=True)
            plt.title(f"Residuals, {h} h ({t})"); plt.xlabel("pred - actual (ug/m3)"); plt.tight_layout()
            plt.savefig(FIG_DIR / f"eval_residuals_{h}h_{t}.png", dpi=130); plt.close()

    # 5. per-city bar + by season + category accuracy (24 h)
    rows = []
    for t in ("A_recent90d", "B_winter"):
        s = sel[(sel.horizon == 24) & (sel.test == t)].copy()
        if s.empty:
            continue
        base = pred[(pred.horizon == 24) & (pred.test == t) & (pred.model == "Persistence")]
        s["se"] = (s.y_pred - s.y_true) ** 2
        base = base.assign(se=(base.y_pred - base.y_true) ** 2)
        bc = pd.DataFrame({"model": np.sqrt(s.groupby("city").se.mean()), "persistence": np.sqrt(base.groupby("city").se.mean())})
        bc.plot.bar(figsize=(8, 4), title=f"RMSE by city, 24 h ({t})"); plt.ylabel("ug/m3"); plt.tight_layout()
        plt.savefig(FIG_DIR / f"eval_by_city_{t}.png", dpi=130); plt.close()
        bc.assign(test=t).reset_index().to_csv(REPORT_DIR / f"by_city_{t}.csv", index=False)
        ct, cp = _cat(s.y_true), _cat(s.y_pred)
        rows.append(dict(test=t, horizon=24, exact_category=float((ct == cp).mean()), within_one=float((abs(ct - cp) <= 1).mean())))
        cm = confusion_matrix(ct, cp, labels=range(len(CATS)))
        plt.figure(figsize=(6, 5)); sns.heatmap(cm, annot=True, fmt="d", xticklabels=CATS, yticklabels=CATS, cmap="Blues")
        plt.xlabel("predicted"); plt.ylabel("actual"); plt.title(f"NAQI category confusion, 24 h ({t})"); plt.tight_layout()
        plt.savefig(FIG_DIR / f"eval_category_confusion_{t}.png", dpi=130); plt.close()
        s["month"] = s.timestamp.dt.month
        out.append(s.groupby("month").se.mean().pipe(np.sqrt).rename(t))
    pd.DataFrame(rows).to_csv(REPORT_DIR / "category_accuracy.csv", index=False)

    # 6. alert PR curve
    plt.figure(figsize=(6, 4))
    for t in ("A_recent90d", "B_winter"):
        p = REPORT_DIR / f"alert_predictions_{t}.parquet"
        if p.exists():
            a = pd.read_parquet(p)
            if a.y_true.sum() > 0:
                pr, rc, _ = precision_recall_curve(a.y_true, a.proba); plt.plot(rc, pr, label=t)
    plt.xlabel("recall"); plt.ylabel("precision"); plt.title("Alert classifier PR curve"); plt.legend(); plt.tight_layout()
    plt.savefig(FIG_DIR / "eval_alert_pr_curve.png", dpi=130); plt.close()

    # summary
    summ = comp[[chosen.get(h) == m for h, m in zip(comp.horizon, comp.model)]]
    base = comp[comp.model == "Persistence"][["horizon", "test", "RMSE"]].rename(columns={"RMSE": "persistence_RMSE"})
    summ = summ.merge(base, on=["horizon", "test"]).sort_values(["test", "horizon"])
    summ.to_csv(REPORT_DIR / "summary_best_models.csv", index=False)
    print(summ.round(3).to_string(index=False))
    print(pd.DataFrame(rows).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
