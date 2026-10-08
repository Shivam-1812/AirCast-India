# AirCast India

Live PM2.5 forecasting for 10 Indian cities: ensemble ML (LightGBM / XGBoost / Random Forest / Ridge / stacking) on Open-Meteo CAMS + ERA5 data, served by FastAPI, visualised in a React dashboard with a 3D globe, a 3D particle "smog" scene, charts and SHAP explanations.

See [reports/final_report.md](reports/final_report.md) for method and results, and [docs/AirCast_India_Project_Plan.md](docs/AirCast_India_Project_Plan.md) for the original plan.

## Results (RMSE µg/m³)
| Horizon | Test A (last 90 d) model / persistence | Test B (winter 2025-26) model / persistence |
|---|---|---|
| 6 h | 9.7 / 12.9 | 15.7 / 31.0 |
| 24 h | 12.7 / 13.7 | 21.9 / 24.1 |
| 48 h | 15.7 / 18.0 | 25.8 / 30.6 |
| 72 h | 16.9 / 20.2 | 27.3 / 34.3 |

Modest gains at 24 h, larger at 6 h and in winter. Data is modelled (CAMS), not station data. Full table: `reports/model_comparison.csv`.

## Run
```powershell
python -m venv .venv; .\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python -m ml.ingest      # downloads / incrementally updates data to today (~15 min first time)
.\.venv\Scripts\python -m ml.clean
.\.venv\Scripts\python -m ml.features
.\.venv\Scripts\python -m ml.train       # ~80 min on 8 cores (tuning + all models)
.\.venv\Scripts\python -m ml.explain     # SHAP explainer + importance
.\.venv\Scripts\python -m ml.evaluate    # figures
.\.venv\Scripts\uvicorn backend.main:app --port 8000
cd frontend; npm install; npm run dev    # http://localhost:5173
```
`run_all.ps1` / `run_all.sh` chain these. Tests: `pytest ml backend` and `cd frontend; npm test`.

## Layout
`ml/` pipeline (ingest, clean, features, train, evaluate, explain, predict) · `backend/` FastAPI (`/docs` lists all endpoints; refreshes every 3 h) · `frontend/` Vite + React + TypeScript + Tailwind v4, Magic UI components, three.js · `models/` saved models + `metadata.json` · `reports/` metrics and figures · `notebooks/` EDA and modelling.

## Notes / deviations from the plan
- History starts Aug 2022 (CAMS API returns no PM2.5 earlier).
- Hourly forecast curve: models for 7 horizons (6, 12, 24, 36, 48, 60, 72 h), linearly interpolated.
- Stacking was evaluated but did not beat single boosted models.
- Alert "probability" is an uncalibrated score.
- Map tiles are from OpenStreetMap; data: Open-Meteo, Copernicus CAMS, ERA5 (CC BY 4.0). Educational project, not medical advice.
