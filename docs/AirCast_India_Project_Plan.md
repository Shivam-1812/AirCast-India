# AirCast India: Live Air-Quality Forecasting with Ensemble ML (FastAPI + React)

**Category:** Supervised Learning (time-series regression + binary alert classification) with ensemble methods
**Data freshness:** pulled live from public APIs up to today (2026), so the model is trained and served on current data, not a frozen old dump
**Stack:** Python (pandas, scikit-learn, LightGBM, XGBoost, SHAP, FastAPI) for ML + backend, React.js (Vite) for the frontend

---

## 0. How to use this file with Claude Code

1. Create an empty folder `aircast-india/`, open a terminal there, and run `claude`.
2. Save this file as `PLAN.md` in that folder.
3. Paste this prompt:

> Read PLAN.md fully. Implement it phase by phase (Phase 0 to Phase 12). After each phase, run that phase's "Acceptance checks" and fix failures before moving on. Use random seed 42. Keep ML code in `ml/`, API in `backend/`, UI in `frontend/`. Do not use git or GitHub commands; I will handle version control myself. Ask me only if something is truly blocking.

---

## 1. Problem statement

Air pollution is a daily health issue in Indian cities, especially in winter. People need to know **how bad the air will be in the next 1 to 3 days** so they can plan outdoor activity, school runs, exercise and masks.

**Goal:** Build a system that
1. downloads the latest hourly air-quality and weather data for 10 Indian cities,
2. trains ML models to **forecast PM2.5 for the next 6 h, 24 h, 48 h and 72 h**,
3. predicts whether the **next-24-hour average PM2.5 will be "Poor" or worse** (alert classification),
4. explains each prediction (SHAP) and reports honest accuracy against baselines,
5. serves everything through a **FastAPI** backend and a **React.js dashboard**.

**Why this suits a mini project / hackathon:** real, current, large data; clear social impact; full ML pipeline plus a polished product with a live map, forecast charts and health advice.

---

## 2. Datasets (all free, current, API-based)

| # | Dataset | Link | Purpose in project |
|---|---|---|---|
| 1 | **Open-Meteo Air Quality API** (Copernicus CAMS global model; hourly PM2.5, PM10, CO, NO2, SO2, O3, aerosol optical depth, dust, US AQI; history from 2022-01-01 plus a short forecast) | https://open-meteo.com/en/docs/air-quality-api | **Main data and target.** Gives the pollutant history used to build training rows and the latest observations used at prediction time. |
| 2 | **Open-Meteo Historical Weather API** (ERA5 reanalysis; hourly temperature, humidity, dew point, pressure, wind, rain, cloud cover; back to 1940, up to a few days ago) | https://open-meteo.com/en/docs/historical-weather-api | **Weather features.** Pollution depends heavily on wind, humidity, rain and temperature. |
| 3 | **Open-Meteo Forecast API** (supports `past_days`, covers the most recent days the archive lacks) | https://open-meteo.com/en/docs | **Fills the last few days** of weather so the data is current to today, and provides weather for live inference. |
| 4 | **Open-Meteo Geocoding API** | https://open-meteo.com/en/docs/geocoding-api | Optional: lets the UI search any Indian city and get its coordinates. |
| 5 (optional) | **OpenAQ** ground-station measurements (free API key needed) | https://openaq.org and https://docs.openaq.org | Optional **sanity check**: compare model-based PM2.5 with real sensor readings for one or two cities. |
| 6 (reference) | **CPCB National AQI (NAQI)** category definitions | https://cpcb.nic.in | Reference for the Indian PM2.5 category cut-offs used to create labels. |

**Licensing and fair use:** Open-Meteo data is CC BY 4.0 and the free tier is meant for non-commercial and small-scale use. Add attribution ("Data: Open-Meteo, Copernicus CAMS, ERA5") in the app footer. No API key is needed for Open-Meteo.

**Honest limitation to state in the report:** dataset 1 is **modelled** (CAMS) data, not ground-sensor data. It is excellent for a forecasting project, but say clearly that it approximates real station readings. Use OpenAQ (optional) to quantify the gap.

### Cities and coordinates (lat, lon)
Pune (18.5204, 73.8567), Mumbai (19.0760, 72.8777), Delhi (28.6139, 77.2090), Bengaluru (12.9716, 77.5946), Chennai (13.0827, 80.2707), Kolkata (22.5726, 88.3639), Hyderabad (17.3850, 78.4867), Ahmedabad (23.0225, 72.5714), Lucknow (26.8467, 80.9462), Nagpur (21.1458, 79.0882).

