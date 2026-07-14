"""Tests for WeatherService."""

from typing import cast
from unittest.mock import MagicMock

import pytest

from app.exceptions import CityNotFoundError, InvalidDataError, WeatherProviderError
from app.models import WeatherData
from app.service import WeatherService


class TestSuccess:
    def test_get_weather_kigali(self, weather_service: WeatherService) -> None:
        result = weather_service.get_weather("Kigali")
        assert result.city == "Kigali"
        assert result.temperature == 22.5

    def test_get_weather_kampala(self, weather_service: WeatherService) -> None:
        result = weather_service.get_weather("Kampala")
        assert result.city == "Kampala"


class TestErrors:
    def test_unknown_city_raises_error(self, weather_service: WeatherService) -> None:
        with pytest.raises(CityNotFoundError):
            weather_service.get_weather("UnknownCity")

    def test_empty_city_raises_error(self, weather_service: WeatherService) -> None:
        with pytest.raises(InvalidDataError):
            weather_service.get_weather("")

    def test_whitespace_city_raises_error(
        self, weather_service: WeatherService
    ) -> None:
        with pytest.raises(InvalidDataError):
            weather_service.get_weather("   ")


class TestMocking:
    def test_collaborates_with_provider(
        self, weather_service_with_mock: WeatherService
    ) -> None:
        result = weather_service_with_mock.get_weather("TestCity")
        assert result.city == "TestCity"

    def test_passes_city_to_provider(
        self, weather_service_with_mock: WeatherService
    ) -> None:
        weather_service_with_mock.get_weather("TestCity")
        provider = cast(MagicMock, weather_service_with_mock._provider)
        provider.get_weather.assert_called_once_with("TestCity")

    def test_handles_provider_exception(
        self, mock_provider_interface: MagicMock
    ) -> None:
        mock_provider_interface.get_weather.side_effect = Exception("API Error")
        service = WeatherService(provider=mock_provider_interface)
        with pytest.raises(WeatherProviderError):
            service.get_weather("TestCity")

    def test_preserves_city_not_found_error(
        self, mock_provider_interface: MagicMock
    ) -> None:
        mock_provider_interface.get_weather.side_effect = CityNotFoundError("TestCity")
        service = WeatherService(provider=mock_provider_interface)
        with pytest.raises(CityNotFoundError):
            service.get_weather("TestCity")

    def test_validates_temperature_too_low(
        self, mock_provider_interface: MagicMock
    ) -> None:
        mock_provider_interface.get_weather.return_value = WeatherData(
            -300.0, 50, "Freezing", "Invalid"
        )
        service = WeatherService(provider=mock_provider_interface)
        with pytest.raises(InvalidDataError):
            service.get_weather("Invalid")

    def test_validates_humidity_too_high(
        self, mock_provider_interface: MagicMock
    ) -> None:
        mock_provider_interface.get_weather.return_value = WeatherData(
            25.0, 150, "Humid", "Invalid"
        )
        service = WeatherService(provider=mock_provider_interface)
        with pytest.raises(InvalidDataError):
            service.get_weather("Invalid")

    def test_validates_empty_description(
        self, mock_provider_interface: MagicMock
    ) -> None:
        mock_provider_interface.get_weather.return_value = WeatherData(
            25.0, 50, "", "TestCity"
        )
        service = WeatherService(provider=mock_provider_interface)
        with pytest.raises(InvalidDataError):
            service.get_weather("TestCity")
