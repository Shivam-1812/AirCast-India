"""Download + incrementally update hourly air-quality and weather data (Open-Meteo)."""
from __future__ import annotations

import sys
import time
from datetime import date, datetime, timedelta

import pandas as pd
import requests

from .config import AQ_VARS, CITIES, RAW_DIR, START_DATE, TIMEZONE, WX_VARS

AQ_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
CHUNK_DAYS = 150  # < 6 months per call


def _get(url: str, params: dict, tries: int = 8) -> dict:
    delay = 5
    for i in range(tries):
        try:
            r = requests.get(url, params=params, timeout=90)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429 or r.status_code >= 500:
                wait = 65 if r.status_code == 429 else delay
                print(f"    HTTP {r.status_code}, sleeping {wait}s")
                time.sleep(wait)
                delay = min(delay * 2, 60)
                continue
            raise RuntimeError(f"{r.status_code}: {r.text[:200]}")
        except requests.RequestException as e:
            print(f"    network error {e!s:.80}, retry")
            time.sleep(delay)
            delay = min(delay * 2, 60)
    raise RuntimeError(f"failed after {tries} tries: {url}")


def _to_df(payload: dict) -> pd.DataFrame:
    h = payload["hourly"]
    df = pd.DataFrame(h)
    df["time"] = pd.to_datetime(df["time"])
    return df.set_index("time")


def _chunks(start: date, end: date):
    s = start
    while s <= end:
        e = min(s + timedelta(days=CHUNK_DAYS - 1), end)
        yield s, e
        s = e + timedelta(days=1)


def fetch_aq(lat: float, lon: float, start: date, end: date) -> pd.DataFrame:
    parts = []
    for s, e in _chunks(start, end):
        p = dict(latitude=lat, longitude=lon, hourly=",".join(AQ_VARS), timezone=TIMEZONE,
                 start_date=s.isoformat(), end_date=e.isoformat())
        parts.append(_to_df(_get(AQ_URL, p)))
        time.sleep(0.6)
    return pd.concat(parts) if parts else pd.DataFrame()


def fetch_weather(lat: float, lon: float, start: date, end: date) -> pd.DataFrame:
    """ERA5 archive up to ~5 days ago, forecast API (past_days) for the rest."""
    arch_end = min(end, date.today() - timedelta(days=5))
    parts = []
    if start <= arch_end:
        for s, e in _chunks(start, arch_end):
            p = dict(latitude=lat, longitude=lon, hourly=",".join(WX_VARS), timezone=TIMEZONE,
                     start_date=s.isoformat(), end_date=e.isoformat())
            parts.append(_to_df(_get(ARCHIVE_URL, p)))
            time.sleep(0.6)
    # recent days from forecast endpoint
    gap_start = max(start, arch_end + timedelta(days=1))
    if gap_start <= end:
        past = min((date.today() - gap_start).days + 1, 92)
        p = dict(latitude=lat, longitude=lon, hourly=",".join(WX_VARS), timezone=TIMEZONE,
                 past_days=past, forecast_days=1)
        df = _to_df(_get(FORECAST_URL, p))
        parts.append(df[df.index >= pd.Timestamp(gap_start)])
    return pd.concat(parts) if parts else pd.DataFrame()


def _update(path, fetcher, lat, lon, label: str) -> pd.DataFrame:
    today = date.today()
    old = pd.read_parquet(path) if path.exists() else None
    if old is not None and len(old):
        # re-fetch the last 2 days (recent values get revised)
        start = (old.index.max() - timedelta(days=2)).date()
    else:
        start = date.fromisoformat(START_DATE)
    new = fetcher(lat, lon, start, today)
    if old is not None and len(new):
        df = pd.concat([old[old.index < new.index.min()], new])
    elif old is not None:
        df = old
    else:
        df = new
    df = df[~df.index.duplicated(keep="last")].sort_index()
    df.to_parquet(path)
    return df


def ingest(cities: list[str] | None = None) -> None:
    for city in cities or list(CITIES):
        lat, lon = CITIES[city]
        print(f"[{city}]")
        aq = _update(RAW_DIR / f"{city}_aq.parquet", fetch_aq, lat, lon, "aq")
        wx = _update(RAW_DIR / f"{city}_weather.parquet", fetch_weather, lat, lon, "wx")
        print(f"  aq: {len(aq):,} rows, latest {aq['pm2_5'].dropna().index.max()}")
        print(f"  wx: {len(wx):,} rows, latest {wx['temperature_2m'].dropna().index.max()}")


if __name__ == "__main__":
    ingest(sys.argv[1:] or None)
