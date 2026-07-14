"""Custom exceptions for the Weather API Service.

Exception Hierarchy:
    WeatherServiceError (base)
    ├── CityNotFoundError
    ├── WeatherProviderError
    └── InvalidDataError
"""

from __future__ import annotations


class WeatherServiceError(Exception):
    """Base exception for all weather service errors."""

    def __init__(self, message: str, details: object = None) -> None:
        """Initialize the exception.

        Args:
            message: Error message describing the problem.
            details: Additional details about the error.
        """
        super().__init__(message)
        self.details = details


class CityNotFoundError(WeatherServiceError):
    """Raised when a city cannot be found in the weather data."""

    def __init__(self, city: str) -> None:
        """Initialize the exception.

        Args:
            city: Name of the city that was not found.
        """
        super().__init__(f"City not found: {city}")
        self.city = city


class WeatherProviderError(WeatherServiceError):
    """Raised when there is an error communicating with the weather provider."""


class InvalidDataError(WeatherServiceError):
    """Raised when weather data is invalid or malformed."""
