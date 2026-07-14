"""Shared test fixtures."""

from unittest.mock import MagicMock

import pytest

from app.mock_provider import MockWeatherProvider
from app.providers import WeatherProvider
from app.service import WeatherService


@pytest.fixture
def mock_provider() -> MockWeatherProvider:
    return MockWeatherProvider()


@pytest.fixture
def mock_provider_interface() -> MagicMock:
    provider = MagicMock(spec=WeatherProvider)
    provider.get_weather.return_value = MagicMock(
        temperature=25.0, humidity=60, description="Sunny", city="TestCity"
    )
    return provider


@pytest.fixture
def weather_service(mock_provider: MockWeatherProvider) -> WeatherService:
    return WeatherService(provider=mock_provider)


@pytest.fixture
def weather_service_with_mock(mock_provider_interface: MagicMock) -> WeatherService:
    return WeatherService(provider=mock_provider_interface)
