"""FastAPI application for Weather API Service.

This module provides the REST API endpoints for fetching weather data.
It uses FastAPI with dependency injection for the weather service.
"""

from dataclasses import asdict

from fastapi import Depends, FastAPI, HTTPException

from app.exceptions import (
    CityNotFoundError,
    InvalidDataError,
    WeatherProviderError,
)
from app.logger import get_logger
from app.mock_provider import MockWeatherProvider
from app.service import WeatherService

logger = get_logger("weather_api")

app = FastAPI(title="Weather API", version="0.1.0")

_service = WeatherService(provider=MockWeatherProvider())


def get_service() -> WeatherService:
    """Get weather service instance.

    Returns:
        WeatherService instance with MockWeatherProvider.
    """
    return _service


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint.

    Returns:
        Health status message.
    """
    return {"status": "healthy"}


@app.get("/weather/{city}")
async def get_weather(
    city: str,
    service: WeatherService = Depends(get_service),  # noqa: B008
) -> dict[str, object]:
    """Fetch weather data for a specific city.

    Args:
        city: Name of the city to fetch weather data for.
        service: Weather service instance (injected).

    Returns:
        Weather data for the requested city.

    Raises:
        HTTPException: 400 for invalid input, 404 for city not found,
                      502 for provider errors.
    """
    try:
        logger.info("GET /weather/%s", city)
        data = service.get_weather(city)
        return asdict(data)
    except InvalidDataError as e:
        raise HTTPException(400, str(e)) from e
    except CityNotFoundError as e:
        raise HTTPException(404, str(e)) from e
    except WeatherProviderError as e:
        raise HTTPException(502, str(e)) from e


@app.get("/forecast/{city}")
async def get_forecast(
    city: str,
    service: WeatherService = Depends(get_service),  # noqa: B008
) -> dict[str, object]:
    """Fetch forecast data for a specific city.

    Args:
        city: Name of the city to fetch forecast data for.
        service: Weather service instance (injected).

    Returns:
        Forecast data for the requested city.

    Raises:
        HTTPException: 400 for invalid input, 404 for city not found,
                      502 for provider errors.
    """
    try:
        logger.info("GET /forecast/%s", city)
        data = service.get_forecast(city)
        return asdict(data)
    except InvalidDataError as e:
        raise HTTPException(400, str(e)) from e
    except CityNotFoundError as e:
        raise HTTPException(404, str(e)) from e
    except WeatherProviderError as e:
        raise HTTPException(502, str(e)) from e
