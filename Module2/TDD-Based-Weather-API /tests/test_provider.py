"""Tests for MockWeatherProvider."""

import pytest
from app.mock_provider import MockWeatherProvider

from app.exceptions import CityNotFoundError


def test_get_weather_kigali(mock_provider: MockWeatherProvider) -> None:
    result = mock_provider.get_weather("Kigali")
    assert result.city == "Kigali"
    assert result.temperature == 22.5


def test_get_weather_kampala(mock_provider: MockWeatherProvider) -> None:
    result = mock_provider.get_weather("Kampala")
    assert result.city == "Kampala"
    assert result.temperature == 28.0


def test_unknown_city_raises_error(mock_provider: MockWeatherProvider) -> None:
    with pytest.raises(CityNotFoundError):
        mock_provider.get_weather("UnknownCity")


def test_case_insensitive(mock_provider: MockWeatherProvider) -> None:
    result = mock_provider.get_weather("kigali")
    assert result.city == "Kigali"
