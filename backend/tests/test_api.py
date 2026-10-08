import pytest
from fastapi.testclient import TestClient

from backend.main import app
from ml.config import CITIES


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_overview(client):
    d = client.get("/api/overview").json()
    assert len(d) == 10 and all(x["category"] for x in d)


def test_forecast_pune(client):
    d = client.get("/api/cities/Pune/forecast").json()
    assert len(d["points"]) == 73
    p = d["points"][24]
    assert p["lower"] <= p["pm25"] <= p["upper"]


@pytest.mark.parametrize("city", list(CITIES))
def test_all_city_endpoints(client, city):
    for ep in ("current", "history?hours=48", "forecast", "explain", "best-time"):
        assert client.get(f"/api/cities/{city}/{ep}").status_code == 200, (city, ep)


def test_misc(client):
    assert client.get("/api/cities/Nowhere/forecast").json() == {"detail": "Unknown city 'Nowhere'"}
    assert len(client.get("/api/compare?cities=Pune,Delhi").json()["series"]) == 2
    assert client.get("/api/advisory?category=Poor").status_code == 200
    assert client.get("/api/model/performance").status_code == 200
    assert client.get("/api/model/importance").status_code == 200
