# Weather API Service

A TDD-based weather API service built with FastAPI, SOLID principles, and dependency injection.

## Project Structure

```
app/
├── models.py          # WeatherData dataclass
├── exceptions.py      # Custom exceptions
├── providers.py       # WeatherProvider interface
├── mock_provider.py   # Mock provider with sample data
├── service.py         # WeatherService with DI
└── main.py            # FastAPI application

tests/
├── conftest.py        # Shared fixtures
├── test_models.py     # Model tests
├── test_provider.py   # Provider tests
├── test_service.py    # Service tests
└── test_api.py        # API endpoint tests
```

## Installation

```bash
git clone <repository-url>
cd weather-api-service
poetry install
poetry shell
```

## Run the Server

```bash
uvicorn app.main:app --reload
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/weather/{city}` | Get weather data |

### Example Response

```json
{
  "city": "Kigali",
  "temperature": 22.5,
  "humidity": 65,
  "description": "Partly Cloudy"
}
```

## Commands

```bash
# Tests
pytest -v

# Coverage
pytest --cov=app --cov-report=term-missing

# Format
black app/ tests/

# Lint
ruff check app/ tests/

# Type check
mypy --strict app/
```

## Architecture

### Dependency Injection

```python
# Swap providers easily
from app.service import WeatherService
from app.mock_provider import MockWeatherProvider

provider = MockWeatherProvider()
service = WeatherService(provider=provider)

# For real API:
# provider = RealWeatherProvider(api_key="your-key")
# service = WeatherService(provider=provider)
```

### Custom Exceptions

```
WeatherServiceError
├── CityNotFoundError
├── WeatherProviderError
└── InvalidDataError
```

## Verification

- [x] 27 tests pass
- [x] 100% coverage
- [x] Black formatting
- [x] Ruff linting
- [x] MyPy strict mode