### Expected data size
About 4.5 to 5 years x 8,760 hours x 10 cities = roughly 400k hourly rows (before feature engineering). Small enough for a laptop.

### Variables to request
- Air quality (hourly): `pm2_5, pm10, carbon_monoxide, nitrogen_dioxide, sulphur_dioxide, ozone, aerosol_optical_depth, dust, us_aqi`
- Weather (hourly): `temperature_2m, relative_humidity_2m, dew_point_2m, surface_pressure, precipitation, cloud_cover, wind_speed_10m, wind_direction_10m`
- Always request `timezone=Asia/Kolkata`.

### Target definitions
- **Regression targets:** `pm25_t+6h`, `pm25_t+24h`, `pm25_t+48h`, `pm25_t+72h` (PM2.5 in ug/m3 at that future hour for the same city).
- **Alert classification target:** `alert_24h = 1` if the mean PM2.5 over the next 24 hours is above 90 ug/m3 (NAQI "Poor" or worse), else 0.
- **NAQI PM2.5 categories (24 h average, ug/m3):** Good 0-30, Satisfactory 31-60, Moderate 61-90, Poor 91-120, Very Poor 121-250, Severe 250+. Use these for the category shown in the app.

---

## 3. Repository structure

```
aircast-india/
├── PLAN.md
├── README.md
├── requirements.txt
├── data/
│   ├── raw/                 # per-city parquet files straight from the APIs
│   └── processed/           # merged + engineered datasets
├── ml/
│   ├── config.py            # cities, variables, horizons, paths, seed
│   ├── ingest.py            # download + cache + incremental update
│   ├── clean.py             # merge, validate, impute
│   ├── features.py          # lags, rolling stats, calendar, weather features
│   ├── train.py             # train/tune/compare models, save best per horizon
│   ├── evaluate.py          # metrics, plots, backtests
│   ├── explain.py           # SHAP
│   └── predict.py           # live inference helper used by the API
├── notebooks/
│   ├── 01_eda.ipynb
│   └── 02_modeling.ipynb
├── models/                  # saved models + metadata.json
├── reports/figures/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── schemas.py           # Pydantic models
│   ├── services.py          # data refresh, caching, prediction
│   └── tests/
└── frontend/                # React app (see Section 6)
```

---

## 4. ML implementation phases

### Phase 0: Environment setup
- Create a Python virtual environment and `requirements.txt`: `pandas numpy pyarrow scikit-learn lightgbm xgboost optuna shap matplotlib seaborn plotly requests httpx fastapi uvicorn pydantic joblib pytest jupyter`
- Create the folder structure above and `ml/config.py` (cities dict, variable lists, `HORIZONS = [6, 24, 48, 72]`, `SEED = 42`).
- Check Node.js 18+ is installed (needed in Phase 9).

**Acceptance checks:** `python -c "import lightgbm, shap, fastapi"` works.

### Phase 1: Data ingestion (`ml/ingest.py`)
- For each city, download hourly **air quality** from the Open-Meteo Air Quality API from `2022-01-01` to today. Request in **chunks of at most 6 months** (the API limits range per call), with a short sleep and retry/backoff between calls.
- Download hourly **weather** from the Historical Weather API up to about 5 days ago, then fill the last days from the Forecast API using `past_days`.
- Save each city as `data/raw/{city}_aq.parquet` and `data/raw/{city}_weather.parquet`.
- Implement **incremental update**: if files exist, only fetch from the last stored timestamp onward. This is the "latest data" feature: running `python -m ml.ingest` always brings data up to today.
- Log row counts and the latest timestamp per city.

**Acceptance checks:** all 10 cities have data; latest timestamp is within 2 days of today; no duplicate timestamps.

### Phase 2: Exploratory data analysis (`notebooks/01_eda.ipynb`)
- Missing values and gaps per city; summary statistics.
- PM2.5 distribution (log-scale), monthly and hourly-of-day patterns, weekday vs weekend.
- Seasonality: monsoon (Jun-Sep) vs winter (Nov-Feb) per city; Delhi/Lucknow vs Bengaluru/Chennai.
- Correlation of PM2.5 with wind speed, humidity, rain, temperature, other pollutants.
- Year-over-year trend per city; extreme-pollution events (top 1% hours).
- Save at least 8 figures to `reports/figures/` and write 8-10 insight bullets.

