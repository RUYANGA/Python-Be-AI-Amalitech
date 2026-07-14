# Weather API Service

A TDD-based weather API service built with FastAPI, SOLID principles, and dependency injection.

## Project Structure

```
app/
├── __init__.py          # Package marker
├── models.py            # WeatherData dataclass
├── exceptions.py        # Custom exception hierarchy
├── providers.py         # WeatherProvider abstract interface
├── mock_provider.py     # Mock provider with sample city data
├── service.py           # WeatherService with validation & DI
└── main.py              # FastAPI application & endpoints

tests/
├── __init__.py          # Package marker
├── conftest.py          # Shared pytest fixtures
├── test_models.py       # Model unit tests
├── test_provider.py     # Provider unit tests
├── test_service.py      # Service unit tests (success, errors, mocking)
└── test_api.py          # API endpoint integration tests
```

## Installation

```bash
git clone <repository-url>
cd Module2/TDD-Based-Weather-API
poetry install
poetry shell
```

## Run the Server

```bash
poetry run uvicorn app.main:app --reload
```

Server starts at `http://127.0.0.1:8000`. Interactive docs available at `/docs`.

## API Endpoints

| Method | Endpoint          | Description              | Status Codes             |
|--------|-------------------|--------------------------|--------------------------|
| GET    | `/health`         | Health check             | 200                      |
| GET    | `/weather/{city}` | Get weather for a city   | 200, 400, 404, 502       |

### Example Requests

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/weather/Kigali
curl http://127.0.0.1:8000/weather/kigali    # case-insensitive
```

### Example Response

```json
{
  "temperature": 22.5,
  "humidity": 65,
  "description": "Partly Cloudy",
  "city": "Kigali"
}
```

### Error Responses

```json
// 404 - City not found
{"detail": "City not found: UnknownCity"}

// 400 - Invalid data
{"detail": "City name cannot be empty"}

// 502 - Provider failure
{"detail": "Provider failed for Kigali"}
```

### Available Cities

| City     | Temp (°C) | Humidity (%) | Description     |
|----------|-----------|--------------|-----------------|
| Kigali   | 22.5      | 65           | Partly Cloudy   |
| Kampala  | 28.0      | 75           | Sunny           |
| Nairobi  | 24.0      | 70           | Cloudy          |
| Lagos    | 32.0      | 85           | Humid           |

## Commands

```bash
# Run all tests
poetry run pytest -v

# Run with coverage
poetry run pytest --cov=app --cov-report=term-missing

# Format code
poetry run black app/ tests/

# Lint code
poetry run ruff check app/ tests/

# Type check
poetry run mypy --strict app/
```

## Architecture

### Dependency Injection

```python
from app.service import WeatherService
from app.mock_provider import MockWeatherProvider

provider = MockWeatherProvider()
service = WeatherService(provider=provider)

# Swap to a real provider:
# provider = RealWeatherProvider(api_key="your-key")
# service = WeatherService(provider=provider)
```

### Custom Exceptions

```
WeatherServiceError
├── CityNotFoundError      # City not in provider data
├── WeatherProviderError   # Provider call failed
└── InvalidDataError       # Validation failed
```

### Validation Rules

- Temperature must be >= -273.15°C (absolute zero)
- Humidity must be between 0 and 100
- Description must not be empty
- City name must not be empty or whitespace

## Verification

- [x] 27 tests pass
- [x] 100% code coverage
- [x] Black formatting
- [x] Ruff linting
- [x] MyPy strict mode
