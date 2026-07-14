"""Tests for custom exceptions."""

import pytest

from app.exceptions import (
    CityNotFoundError,
    InvalidAPIKeyError,
    InvalidDataError,
    WeatherProviderError,
    WeatherServiceError,
)


class TestExceptionHierarchy:
    def test_weather_service_error_is_base(self) -> None:
        assert issubclass(CityNotFoundError, WeatherServiceError)
        assert issubclass(WeatherProviderError, WeatherServiceError)
        assert issubclass(InvalidDataError, WeatherServiceError)
        assert issubclass(InvalidAPIKeyError, WeatherServiceError)

    def test_all_inherit_from_exception(self) -> None:
        assert issubclass(WeatherServiceError, Exception)

    def test_city_not_found_error_message(self) -> None:
        with pytest.raises(WeatherServiceError, match="City not found: Accra"):
            raise CityNotFoundError("Accra")

    def test_city_not_found_stores_city(self) -> None:
        exc = CityNotFoundError("Accra")
        assert exc.city == "Accra"

    def test_invalid_api_key_error_default_message(self) -> None:
        with pytest.raises(InvalidAPIKeyError, match="Invalid or missing API key"):
            raise InvalidAPIKeyError()

    def test_invalid_api_key_error_custom_message(self) -> None:
        with pytest.raises(InvalidAPIKeyError, match="Key expired"):
            raise InvalidAPIKeyError("Key expired")

    def test_weather_service_error_with_details(self) -> None:
        exc = WeatherServiceError("error", details={"code": 500})
        assert exc.details == {"code": 500}

    def test_weather_provider_error_message(self) -> None:
        with pytest.raises(WeatherProviderError, match="timeout"):
            raise WeatherProviderError("timeout")