**Acceptance checks:** notebook runs end to end; insights written.

### Phase 3: Cleaning and preprocessing (`ml/clean.py`)
- Merge air quality and weather on `city + timestamp`.
- Reindex to a complete hourly grid per city; fill small gaps (up to 3 hours) with linear interpolation, leave bigger gaps as missing and drop rows that cannot be used.
- Clip physically impossible values (negative concentrations, humidity outside 0-100).
- Convert wind direction into `wind_dir_sin` and `wind_dir_cos`.
- Save `data/processed/clean.parquet`.

**Acceptance checks:** no negative pollutant values, no duplicate `(city, timestamp)`, hourly continuity verified.

### Phase 4: Feature engineering (`ml/features.py`)
All features must use **only information available at time t** (no future leakage).
1. **Lag features** (per city): PM2.5 at t-1, 2, 3, 6, 12, 24, 48, 72, 168 h.
2. **Rolling statistics**: mean, std, min, max of PM2.5 over 6, 24, 72, 168 h; rolling mean of PM10, NO2, CO.
3. **Trend features**: PM2.5(t) minus PM2.5(t-24), 6-hour slope.
4. **Weather features**: current values plus 24 h rolling rain total, 24 h mean wind speed, humidity-temperature interaction, "stagnation index" (low wind x high pressure).
5. **Calendar features**: hour, day of week, month, day of year, weekend flag, cyclical encodings (`hour_sin/cos`, `month_sin/cos`), season label (winter, pre-monsoon, monsoon, post-monsoon), Diwali-window flag (hard-code Diwali dates for 2022-2026).
6. **City features**: city as categorical (one-hot or LightGBM categorical), latitude, longitude.
7. **Cross-pollutant ratios**: PM2.5/PM10, NO2/CO.
8. **Targets**: build `pm25_t+6h`, `pm25_t+24h`, `pm25_t+48h`, `pm25_t+72h` via `shift(-h)` per city, and `alert_24h` from the forward 24 h mean.
- Drop rows with missing lags or targets.
- Save `data/processed/features.parquet`.
- In the notebook, add a markdown table explaining why each feature group helps.

**Optional upgrade (flag clearly in report):** add future weather at t+h as "known covariates" (in production these come from the weather forecast). Note that training with reanalysis weather as a stand-in for forecasts is slightly optimistic.

**Acceptance checks:** unit test shows that shifting logic never uses future data for features; shape and NaN report printed.

### Phase 5: Model building (`ml/train.py`)
**Splits (time-based, never random):**
- **Train:** from 2022 up to a cutoff.
- **Validation:** time-series cross-validation with expanding windows (`TimeSeriesSplit`, 5 folds, with a gap equal to the max horizon to avoid overlap leakage).
- **Two final test sets:**
  - Test A: the **most recent 90 days** (what the live app will face).
  - Test B: **a winter holdout (Nov 2025 to Feb 2026)**, the hard season. Train this variant on data before Nov 2025.

**Models (per horizon):**
1. Baseline 1: **Persistence** (prediction = current PM2.5).
2. Baseline 2: **Seasonal naive** (PM2.5 at the same hour yesterday).
3. Ridge Regression
4. Random Forest
5. XGBoost
6. LightGBM
7. **Stacking ensemble** (RF + XGBoost + LightGBM, Ridge meta-learner) or weighted average ensemble tuned on validation data.
8. Optional stretch: small LSTM / GRU in PyTorch for comparison.

**Tuning:** Optuna (30-50 trials) for LightGBM and XGBoost, optimising RMSE (or MAE) on time-series CV. Consider training on `log1p(PM2.5)` and inverting predictions; compare both.

**Alert classifier:** LightGBM classifier for `alert_24h` with class weights; tune the decision threshold for recall >= 0.80 with best precision.

**Optional uncertainty:** train LightGBM quantile models (10th and 90th percentile) to give a **prediction interval** for the chart.

**Acceptance checks:** `reports/model_comparison.csv` (every model x horizon x test set); best model per horizon saved to `models/` with `metadata.json` (feature list, metrics, training date, latest data timestamp).

