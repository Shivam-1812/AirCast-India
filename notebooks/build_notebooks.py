"""Generate and execute the two notebooks:  python notebooks/build_notebooks.py"""
import sys
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parent.parent
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell

SETUP = """import sys; sys.path.insert(0, '..')
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd, matplotlib.pyplot as plt, seaborn as sns
from ml.config import FIG_DIR, PROC_DIR, REPORT_DIR, MODEL_DIR
sns.set_theme(style='whitegrid')
def save(name): plt.tight_layout(); plt.savefig(FIG_DIR / name, dpi=130); plt.show()
df = pd.read_parquet(PROC_DIR / 'clean.parquet')
df['month'] = df.timestamp.dt.month; df['hour'] = df.timestamp.dt.hour; df['year'] = df.timestamp.dt.year
df['season'] = df.month.map(lambda m: 'Winter' if m in (11,12,1,2) else 'Monsoon' if m in (6,7,8,9) else 'Other')
"""

eda = [
    md("# 01 - Exploratory data analysis\nHourly PM2.5, other pollutants and weather for 10 Indian cities (Open-Meteo / CAMS / ERA5)."),
    code(SETUP + "df.shape, df.timestamp.min(), df.timestamp.max()"),
    md("## 1. Missing values and gaps"),
    code("print(df.groupby('city').size().to_frame('rows').join(df.groupby('city').pm2_5.apply(lambda s: s.isna().sum()).rename('missing_pm25')))\n"
         "df[['pm2_5','pm10','nitrogen_dioxide','temperature_2m','wind_speed_10m']].describe().round(1)"),
    md("## 2. PM2.5 distribution (log scale)"),
    code("fig, ax = plt.subplots(figsize=(9,4))\nfor c, g in df.groupby('city'): sns.kdeplot(np.log10(g.pm2_5.clip(lower=0.5)), ax=ax, label=c)\n"
         "ax.set_xlabel('log10 PM2.5'); ax.legend(ncol=2, fontsize=8); ax.set_title('PM2.5 distribution by city'); save('eda_01_distribution.png')"),
    md("## 3. Monthly pattern per city"),
    code("m = df.pivot_table(index='month', columns='city', values='pm2_5'); plt.figure(figsize=(10,5)); sns.heatmap(m.T, cmap='rocket_r', annot=True, fmt='.0f')\n"
         "plt.title('Mean PM2.5 by month (ug/m3)'); save('eda_02_monthly_heatmap.png')"),
    md("## 4. Hour-of-day pattern and weekday vs weekend"),
    code("fig, ax = plt.subplots(1, 2, figsize=(12,4))\nfor c in ['Delhi','Pune','Bengaluru']:\n    ax[0].plot(df[df.city==c].groupby('hour').pm2_5.mean(), label=c)\n"
         "ax[0].set_title('Mean PM2.5 by hour of day'); ax[0].legend(); ax[0].set_xlabel('hour (IST)')\n"
         "wk = df.assign(weekend=df.timestamp.dt.dayofweek>=5).groupby(['city','weekend']).pm2_5.mean().unstack(); wk.plot.bar(ax=ax[1]); ax[1].set_title('Weekday vs weekend')\nsave('eda_03_hourly_weekend.png')"),
    md("## 5. Seasonality: monsoon vs winter"),
    code("s = df[df.season!='Other'].groupby(['city','season']).pm2_5.mean().unstack(); s['winter/monsoon'] = s.Winter/s.Monsoon\nprint(s.round(1))\n"
         "s[['Monsoon','Winter']].plot.bar(figsize=(9,4), title='Mean PM2.5: monsoon vs winter'); save('eda_04_season.png')"),
    md("## 6. Correlation with weather and other pollutants"),
    code("cols = ['pm2_5','pm10','nitrogen_dioxide','carbon_monoxide','ozone','wind_speed_10m','relative_humidity_2m','precipitation','temperature_2m','surface_pressure']\n"
         "plt.figure(figsize=(8,6)); sns.heatmap(df[cols].corr(), annot=True, fmt='.2f', cmap='coolwarm', center=0); plt.title('Correlation matrix'); save('eda_05_correlation.png')"),
    code("fig, ax = plt.subplots(1, 3, figsize=(14,4)); d = df.sample(30000, random_state=42)\n"
         "for a, c in zip(ax, ['wind_speed_10m','relative_humidity_2m','precipitation']): sns.scatterplot(data=d, x=c, y='pm2_5', s=4, alpha=.3, ax=a); a.set_yscale('log')\nsave('eda_06_weather_scatter.png')"),
    md("## 7. Year-over-year trend"),
    code("y = df[df.year.between(2023, 2025)].pivot_table(index='city', columns='year', values='pm2_5'); y.plot.bar(figsize=(9,4), title='Annual mean PM2.5 (full years)'); save('eda_07_yearly.png')"),
    md("## 8. Extreme-pollution events (top 1% hours)"),
    code("thr = df.pm2_5.quantile(.99); ex = df[df.pm2_5 >= thr]; print('99th percentile:', round(thr,1))\n"
         "ex.groupby('city').size().sort_values().plot.barh(figsize=(7,4), title='Hours in the national top 1%'); save('eda_08_extremes.png')\n"
         "ex.groupby('month').size().plot.bar(figsize=(7,3), title='Extreme hours by month'); save('eda_09_extreme_months.png')"),
    md("## Insights\nSee the generated figures and the bullet list written in `reports/final_report.md` (section Data)."),
]

