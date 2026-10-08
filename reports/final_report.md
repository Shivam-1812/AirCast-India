# AirCast India: final report

## 1. Introduction
AirCast India forecasts hourly PM2.5 for 10 Indian cities (Pune, Mumbai, Delhi, Bengaluru, Chennai, Kolkata, Hyderabad, Ahmedabad, Lucknow, Nagpur) for the next 72 hours, flags whether the next-24-hour average will be Poor or worse (> 90 µg/m³, CPCB NAQI), and explains each forecast with SHAP.

## 2. Data
- Open-Meteo Air Quality API (Copernicus CAMS global model): PM2.5, PM10, CO, NO2, SO2, O3, aerosol optical depth, dust, US AQI.
- Open-Meteo Historical Weather (ERA5) plus Forecast API `past_days` for the latest days: temperature, humidity, dew point, pressure, rain, cloud cover, wind.
- Window: 2022-08 to 2026-10-08 (CAMS values in the API are empty before about Aug 2022, so history starts then rather than 2022-01-01). 36,642 hourly rows per city, 366,420 in total, 364,020 labelled rows after feature engineering. Ingestion is incremental (`python -m ml.ingest`).
- The data is **modelled**, not ground-sensor data. OpenAQ validation was not done.

Insights from EDA (`notebooks/01_eda.ipynb`, 9 figures):
1. Delhi (mean 74 µg/m³), Lucknow (58) and Kolkata (58) are the most polluted; Bengaluru (21) and Chennai (23) the cleanest.
2. Winter (Nov-Feb) PM2.5 is 1.5x (Chennai) to 4.5x (Pune) the monsoon level.
3. PM2.5 follows a daily cycle: highest 19:00-01:00 (about 47 µg/m³), lowest 12:00-16:00 (about 32).
4. PM2.5 correlates with PM10 (r = 0.73) and NO2 (0.62), negatively with wind (-0.37) and temperature (-0.33), weakly with rain (-0.11).
5. The top 1% of hours (> 175 µg/m³) occur almost only in Delhi, Kolkata, Lucknow and Mumbai.
6. 2025 annual means rose in Delhi (66 → 80), Kolkata and Lucknow versus 2024.

## 3. Preprocessing
AQ and weather merged on city+timestamp, complete hourly grid, linear interpolation for gaps up to 3 h, clipping of impossible values, wind direction as sin/cos, rows after "now" dropped (the API returns model-forecast hours for today). Checks in `ml.clean` assert no negatives, no duplicates and hourly continuity.

## 4. Features (73)
PM2.5 lags (1-168 h), rolling mean/std/min/max (6-168 h), PM10/NO2/CO rolling means, 6 h and 24 h trends, weather (rain 24/72 h, mean wind, stagnation index, humidity x temperature, pressure/temperature change), calendar (hour, weekday, month, cyclical encodings, season, Diwali window), city latitude/longitude, PM2.5/PM10 and NO2/CO ratios. All use data at time ≤ t only; `ml/tests/test_features.py` perturbs future rows and verifies features at t do not change. Future weather is **not** used.

## 5. Models and protocol
Per horizon (6, 12, 24, 36, 48, 60, 72 h): Persistence, SeasonalNaive, 7-day mean baselines; Ridge, Random Forest, XGBoost, LightGBM, log1p variants, and a stacking ensemble (RF+XGB+LGBM, Ridge meta-learner fitted on out-of-fold expanding-window predictions). The full comparison runs on the 6/24/48/72 h headline horizons; 12/36/60 h use LightGBM only to give a smooth hourly curve (interpolated between horizons). Optuna (25 trials, 3 expanding-window folds, 72 h gap) tuned LightGBM and XGBoost at 24 h; parameters are reused for other horizons. Alert classifier: LightGBM with balanced class weights, threshold tuned for recall ≥ 0.80 on a validation block. Intervals: LightGBM 10%/90% quantile models.

Splits are chronological with a 72 h gap. **Test A** = last 90 days (Jul-Oct 2026, monsoon, mostly clean air); **Test B** = Nov 2025-Feb 2026 winter holdout (models trained only before Nov 2025). The model per horizon was chosen by mean RMSE over both test sets, so the reported scores carry a small selection effect (the top models differ by under 1 µg/m³). Production models are refit on all data.

## 6. Results (RMSE µg/m³, from `reports/model_comparison.csv`)
| Horizon | Best model | Test A RMSE | Persistence | Skill | Test B RMSE | Persistence | Skill |
|---|---|---|---|---|---|---|---|
| 6 h | LightGBM | 9.7 | 12.9 | 25% | 15.7 | 31.0 | 49% |
| 12 h | LightGBM | 11.4 | 16.1 | 29% | 19.6 | 37.8 | 48% |
| 24 h | XGBoost | 12.7 | 13.7 | 7% | 21.9 | 24.1 | 9% |
| 48 h | XGBoost | 15.7 | 18.0 | 13% | 25.8 | 30.6 | 16% |
| 72 h | LightGBM | 16.9 | 20.2 | 16% | 27.3 | 34.3 | 20% |

Full model x horizon x test tables: `reports/model_comparison.csv`, heatmaps in `reports/figures/eval_rmse_heatmap_*.png`.

Conclusions:
- Every selected model beats persistence at all horizons on both test sets, but the margin at 24 h is small (7-9%) because "same hour yesterday" already encodes the daily cycle; the largest gains are at 6 h and in winter.
- Ridge, Random Forest, XGBoost and LightGBM are within about 0.5 µg/m³ of each other at 6-72 h: most skill comes from autoregressive and calendar features, not model class. **The stacking ensemble did not beat the best single model** (e.g. 13.0 vs 12.7 at 24 h on Test A), so it is reported but not selected. log1p targets were consistently worse on RMSE.
- Error grows with horizon (MAE 5.7 → 9.9 on Test A) and is roughly doubled in winter; extreme spikes are hardest. R² falls from 0.83 (6 h) to 0.50 (72 h) on Test A.
- 24 h NAQI category accuracy: 82% exact / 99% within one category (Test A); 62% / 97% (winter).
- Alert classifier (threshold 0.75): Test A precision 0.71, recall 0.81, PR-AUC 0.82 (only 1.7% positive days); winter precision 0.79, recall 0.92, PR-AUC 0.93. Scores are uncalibrated because of class weighting; the UI says so.
- 80% prediction intervals cover 77-78% of Test A outcomes (slightly narrow).

## 7. Explainability
SHAP TreeExplainer on a dedicated LightGBM 24 h model. Global importance is led by current PM2.5, then PM2.5 1 h ago, city location, time of year and carbon monoxide (`reports/figures/shap_*.png`, `models/importance.json`). The API returns the top five factors with signed µg/m³ contributions in plain English.

## 8. Limitations
CAMS modelled data rather than station readings; no future-weather inputs (so long-horizon errors are larger than a forecast-driven model might achieve); Test A covers a clean monsoon period; hyperparameters tuned once at 24 h; only 4 years of history, so only four Diwalis; no OpenAQ validation.

## 9. Future work
Add weather-forecast covariates, OpenAQ bias correction, probability calibration for alerts, LSTM/GRU or temporal fusion models, a what-if endpoint, more cities via geocoding.