### Phase 6: Evaluation (`ml/evaluate.py`, `notebooks/02_modeling.ipynb`)
- Regression metrics: MAE, RMSE, R2, and **skill score vs persistence** (1 - RMSE_model / RMSE_persistence).
- Report by horizon, by city, by season.
- Classification metrics for alerts: precision, recall, F1, PR-AUC, ROC-AUC, confusion matrix.
- **Category accuracy:** how often the predicted NAQI category equals the true category, and "within one category".
- Plots: actual vs predicted time series for 2 cities, error vs horizon, residual histogram, per-city bar chart.
- Be honest: error grows with horizon, and extreme spikes are the hardest. Do not claim unrealistic accuracy.

**Acceptance checks:** all figures saved; model beats persistence at 24/48/72 h on Test A; a short written conclusion for each result.

### Phase 7: Explainability (`ml/explain.py`)
- SHAP `TreeExplainer` on the best tree model for the 24 h horizon.
- Global importance (beeswarm and top-15 bar).
- Local explanation function `explain(city, timestamp)` returning the top 5 features with signed contributions in plain English (e.g. "Low wind speed raised the predicted PM2.5 by 18 ug/m3").
- Save global feature importance as JSON for the frontend.

**Acceptance checks:** `explain()` returns valid output for a sample row.

---

## 5. Backend implementation phases (FastAPI)

### Phase 8: Backend API (`backend/`)
**Startup behaviour:** load models and metadata; load the latest processed data into memory; start a background refresh (every 3 hours) that runs incremental ingestion for recent days, rebuilds features for the latest rows and caches predictions.

**Endpoints (JSON, CORS enabled for `http://localhost:5173`):**

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | status, model version, latest data timestamp |
| GET | `/api/cities` | list of cities with lat/lon |
| GET | `/api/overview` | for every city: current PM2.5, NAQI category, next-24h alert flag, predicted PM2.5 at 24 h (powers the map) |
| GET | `/api/cities/{city}/current` | latest pollutant and weather readings |
| GET | `/api/cities/{city}/history?hours=168` | past hourly PM2.5 (and optional pollutants) |
| GET | `/api/cities/{city}/forecast` | hourly forecast for next 72 h with `pm25`, `lower`, `upper`, `category`, plus alert probability |
| GET | `/api/cities/{city}/explain` | top contributing factors for the current forecast |
| GET | `/api/cities/{city}/best-time` | best 3-hour outdoor window in the next 48 h (lowest predicted PM2.5) |
| GET | `/api/compare?cities=Pune,Delhi` | side-by-side forecast series |
| GET | `/api/model/performance` | metrics table, per-horizon errors, baseline comparison |
| GET | `/api/model/importance` | global SHAP importance |
| GET | `/api/advisory?category=Poor` | health advice for a category (static content, per group: general, children, asthma/elderly, exercise) |

**Implementation notes**
- Pydantic response models in `schemas.py`; consistent error format `{ "detail": "..." }`.
- Interpolate the hourly forecast between horizon predictions (6, 24, 48, 72 h) or train additional horizons (12, 36, 60 h) for a smoother curve. Pick one and document it.
- Cache results in memory with a timestamp so the UI is fast.
- Pytest tests for `/api/health`, `/api/overview`, `/api/cities/Pune/forecast`.

**Acceptance checks:** `uvicorn backend.main:app --reload` runs; Swagger docs at `/docs` show all endpoints; all return valid JSON for all 10 cities.

---

## 6. Frontend plan (React.js)

### 6.1 Tech choices
- **React 18 + Vite** (JavaScript or TypeScript; TypeScript preferred if comfortable)
- **React Router v6** (pages), **TanStack Query (React Query)** (data fetching, caching, auto-refresh), **Axios** (HTTP client)
- **Tailwind CSS** (styling), optional **shadcn/ui** or **Headless UI** components
- **Recharts** for line/area/bar charts (or Plotly.js for richer interaction)
- **React-Leaflet + Leaflet** for the India map (OpenStreetMap tiles)
- **Lucide-react** icons, **date-fns** for date formatting
- Optional: **Framer Motion** for subtle animation, **react-hot-toast** for notifications
- Config via `.env`: `VITE_API_BASE_URL=http://localhost:8000`