model = [
    md("# 02 - Modelling and evaluation\nAll numbers come from `reports/model_comparison.csv`, produced by `python -m ml.train`."),
    code(SETUP + "comp = pd.read_csv(REPORT_DIR/'model_comparison.csv'); meta = pd.read_json(MODEL_DIR/'metadata.json', typ='series')\nlen(meta.features), meta.latest_data_timestamp"),
    md("## Feature groups and why they help\n| Group | Examples | Why |\n|---|---|---|\n| Lags | PM2.5 t-1 ... t-168 | Pollution is highly autocorrelated; the last day and week set the baseline |\n| Rolling stats | mean/std/min/max over 6-168 h | Smooth noise, capture regime and volatility |\n| Trend | diff 24 h, 6 h slope | Rising vs falling episodes |\n| Weather | wind, humidity, rain, pressure, stagnation | Dispersion and wet removal |\n| Calendar | hour, month, season, Diwali | Traffic cycles, winter inversion, fireworks |\n| City | lat, lon | Local climate/emission level |\n| Ratios | PM2.5/PM10, NO2/CO | Source mix (dust vs combustion) |"),
    md("## Model comparison"),
    code("for t in comp.test.unique():\n    print(t); display(comp[comp.test==t].pivot_table(index='model', columns='horizon', values='RMSE').round(2))"),
    code("summ = pd.read_csv(REPORT_DIR/'summary_best_models.csv'); display(summ.round(3))"),
    md("## Figures"),
    code("from IPython.display import Image, display\nfor f in sorted(FIG_DIR.glob('eval_*.png')): print(f.name); display(Image(str(f), width=700))"),
    md("## Alert classifier"),
    code("display(pd.read_csv(REPORT_DIR/'alert_metrics.csv').round(3)); display(pd.read_csv(REPORT_DIR/'category_accuracy.csv').round(3))"),
    md("## SHAP"),
    code("for n in ['shap_bar_24h.png','shap_beeswarm_24h.png']: display(Image(str(FIG_DIR/n), width=700))"),
    md("## Conclusions\nSee `reports/final_report.md` for written conclusions with the measured numbers."),
]


def build(name, cells):
    nb = nbf.v4.new_notebook(cells=cells, metadata={"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}})
    p = ROOT / "notebooks" / name
    nbf.write(nb, p)
    return p


if __name__ == "__main__":
    which = sys.argv[1:] or ["eda", "model"]
    import subprocess
    for w in which:
        p = build("01_eda.ipynb" if w == "eda" else "02_modeling.ipynb", eda if w == "eda" else model)
        subprocess.run([sys.executable, "-m", "jupyter", "nbconvert", "--to", "notebook", "--execute", "--inplace",
                        "--ExecutePreprocessor.timeout=900", str(p)], check=True, cwd=ROOT / "notebooks")
        print("executed", p.name)
