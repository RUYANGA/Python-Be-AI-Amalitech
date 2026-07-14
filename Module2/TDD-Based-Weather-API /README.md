# Weather API Service

A TDD-based weather API service built with FastAPI, SOLID principles, and dependency injection.

## TDD Approach: Red-Green-Refactor

This project follows a strict **Test-Driven Development** workflow. Every feature was built using the Red-Green-Refactor cycle:

### Red - Write a Failing Test

Before writing any implementation code, a test is written that defines the expected behavior. The test **must fail** initially, confirming the feature doesn't exist yet.

```python
# Example: First test for WeatherData model (commit: 9eb1f45)
def test_create_weather_data() -> None:
    data = WeatherData(25.5, 60, "Sunny", "Kampala")
    assert data.temperature == 25.5
```

### Green - Write Minimum Code to Pass

Write the simplest code that makes the test pass. No extra features, no premature optimization.

```python
# Example: Minimal WeatherData implementation (commit: db14ba8)
@dataclass
class WeatherData:
    temperature: float
    humidity: int
    description: str
    city: str = field(default="")
```

### Refactor - Improve the Code

Clean up the code while keeping all tests green. Apply SOLID principles, extract abstractions, and improve readability.

```python
# Example: Extract WeatherProvider ABC for dependency inversion (commit: 26d5464)
class WeatherProvider(ABC):
    @abstractmethod
    def get_weather(self, city: str) -> WeatherData: ...
```

### TDD Commit History

The git history demonstrates the TDD cycle across the project:

| Commit | Phase | Description |
|--------|-------|-------------|
| `9eb1f45` | Red | Failing tests for WeatherData model |
| `db14ba8` | Green | Implement WeatherData dataclass |
| `f01a644` | Green | Add custom exception hierarchy |
| `26d5464` | Refactor | Extract WeatherProvider ABC interface |
| `cb22aea` | Green | Implement MockWeatherProvider |
| `11da007` | Red | Failing tests for WeatherService |
| `88456a6` | Green | Implement WeatherService with DI |
| `22c97e6` | Green | Add FastAPI endpoints |

## Project Structure

```
app/
├── __init__.py          # Package marker
├── models.py            # WeatherData dataclass
├── exceptions.py        # Custom exception hierarchy
├── providers.py         # WeatherProvider abstract interface
├── mock_provider.py     # Mock provider with sample city data
├── service.py           # WeatherService with validation & DI
├── logger.py            # Structured logging configuration
└── main.py              # FastAPI application & endpoints

tests/
├── __init__.py          # Package marker
├── conftest.py          # Shared pytest fixtures
├── test_models.py       # Model unit tests
├── test_exceptions.py   # Exception hierarchy tests
├── test_provider.py     # Provider unit tests
├── test_service.py      # Service unit tests (success, errors, mocking)
├── test_logger.py       # Logger unit tests
└── test_api.py          # API endpoint integration tests
```

## Installation

```bash
git clone <repository-url>
cd Module2/TDD-Based-Weather-API

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Run the Server

```bash
uvicorn app.main:app --reload
```

Server starts at `http://127.0.0.1:8000`. Interactive docs available at `/docs`.

## API Endpoints

| Method | Endpoint            | Description              | Status Codes             |
|--------|---------------------|--------------------------|--------------------------|
| GET    | `/health`           | Health check             | 200                      |
| GET    | `/weather/{city}`   | Get weather for a city   | 200, 400, 404, 502       |
| GET    | `/forecast/{city}`  | Get forecast for a city  | 200, 400, 404, 502       |

### Example Requests

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/weather/Kigali
curl http://127.0.0.1:8000/forecast/Kigali
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
pytest -v

# Run with coverage
pytest --cov=app --cov-report=term-missing

# Format code
black app/ tests/

# Lint code
ruff check app/ tests/

# Type check
mypy --strict app/
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
├── InvalidDataError       # Validation failed
└── InvalidAPIKeyError     # API key missing or invalid
```

### Validation Rules

- Temperature must be >= -273.15°C (absolute zero)
- Humidity must be between 0 and 100
- Description must not be empty
- City name must not be empty or whitespace

## Verification

- [x] 68 tests pass
- [x] 100% code coverage
- [x] `@pytest.mark.parametrize` for data-driven tests
- [x] Black formatting
- [x] Ruff linting
- [x] MyPy strict mode
- [x] Pre-commit hooks configured
- [x] `.gitignore` configured
- [x] `requirements.txt` generated
