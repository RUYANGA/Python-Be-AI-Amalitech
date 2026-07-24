"""Tests for MockWeatherProvider."""

import pytest

from app.exceptions import CityNotFoundError
from app.mock_provider import MockWeatherProvider


def test_get_weather_kigali(mock_provider: MockWeatherProvider) -> None:
    result = mock_provider.get_weather("Kigali")
    assert result.city == "Kigali"
    assert result.temperature == 22.5


def test_get_weather_kampala(mock_provider: MockWeatherProvider) -> None:
    result = mock_provider.get_weather("Kampala")
    assert result.city == "Kampala"
    assert result.temperature == 28.0


@pytest.mark.parametrize(
    "city, expected_temp",
    [
        ("Kigali", 22.5),
        ("Kampala", 28.0),
        ("Nairobi", 24.0),
        ("Lagos", 32.0),
    ],
)
def test_known_cities(
    mock_provider: MockWeatherProvider, city: str, expected_temp: float
) -> None:
    result = mock_provider.get_weather(city)
    assert result.city == city
    assert result.temperature == expected_temp


def test_unknown_city_raises_error(mock_provider: MockWeatherProvider) -> None:
    with pytest.raises(CityNotFoundError):
        mock_provider.get_weather("UnknownCity")


def test_case_insensitive(mock_provider: MockWeatherProvider) -> None:
    result = mock_provider.get_weather("kigali")
    assert result.city == "Kigali"


@pytest.mark.parametrize(
    "city",
    [
        "kampala",
        "NAIROBI",
        "lagos",
    ],
)
def test_case_insensitive_variants(
    mock_provider: MockWeatherProvider, city: str
) -> None:
    result = mock_provider.get_weather(city)
    assert result.city == city.title()