### 6.2 Folder structure
```
frontend/
├── index.html
├── package.json
├── vite.config.js
├── tailwind.config.js
└── src/
    ├── main.jsx
    ├── App.jsx                    # routes + layout
    ├── api/
    │   ├── client.js              # axios instance, error handling
    │   └── endpoints.js           # one function per backend endpoint
    ├── hooks/
    │   ├── useOverview.js         # React Query hooks wrapping endpoints
    │   ├── useForecast.js
    │   └── useTheme.js            # dark/light toggle
    ├── components/
    │   ├── layout/ (Navbar, Footer, PageContainer)
    │   ├── common/ (Card, Loader, ErrorState, EmptyState, Badge)
    │   ├── aqi/ (AqiBadge, AqiGauge, CategoryLegend, PollutantTile)
    │   ├── charts/ (ForecastChart, HistoryChart, CompareChart, ImportanceBar, ErrorByHorizonChart)
    │   ├── map/ (IndiaMap, CityMarker)
    │   └── advice/ (HealthAdvisoryCard, BestTimeCard)
    ├── pages/
    │   ├── Dashboard.jsx
    │   ├── CityDetail.jsx
    │   ├── Compare.jsx
    │   ├── ModelInsights.jsx
    │   └── About.jsx
    ├── utils/
    │   ├── aqi.js                 # NAQI category, color, label from PM2.5
    │   └── format.js
    └── styles/index.css
```

### 6.3 Design system
- NAQI colors: Good `#00b050`, Satisfactory `#92d050`, Moderate `#ffd966`, Poor `#ff9900`, Very Poor `#ff0000`, Severe `#7f0000`. Never rely on color alone: always show the category text too.
- Mobile-first, responsive grid (1 column on phones, 2-3 on tablets, 3-4 on desktop).
- Dark and light theme toggle stored in memory/`localStorage` (this works in a normal browser app).
- Accessible: semantic HTML, alt text and aria-labels for charts and map markers, keyboard navigable.

### 6.4 Pages and features

**Page 1: Dashboard (`/`)**
- Header with title, "Last updated" time (from `/api/health`) and a refresh button.
- **India map** with a colored marker per city (from `/api/overview`); popup shows current PM2.5, category, 24 h prediction; click goes to the city page.
- **City cards grid:** AqiBadge, current PM2.5, arrow showing predicted trend (better/worse in 24 h), alert icon if `alert_24h` is true.
- Summary strip: most polluted city now, cleanest city now, number of cities with alerts.
- Search/filter box and sort (by PM2.5, by name).

**Page 2: City Detail (`/city/:name`)**
- Top: big AQI gauge, category, current weather tiles (temperature, humidity, wind, rain) and pollutant tiles (PM10, NO2, SO2, O3, CO).
- **Forecast chart:** next 72 h PM2.5 line with shaded 10-90% interval and colored category bands in the background; tooltip with time, value, category.
- **History vs forecast chart:** last 7 days (actual) joined to next 3 days (predicted), vertical "now" line.
- **Alert panel:** "Probability of Poor/worse air in the next 24 h: 72%" with progress bar.
- **Why this forecast? (explainability):** horizontal bar chart of the top 5 SHAP factors with plain-English sentences.
- **Best time outdoors** card (from `/best-time`).
- **Health advisory** card with tabs: General, Children, Asthma/Elderly, Exercise.

**Page 3: Compare (`/compare`)**
- Multi-select up to 4 cities; overlay forecast lines on one chart; table of min/avg/max predicted PM2.5 and category counts.

**Page 4: Model Insights (`/model`)**
- Metrics table (MAE, RMSE, skill vs persistence) per horizon from `/api/model/performance`.
- Bar chart: model vs persistence baseline; error-by-horizon chart.
- Global feature importance chart.
- Short text on method, data sources, and limitations.

**Page 5: About (`/about`)**
- Dataset sources with links, attribution, methodology summary, limitations and disclaimer ("Educational project, not an official AQI source or medical advice").

### 6.5 Frontend implementation phases

**Phase 9: Frontend scaffold and API layer**
- `npm create vite@latest frontend -- --template react` (or `react-ts`), install dependencies: `react-router-dom @tanstack/react-query axios recharts leaflet react-leaflet lucide-react date-fns tailwindcss postcss autoprefixer`.
- Configure Tailwind, routes, base layout (Navbar, Footer), `.env`.
- Build `api/client.js`, `endpoints.js`, and React Query hooks with `refetchInterval` of 10 minutes.
- Build shared components: Card, Loader, ErrorState, AqiBadge, and `utils/aqi.js`.

**Acceptance checks:** `npm run dev` shows the layout; a test call to `/api/health` displays the model version and last update time.

