"""Weather provider interface following Dependency Inversion Principle.

This module defines the abstract interface for weather data providers.
Concrete implementations should handle fetching weather data from
external APIs or other data sources.
"""

from abc import ABC, abstractmethod

from app.models import WeatherData


class WeatherProvider(ABC):
    """Abstract base class for weather data providers.

    This interface defines the contract for all weather providers.
    Implementations should return WeatherData for valid cities
    and raise CityNotFoundError for unknown cities.
    """

    @abstractmethod
    def get_weather(self, city: str) -> WeatherData:
        """Fetch weather data for a specific city.

        Args:
            city: Name of the city to fetch weather data for.

        Returns:
            WeatherData object containing the weather information.

        Raises:
            CityNotFoundError: If the city cannot be found.
        """
        ...
