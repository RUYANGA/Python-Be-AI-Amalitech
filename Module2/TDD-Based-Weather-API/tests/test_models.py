"""Tests for WeatherData model."""

from app.models import WeatherData


def test_create_weather_data() -> None:
    data = WeatherData(25.5, 60, "Sunny", "Kampala")
    assert data.temperature == 25.5
    assert data.humidity == 60
    assert data.description == "Sunny"
    assert data.city == "Kampala"


def test_default_city() -> None:
    data = WeatherData(30.0, 70, "Cloudy")
    assert data.city == ""


def test_fields_writable() -> None:
    data = WeatherData(20.0, 50, "Rainy")
    data.temperature = 22.5
    assert data.temperature == 22.5
