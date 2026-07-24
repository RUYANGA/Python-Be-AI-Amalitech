"""Data models for the Weather API Service."""

from dataclasses import dataclass, field


@dataclass
class WeatherData:
    """Represents weather data for a specific location.

    Attributes:
        temperature: Current temperature in Celsius.
        humidity: Current humidity percentage (0-100).
        description: Weather description (e.g., 'Sunny', 'Cloudy').
        city: Name of the city for this weather data.
    """

    temperature: float
    humidity: int
    description: str
    city: str = field(default="")