**Phase 10: Dashboard and City Detail pages**
- Implement `IndiaMap`, city cards, summary strip (Dashboard).
- Implement `ForecastChart`, `HistoryChart`, gauge, weather/pollutant tiles, alert panel, explainability bar chart, best-time and advisory cards (City Detail).
- Handle loading skeletons, error states, empty states.

**Acceptance checks:** every city page renders with live backend data; charts show the 72 h forecast with interval; map markers are colored correctly.

**Phase 11: Compare, Model Insights, About, and polish**
- Implement Compare (multi-select, overlay chart, summary table), Model Insights, About.
- Add dark mode, responsive fixes, accessibility pass, favicon, page titles, toast on failed refresh, footer attribution.
- Test on mobile width (about 375 px) and desktop.

**Acceptance checks:** all 5 pages work on mobile and desktop; no console errors; Lighthouse accessibility score above 90 (nice to have).

---

## 7. Integration and testing

### Phase 12: Integration, testing, and run scripts
- End-to-end test: run `ml.ingest`, `ml.features`, `ml.train`, start backend, start frontend, click through every page.
- Backend: pytest passes. Frontend: manual checklist of all pages, plus a few React Testing Library tests (e.g. `AqiBadge` shows the right category for 25, 75, 130, 300 ug/m3).
- Add `run_all.sh` (or a README section) with the exact commands:
  1. `pip install -r requirements.txt`
  2. `python -m ml.ingest` then `python -m ml.features` then `python -m ml.train`
  3. `uvicorn backend.main:app --reload --port 8000`
  4. `cd frontend && npm install && npm run dev`
- Write `README.md` (problem, data sources, architecture, results table, screenshots, how to run, limitations).
- Write a short `reports/final_report.md` (Introduction, Data, Preprocessing, Features, Models, Results, Explainability, Limitations, Future work).

**Acceptance checks:** a fresh run from the commands above works on a clean machine; the report contains real numbers from `model_comparison.csv`.

---

## 8. Architecture overview

```
Open-Meteo APIs (air quality, weather, forecast)
        │  (incremental ingestion)
        ▼
  ml/ingest -> ml/clean -> ml/features -> ml/train -> models/*.joblib
                                               │
                                               ▼
                          FastAPI (backend/) <- live data refresh every 3 h
                                               │  JSON
                                               ▼
              React + Vite dashboard (map, charts, SHAP, advisory)
```

---

## 9. ML concepts covered (for report and viva)

| Concept | Where |
|---|---|
| Time-series data handling, gaps, interpolation | Phases 1, 3 |
| Feature engineering: lags, rolling windows, cyclical encoding | Phase 4 |
| Leakage prevention in time series | Phases 4, 5 |
| Time-based CV with gap, rolling-origin backtesting | Phase 5 |
| Baselines (persistence, seasonal naive) | Phases 5, 6 |
| Bagging, boosting, stacking ensembles | Phase 5 |
| Hyperparameter tuning (Optuna) | Phase 5 |
| Imbalanced classification and threshold tuning | Phase 5 |
| Quantile regression for uncertainty | Phase 5 |
| Explainable AI (SHAP) | Phase 7 |
| Model serving and live data refresh | Phase 8 |

**Likely viva questions:** Why not a random train/test split for time series? What is persistence and why must you beat it? Why does error rise with forecast horizon? What is a stacking ensemble? How do you avoid leakage with lag features? What does a SHAP value mean? What are the limits of using CAMS model data instead of ground sensors?

---

## 10. Stretch goals
- Compare with an LSTM/GRU or a Temporal Fusion style model.
- Add more cities, or let users search any city with the Geocoding API (train a single "global" model with lat/lon features).
- Validate against OpenAQ ground stations for Pune and Delhi and show the bias in the Model Insights page.
- Add an "alert subscription" demo (email/WhatsApp simulation) when predicted category is Poor or worse.
- Add a what-if slider on the City page ("what if wind speed doubles?") that calls a `/api/whatif` endpoint using the model.

---

## 11. Definition of done
- [ ] Data downloaded for 10 cities up to within 2 days of today, with incremental update working
- [ ] Feature pipeline with no leakage and unit tests
- [ ] At least 6 models compared, including persistence baselines and a stacking ensemble
- [ ] Two test sets (recent 90 days and winter holdout) reported honestly
- [ ] SHAP explanations integrated into the API and UI
- [ ] FastAPI backend with all endpoints and passing tests
- [ ] React frontend with 5 pages, map, forecast charts, dark mode, responsive layout
- [ ] README and short final report with real results
