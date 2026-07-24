"""Weather service implementation with dependency injection.

This module provides the core business logic for fetching and
validating weather data. It follows SOLID principles and uses
dependency injection for the weather provider.
"""

from app.exceptions import (
    CityNotFoundError,
    InvalidDataError,
    WeatherProviderError,
)
from app.logger import get_logger
from app.models import WeatherData
from app.providers import WeatherProvider

logger = get_logger("weather_service")


class WeatherService:
    """Service for retrieving and validating weather data.

    This service implements the weather data retrieval logic while depending
    on the WeatherProvider interface, enabling easy swapping of providers.
    """

    def __init__(self, provider: WeatherProvider, api_key: str = "default-key") -> None:
        """Initialize the weather service.

        Args:
            provider: Weather provider implementation to use.
            api_key: API key for authenticating with the weather provider.
        """
        self._provider = provider
        self._api_key = api_key

    def get_weather(self, city: str) -> WeatherData:
        """Fetch weather data for a specific city.

        Args:
            city: Name of the city to fetch weather data for.

        Returns:
            WeatherData object containing the weather information.

        Raises:
            InvalidDataError: If the city name is empty or invalid.
            CityNotFoundError: If the city cannot be found.
            WeatherProviderError: If there is an error with the provider.
        """
        if not city or not city.strip():
            raise InvalidDataError("City name cannot be empty")

        try:
            logger.info("Fetching weather for %s", city)
            data = self._provider.get_weather(city)
            self._validate(data)
            logger.info(
                "Weather fetched: %s - %.1f°C",
                city,
                data.temperature,
            )
            return data
        except CityNotFoundError:
            raise
        except InvalidDataError:
            raise
        except Exception as e:
            logger.error("Provider error: %s", e)
            raise WeatherProviderError(f"Provider failed for {city}") from e

    def get_forecast(self, city: str) -> WeatherData:
        """Fetch forecast data for a specific city.

        This method delegates to get_weather to retrieve forecast data.
        It serves as the primary forecast interface as specified in the
        service requirements.

        Args:
            city: Name of the city to fetch forecast data for.

        Returns:
            WeatherData object containing the forecast information.

        Raises:
            InvalidDataError: If the city name is empty or invalid.
            CityNotFoundError: If the city cannot be found.
            WeatherProviderError: If there is an error with the provider.
        """
        logger.info("Forecast requested for %s", city)
        return self.get_weather(city)

    def _validate(self, data: WeatherData) -> None:
        """Validate weather data response.

        Args:
            data: WeatherData object to validate.

        Raises:
            InvalidDataError: If the weather data is invalid.
        """
        if data.temperature < -273.15:
            raise InvalidDataError(f"Invalid temperature: {data.temperature}°C")
        if not (0 <= data.humidity <= 100):
            raise InvalidDataError(f"Invalid humidity: {data.humidity}%")
        if not data.description:
            raise InvalidDataError("Description cannot be empty")
