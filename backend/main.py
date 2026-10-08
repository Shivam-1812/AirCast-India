"""AirCast India API."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ml.config import CITIES, naqi_category

from . import schemas
from .services import ADVISORY, COLORS, get_state

REFRESH_SECONDS = 3 * 3600
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_state()

    async def loop():
        while True:
            await asyncio.sleep(REFRESH_SECONDS)
            await asyncio.to_thread(get_state().refresh)

    task = asyncio.create_task(loop())
    yield
    task.cancel()


app = FastAPI(title="AirCast India API", version="1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(HTTPException)
async def http_exc(_: Request, exc: HTTPException):
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


def _city(name: str) -> str:
    for c in CITIES:
        if c.lower() == name.lower():
            return c
    raise HTTPException(404, f"Unknown city '{name}'")


@app.get("/api/health", response_model=schemas.Health)
def health():
    s = get_state()
    return dict(status="ok", model_version=s.pred.meta["trained_at"],
                latest_data_timestamp=str(s.feats["timestamp"].max()), last_refresh=s.last_refresh)


@app.get("/api/cities", response_model=list[schemas.City])
def cities():
    return [dict(name=n, lat=la, lon=lo) for n, (la, lo) in CITIES.items()]


@app.get("/api/overview", response_model=list[schemas.OverviewItem])
def overview():
    return get_state().overview()


@app.get("/api/cities/{city}/current", response_model=schemas.Current)
def current(city: str):
    s, city = get_state(), _city(city)
    r = s.city_row(city)
    cat = naqi_category(float(r["pm2_5"]))
    last = s.clean[s.clean.city == city].iloc[-1]
    f = lambda k: None if pd.isna(last[k]) else round(float(last[k]), 2)
    return dict(city=city, observed_at=pd.Timestamp(last["timestamp"]).isoformat(), category=cat, color=COLORS[cat],
                us_aqi=f("us_aqi"),
                pollutants={"pm25": f("pm2_5"), "pm10": f("pm10"), "no2": f("nitrogen_dioxide"),
                            "so2": f("sulphur_dioxide"), "o3": f("ozone"), "co": f("carbon_monoxide")},
                weather={"temperature": f("temperature_2m"), "humidity": f("relative_humidity_2m"),
                         "wind_speed": f("wind_speed_10m"), "rain": f("precipitation"),
                         "pressure": f("surface_pressure"), "cloud_cover": f("cloud_cover")})


@app.get("/api/cities/{city}/history", response_model=list[schemas.HistoryPoint])
def history(city: str, hours: int = Query(168, ge=1, le=2160)):
    s, city = get_state(), _city(city)
    d = s.clean[s.clean.city == city].tail(hours)
    return [dict(timestamp=pd.Timestamp(t).isoformat(), pm25=None if pd.isna(a) else round(float(a), 1),
                 pm10=None if pd.isna(b) else round(float(b), 1), no2=None if pd.isna(c) else round(float(c), 1))
            for t, a, b, c in zip(d.timestamp, d.pm2_5, d.pm10, d.nitrogen_dioxide)]


@app.get("/api/cities/{city}/forecast", response_model=schemas.Forecast)
def forecast(city: str):
    s, city = get_state(), _city(city)
    f = s.forecasts[city]
    mean24 = float(np.mean(f["pm25"][1:25]))
    return dict(city=city, generated_from=s.latest_ts(city).isoformat(), alert_24h=bool(f["alert"]),
                alert_score=round(f["alert_score"], 3), mean_24h=round(mean24, 1),
                category_24h=naqi_category(mean24), points=s.forecast_points(city))


@app.get("/api/cities/{city}/explain", response_model=schemas.Explain)
def explain(city: str):
    s, city = get_state(), _city(city)
    try:
        return s.explain(city)
    except RuntimeError as e:
        raise HTTPException(503, str(e))


@app.get("/api/cities/{city}/best-time", response_model=schemas.BestTime)
def best_time(city: str):
    return get_state().best_time(_city(city))


@app.get("/api/compare", response_model=schemas.Compare)
def compare(cities: str = Query(..., description="comma separated, e.g. Pune,Delhi")):
    names = [_city(c.strip()) for c in cities.split(",") if c.strip()]
    if not 1 <= len(names) <= 4:
        raise HTTPException(422, "Provide 1 to 4 cities")
    s = get_state()
    return {"series": {n: s.forecast_points(n) for n in names}}


@app.get("/api/model/performance")
def performance():
    return get_state().perf


@app.get("/api/model/importance")
def importance():
    return get_state().importance


@app.get("/api/advisory", response_model=schemas.Advisory)
def advisory(category: str = "Moderate"):
    for k in ADVISORY:
        if k.lower() == category.lower():
            summary, groups = ADVISORY[k]
            return dict(category=k, color=COLORS[k], summary=summary, groups=groups)
    raise HTTPException(404, f"Unknown category '{category}'")
