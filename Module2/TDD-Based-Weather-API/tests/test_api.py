"""Tests for FastAPI endpoints."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app, get_service

client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


@pytest.mark.parametrize(
    "city, expected_temp",
    [
        ("Kigali", 22.5),
        ("Kampala", 28.0),
        ("Nairobi", 24.0),
        ("Lagos", 32.0),
    ],
)
def test_get_weather_all_cities(city: str, expected_temp: float) -> None:
    response = client.get(f"/weather/{city}")
    assert response.status_code == 200
    data = response.json()
    assert data["city"] == city
    assert data["temperature"] == expected_temp


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
    from app.exceptions import InvalidDataError

    mock_service = MagicMock()
    mock_service.get_weather.side_effect = InvalidDataError("Invalid data")
    app.dependency_overrides[get_service] = lambda: mock_service
    try:
        response = client.get("/weather/Test")
        assert response.status_code == 400
    finally:
        app.dependency_overrides.pop(get_service, None)


def test_provider_error_returns_502() -> None:
    from app.exceptions import WeatherProviderError

    mock_service = MagicMock()
    mock_service.get_weather.side_effect = WeatherProviderError("Provider failed")
    app.dependency_overrides[get_service] = lambda: mock_service
    try:
        response = client.get("/weather/Test")
        assert response.status_code == 502
    finally:
        app.dependency_overrides.pop(get_service, None)


def test_invalid_api_key_returns_401() -> None:
    from app.exceptions import InvalidAPIKeyError

    mock_service = MagicMock()
    mock_service.get_weather.side_effect = InvalidAPIKeyError()
    app.dependency_overrides[get_service] = lambda: mock_service
    try:
        response = client.get("/weather/Test")
        assert response.status_code == 401
    finally:
        app.dependency_overrides.pop(get_service, None)


class TestForecastEndpoint:
    def test_get_forecast_kigali(self) -> None:
        response = client.get("/forecast/Kigali")
        assert response.status_code == 200
        data = response.json()
        assert data["city"] == "Kigali"
        assert data["temperature"] == 22.5

    def test_get_forecast_unknown_city(self) -> None:
        response = client.get("/forecast/UnknownCity")
        assert response.status_code == 404

    def test_get_forecast_response_fields(self) -> None:
        response = client.get("/forecast/Kigali")
        data = response.json()
        assert all(
            k in data for k in ["city", "temperature", "humidity", "description"]
        )

    def test_get_forecast_invalid_data_returns_400(self) -> None:
        from app.exceptions import InvalidDataError

        mock_service = MagicMock()
        mock_service.get_forecast.side_effect = InvalidDataError("Invalid data")
        app.dependency_overrides[get_service] = lambda: mock_service
        try:
            response = client.get("/forecast/Test")
            assert response.status_code == 400
        finally:
            app.dependency_overrides.pop(get_service, None)

    def test_get_forecast_provider_error_returns_502(self) -> None:
        from app.exceptions import WeatherProviderError

        mock_service = MagicMock()
        mock_service.get_forecast.side_effect = WeatherProviderError("Provider failed")
        app.dependency_overrides[get_service] = lambda: mock_service
        try:
            response = client.get("/forecast/Test")
            assert response.status_code == 502
        finally:
            app.dependency_overrides.pop(get_service, None)
