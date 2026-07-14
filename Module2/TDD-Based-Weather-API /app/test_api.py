"""Tests for FastAPI endpoints."""

from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.exceptions import InvalidDataError, WeatherProviderError
from app.main import app, get_weather

client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_get_weather_kigali() -> None:
    response = client.get("/weather/Kigali")
    assert response.status_code == 200
    data = response.json()
    assert data["city"] == "Kigali"
    assert data["temperature"] == 22.5


def test_get_weather_kampala() -> None:
    response = client.get("/weather/Kampala")
    assert response.status_code == 200
    assert response.json()["city"] == "Kampala"


def test_get_weather_unknown_city() -> None:
    response = client.get("/weather/UnknownCity")
    assert response.status_code == 404


def test_get_weather_case_insensitive() -> None:
    response = client.get("/weather/kigali")
    assert response.status_code == 200
    assert response.json()["city"] == "Kigali"


def test_response_has_all_fields() -> None:
    response = client.get("/weather/Kigali")
    data = response.json()
    assert all(k in data for k in ["city", "temperature", "humidity", "description"])


def test_invalid_data_returns_400() -> None:
    with patch("app.main._service") as mock:
        mock.get_weather.side_effect = InvalidDataError("Invalid data")
        with patch("app.main.get_service", return_value=mock):
            test_app = FastAPI()
            test_app.get("/weather/{city}")(get_weather)
            test_client = TestClient(test_app)
            response = test_client.get("/weather/Test")
            assert response.status_code == 400


def test_provider_error_returns_502() -> None:
    with patch("app.main._service") as mock:
        mock.get_weather.side_effect = WeatherProviderError("Provider failed")
        with patch("app.main.get_service", return_value=mock):
            test_app = FastAPI()
            test_app.get("/weather/{city}")(get_weather)
            test_client = TestClient(test_app)
            response = test_client.get("/weather/Test")
            assert response.status_code == 502
