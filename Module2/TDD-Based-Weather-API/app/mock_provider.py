"""Mock weather provider for testing and development.

This module provides a mock implementation of the WeatherProvider
interface that returns predefined weather data for known cities.
"""

from app.exceptions import CityNotFoundError
from app.models import WeatherData
from app.providers import WeatherProvider

MOCK_DATA: dict[str, WeatherData] = {
    "Kigali": WeatherData(22.5, 65, "Partly Cloudy", "Kigali"),
    "Kampala": WeatherData(28.0, 75, "Sunny", "Kampala"),
    "Nairobi": WeatherData(24.0, 70, "Cloudy", "Nairobi"),
    "Lagos": WeatherData(32.0, 85, "Humid", "Lagos"),
}


class MockWeatherProvider(WeatherProvider):
    """Mock implementation of WeatherProvider for testing.

    This provider returns predefined weather data for a set of known cities.
    It raises CityNotFoundError for unknown cities.
    """

    def get_weather(self, city: str) -> WeatherData:
        """Fetch weather data for a specific city.

        Args:
            city: Name of the city to fetch weather data for.

        Returns:
            WeatherData object containing the weather information.

        Raises:
            CityNotFoundError: If the city is not in the mock database.
        """
        key = city.strip().title()
        if key not in MOCK_DATA:
            raise CityNotFoundError(city)
        return MOCK_DATA[key]
