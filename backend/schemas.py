from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class Health(BaseModel):
    status: str
    model_version: str
    latest_data_timestamp: str
    last_refresh: Optional[str] = None


class City(BaseModel):
    name: str
    lat: float
    lon: float


class OverviewItem(BaseModel):
    city: str
    lat: float
    lon: float
    pm25: float
    category: str
    color: str
    alert_24h: bool
    alert_score: float
    pred_24h: float
    pred_category_24h: str
    trend: str  # "better" | "worse" | "steady"
    observed_at: str


class Current(BaseModel):
    city: str
    observed_at: str
    category: str
    color: str
    us_aqi: Optional[float] = None
    pollutants: dict[str, Optional[float]]
    weather: dict[str, Optional[float]]


class HistoryPoint(BaseModel):
    timestamp: str
    pm25: Optional[float] = None
    pm10: Optional[float] = None
    no2: Optional[float] = None


class ForecastPoint(BaseModel):
    timestamp: str
    hour_ahead: int
    pm25: float
    lower: float
    upper: float
    category: str


class Forecast(BaseModel):
    city: str
    generated_from: str
    alert_24h: bool
    alert_score: float
    mean_24h: float
    category_24h: str
    points: list[ForecastPoint]


class Factor(BaseModel):
    label: str
    shap: float
    direction: str
    text: str


class Explain(BaseModel):
    city: str
    horizon_hours: int
    base_value: float
    factors: list[Factor]


class BestTime(BaseModel):
    city: str
    start: str
    end: str
    mean_pm25: float
    category: str
    worst_start: str
    worst_mean_pm25: float


class Compare(BaseModel):
    series: dict[str, list[ForecastPoint]]


class Advisory(BaseModel):
    category: str
    color: str
    summary: str
    groups: dict[str, str]


JSON = dict[str, Any]
