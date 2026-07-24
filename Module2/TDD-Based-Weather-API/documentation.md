# Weather API Service — Technical Documentation

---

## Table of Contents

1. [Getting Started Guide](#1-getting-started-guide)
2. [API Reference](#2-api-reference)
3. [Troubleshooting](#3-troubleshooting)
4. [Prompt History](#4-prompt-history)
5. [Reflection](#5-reflection)

---

## 1. Getting Started Guide

### What Is the Weather API?

The Weather API is a lightweight web service that provides current weather data for cities across Africa. You can query it using simple HTTP requests and get back structured weather information including temperature, humidity, and a short description.

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)
- A terminal or command prompt

### Step 1 — Clone the Repository

```bash
git clone <repository-url>
cd Module2/TDD-Based-Weather-API
```

### Step 2 — Create a Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
```

### Step 3 — Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4 — Start the Server

```bash
uvicorn app.main:app --reload
```

The server starts at **http://127.0.0.1:8000**. You will see output confirming the server is running.

### Step 5 — Test It

Open your browser and go to:

- **http://127.0.0.1:8000/docs** — Interactive API documentation (Swagger UI)
- **http://127.0.0.1:8000/health** — Returns `{"status": "healthy"}` if the server is up

### Step 6 — Fetch Weather Data

Use your browser, curl, or any HTTP client:

```bash
curl http://127.0.0.1:8000/weather/Kigali
```

You will receive a JSON response like:

```json
{
  "temperature": 22.5,
  "humidity": 65,
  "description": "Partly Cloudy",
  "city": "Kigali"
}
```

### Available Cities

| City     | Temperature (°C) | Humidity (%) | Description     |
|----------|------------------|--------------|-----------------|
| Kigali   | 22.5             | 65           | Partly Cloudy   |
| Kampala  | 28.0             | 75           | Sunny           |
| Nairobi  | 24.0             | 70           | Cloudy          |
| Lagos    | 32.0             | 85           | Humid           |

### Basic Usage Tips

- City names are **case-insensitive** — `kigali`, `KIGALI`, and `Kigali` all work.
- City names with spaces are not currently supported in URL paths.
- Use the `/forecast/{city}` endpoint for forecast data (returns the same structure as `/weather/{city}`).

---

## 2. API Reference

### Base URL

```
http://127.0.0.1:8000
```

### Endpoints

#### GET `/health`

Check if the service is running.

**Response**

| Status | Body                                    |
|--------|-----------------------------------------|
| 200    | `{"status": "healthy"}`                 |

**Example**

```bash
curl http://127.0.0.1:8000/health
```

---

#### GET `/weather/{city}`

Fetch current weather data for a specific city.

**Path Parameters**

| Parameter | Type   | Required | Description            |
|-----------|--------|----------|------------------------|
| `city`    | string | Yes      | Name of the city       |

**Response — Success (200)**

```json
{
  "temperature": 22.5,
  "humidity": 65,
  "description": "Partly Cloudy",
  "city": "Kigali"
}
```

| Field         | Type   | Description                                  |
|---------------|--------|----------------------------------------------|
| `temperature` | float  | Current temperature in Celsius               |
| `humidity`    | int    | Humidity percentage (0–100)                  |
| `description` | string | Short weather description (e.g. "Sunny")     |
| `city`        | string | Canonical city name                          |

**Error Responses**

| Status | Meaning         | Example Body                                      |
|--------|-----------------|---------------------------------------------------|
| 400    | Invalid input   | `{"detail": "City name cannot be empty"}`         |
| 404    | City not found  | `{"detail": "City not found: UnknownCity"}`       |
| 502    | Provider error  | `{"detail": "Provider failed for Kigali"}`        |

**Example**

```bash
curl http://127.0.0.1:8000/weather/Nairobi
```

---

#### GET `/forecast/{city}`

Fetch forecast data for a specific city. Returns the same data structure as `/weather/{city}`.

**Path Parameters**

| Parameter | Type   | Required | Description            |
|-----------|--------|----------|------------------------|
| `city`    | string | Yes      | Name of the city       |

**Response**

Same as `/weather/{city}`.

**Error Responses**

Same as `/weather/{city}`.

**Example**

```bash
curl http://127.0.0.1:8000/forecast/Lagos
```

---

### Validation Rules

The service validates all responses before returning them:

- **Temperature** must be ≥ −273.15 °C (absolute zero).
- **Humidity** must be between 0 and 100 inclusive.
- **Description** must not be empty.
- **City name** must not be empty or whitespace-only.

If any rule is violated, a `400 Bad Request` is returned.

---

## 3. Troubleshooting

### Server won't start

**Symptom:** `uvicorn` command fails or port is already in use.

**Fix:**

1. Make sure your virtual environment is activated.
2. Check if another process is using port 8000:
   ```bash
   lsof -i :8000
   ```
3. Kill the conflicting process or use a different port:
   ```bash
   uvicorn app.main:app --reload --port 8080
   ```

---

### "City not found" for a valid city

**Symptom:** Requesting `/weather/Kigali` returns `404`.

**Fix:**

- The mock provider only knows four cities: Kigali, Kampala, Nairobi, and Lagos.
- Check your spelling and capitalisation (though the service is case-insensitive).
- If you need more cities, you would need to extend `MOCK_DATA` in `app/mock_provider.py` or integrate a real weather API provider.

---

### Empty city name returns 400

**Symptom:** Requesting `/weather/` or `/weather/ ` returns `{"detail": "City name cannot be empty"}`.

**Fix:**

- Ensure the city name is non-empty in the URL path.
- URL-encode spaces if necessary, though the API currently does not support multi-word city names in paths.

---

### Import errors when running tests

**Symptom:** `ModuleNotFoundError: No module named 'app'`.

**Fix:**

- Run tests from the project root directory (`Module2/TDD-Based-Weather-API/`).
- Make sure the virtual environment is activated.
- Verify all dependencies are installed:
  ```bash
  pip install -r requirements.txt
  ```

---

### Tests fail with type errors

**Symptom:** MyPy or test suite reports type mismatches.

**Fix:**

- Run the formatter and linter first:
  ```bash
  black app/ tests/
  ruff check app/ tests/
  ```
- Then run type checking:
  ```bash
  mypy --strict app/
  ```
- Fix any reported issues before running the test suite again.

---

### Logging not visible

**Symptom:** Server runs but no log output appears in the terminal.

**Fix:**

- Logs are written to a structured logger, not stdout by default.
- Check the logging configuration in `app/logger.py`.
- For development, you may need to adjust the log level or handler to see output in the console.

---

## 4. Prompt History

The following prompts were used iteratively to generate and refine this documentation:

### Prompt 1 — Initial Structure

> "Act as a technical writer. I have a FastAPI weather API project. Create a documentation file with a Getting Started guide, API reference, and Troubleshooting section. The project has endpoints: GET /health, GET /weather/{city}, GET /forecast/{city}. It returns JSON with temperature, humidity, description, and city fields. Start with a rough draft."

**Result:** Produced a generic template with placeholder content. Needed specific project details.

---

### Prompt 2 — Inject Project Context

> "Here is the README for the project. Use the exact endpoint paths, response structures, status codes, and available cities from it. Do not invent data. Getting Started guide should be for someone who has never run the project. API reference should list every field in the response. Troubleshooting should cover common setup and usage issues."

**Result:** Much more accurate. Response structures now matched the actual code. Troubleshooting section needed more depth.

---

### Prompt 3 — Refine Troubleshooting

> "Expand the Troubleshooting section. Add entries for: server port conflicts, city-not-found errors, import errors when running tests, type-checking failures, and missing log output. Each entry should have a Symptom and a Fix. Keep language simple and actionable."

**Result:** Troubleshooting section became more practical. Tone was still slightly formal.

---

### Prompt 4 — Tone and Style Pass

> "Rewrite the entire document to use a consistent professional tone: clear, direct, and free of jargon. All main headings should be H2, sub-headings H3. Tables should align consistently. Ensure every code example is runnable. Remove any invented content that does not come from the actual project files."

**Result:** Final polish. Document became consistent in formatting and tone. All content verified against source code.

---

### Prompt 5 — Add Prompt History and Reflection

> "Append a Prompt History section listing each prompt used and what changed after each one. Then add a Reflection section (200 words or fewer) about the hardest part of the task and how iterative prompting improved quality."

**Result:** Completed the deliverable set.

---

## 5. Reflection

**What was the hardest part?**

The hardest part was fact-checking the AI's output against the actual project files. The AI would confidently generate plausible response structures, example data, and error messages that looked correct but did not match the source code. For example, it initially suggested a `"status"` field in the weather response that does not exist in the `WeatherData` model. Every section had to be cross-referenced against `app/main.py`, `app/models.py`, and `app/mock_provider.py` to ensure accuracy.

**How did iterative prompting change the quality?**

Iterative prompting was essential. The first draft was a generic template with no project-specific detail. Each subsequent prompt injected more context — exact field names, real error messages, actual city data — which progressively anchored the output to reality. The tone and style pass (Prompt 4) unified the document's voice across all sections. Without iteration, the documentation would have been plausible but technically wrong in several places.

---

*Document generated for the Weather API Service project.*
