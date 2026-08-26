# Enterprise-Grade URL Shortener Microservice

A production-style URL shortening service built with Django REST Framework and SQLAlchemy. It provides JWT-authenticated user accounts, a short-link API with tagging and analytics, and a Redis read-through cache — all backed by SQLAlchemy as the sole data-access layer.

Built as an AmaliTech Training Academy project to demonstrate a clean, layered architecture with Dependency Inversion — views, serializers, services, and repositories each with a single, testable responsibility.

## Contents

- [Features](#features)
- [Tech stack](#tech-stack)
- [Architecture](#architecture)
- [Redis caching](#redis-caching)
- [Project structure](#project-structure)
- [Getting started](#getting-started)
- [Environment variables](#environment-variables)
- [API reference](#api-reference)
- [Interactive API docs](#interactive-api-docs)
- [Running the tests](#running-the-tests)
- [Code quality](#code-quality)
- [Design notes](#design-notes)

## Features

- **JWT authentication** — register, login, logout (with refresh-token blacklisting), and access-token refresh.
- **URL shortening** — generate a unique, collision-safe short code (base62, CSPRNG) for any URL.
- **Tagging** — assign tags to shortened URLs for categorization and filtering.
- **Owner-scoped management** — list, update, and delete only the short links you created; anyone else's return `404`, not `403`, so link IDs can't be probed.
- **Public resolution** — look up the original URL for any short code, no login required.
- **Click analytics** — country breakdown, referrer stats, hourly distribution, time-series data, and recent click history.
- **Top URLs leaderboard** — ranked list of a user's most-clicked links.
- **Redis caching** — read-through cache with write-through invalidation, TTL-based expiry, and graceful fallback to PostgreSQL when Redis is unavailable.
- **Keyset pagination** — cursor-based pagination on the list endpoint for O(1) page navigation and consistent results under concurrent writes.
- **Dynamic filtering** — search, filter by tag, active status, click count range, or creation date.
- **OpenAPI 3 schema** — full interactive documentation via Swagger UI and Redoc, generated from the code (`drf-spectacular`).

## Tech stack

| Layer | Choice |
|---|---|
| Language / runtime | Python 3.12 |
| Framework | Django 6.1, Django REST Framework |
| Auth | `djangorestframework-simplejwt` (JWT, with token blacklisting) |
| ORM (primary) | **SQLAlchemy** — all data access goes through SA models |
| ORM (stubs) | Django models (`managed=False`) — exist only to prevent DROP TABLE |
| Database | PostgreSQL |
| Cache | Redis (`redis`, `django-redis`) |
| Migration | Alembic (SQLAlchemy schema management) |
| API docs | `drf-spectacular` (OpenAPI 3, Swagger UI, Redoc) |
| Server | Uvicorn (ASGI) |
| Testing | pytest, pytest-django, pytest-cov |
| Linting / formatting | ruff, black, mypy, pre-commit |
| Containerization | Docker, Docker Compose |

## Architecture

Each Django app (`apps/users`, `apps/shortener`) follows the same layered structure under `api/`, so once you understand one, you understand both:

```
api/
├── views/          # Thin HTTP layer: parse request, call a service, shape the response
├── serializers/    # Validate input / shape output — no business logic
├── services/       # Business logic, framework-agnostic where practical
├── interfaces/     # Abstract contracts services depend on (Dependency Inversion)
├── repositories/   # SQLAlchemy implementations — the only place that touches the DB
├── cache/          # Redis client wrapper and connection management
├── exceptions/     # Domain errors, translated to HTTP status codes by views
└── urls.py

database/            # SQLAlchemy models and connection management
├── __init__.py      # Re-exports all SA models from subpackages
├── connection.py    # Engine, session factory, Base class
├── shortener/
│   └── models.py    # URLModel, ClickModel, TagModel, URLTagModel
└── users/
    └── models.py    # UserModel (read-only; writes go through Django auth)
```

This keeps the ORM at a single boundary (the repository), lets services be unit-tested with mock repositories instead of a database, and means swapping a data store or generation algorithm later doesn't ripple through the views.

### SQLAlchemy as the primary data layer

All queries, inserts, updates, and deletes go through SQLAlchemy models in `database/`. Django models in `apps/shortener/models.py` are `managed=False` stubs that exist solely to prevent Django from issuing `DROP TABLE` migrations against tables it doesn't own. The `UserModel` is read-only — user creation and authentication always goes through Django's auth system.

The `CachedURLRepository` wraps the SA URL repository, and `CachedAnalyticsRepository` wraps the SA analytics repository. Both add Redis caching transparently. The service layer depends only on `IURLRepository` and `IClickAnalyticsRepository`, so the cache can be toggled on or off without changing any business logic.

## Redis caching

Two decorator repositories wrap the SQLAlchemy data-access layer with Redis caching:

- **`CachedURLRepository`** — wraps `SQLAlchemyURLRepository` with read-through caching for URL entities and write-through invalidation.
- **`CachedAnalyticsRepository`** — wraps `SQLAlchemyClickAnalyticsRepository` with short-TTL caching for expensive aggregation queries.

The service layer depends only on abstract interfaces (`IURLRepository`, `IClickAnalyticsRepository`), so the cache can be toggled on or off without changing any business logic.

### Data flow

```
View → Service → CachedURLRepository → Redis (reads)
                                          ↓ (miss)
                                    SQLAlchemyURLRepository → PostgreSQL

View → Service → CachedAnalyticsRepository → Redis (reads)
                                                  ↓ (miss)
                                        SQLAlchemyClickAnalyticsRepository → PostgreSQL
```

Writes always go to PostgreSQL first, then invalidate the affected cache keys so the next read repopulates with fresh data.

### Cache key scheme

#### URL entity keys

| Key pattern | Stores | TTL |
|---|---|---|
| `url:code:{short_code}` | URL data (with tags) by short code | 10 min |
| `url:id:{pk}` | URL data (with tags) by primary key | 10 min |
| `url:exists:{short_code}` | Existence check result | 5 min |
| `url:list:{owner_id}` | List of URL IDs for an owner | 2 min |
| `url:stats:{pk}` | Aggregate stats (total clicks, countries, referrer) | 30 sec |
| `url:top:{owner_id}:{limit}` | Top URLs leaderboard | 30 sec |
| `url:ts:{pk}:{days}` | Daily click time series | 30 sec |

#### Analytics keys

| Key pattern | Stores | TTL |
|---|---|---|
| `analytics:countries:{pk}:{limit}` | Country breakdown | 30 sec |
| `analytics:referrers:{pk}:{limit}` | Referrer breakdown | 30 sec |
| `analytics:hourly:{pk}` | Hourly click distribution | 30 sec |

### Endpoint behaviour

| Endpoint | Cache action |
|---|---|
| `POST /urls/` | Write DB → invalidate URL entity keys + list; re-invalidate after tag/title writes |
| `GET /urls/mine/` | Read `url:list:{owner_id}`, each URL from `url:id:{pk}` |
| `GET /urls/top/` | Read `url:top:{owner_id}:{limit}` |
| `PATCH /urls/{id}/` | Write DB → invalidate all related URL keys |
| `DELETE /urls/{id}/` | Write DB → invalidate all related URL keys |
| `GET /{short_code}/` | Read `url:code:{short_code}` → record click → invalidate URL entity keys |
| `GET /urls/{id}/analytics/` | Read `url:stats:`, `analytics:countries:`, `analytics:referrers:`, `analytics:hourly:` |
| `GET /urls/{id}/analytics/timeseries/` | Read `url:ts:{pk}:{days}` |

### Cache invalidation on clicks

When a short code is resolved, the analytics repository records the click and atomically increments `click_count` in PostgreSQL. The service then calls `invalidate()` on the URL repository, which evicts `url:code:`, `url:id:`, `url:stats:`, and `url:list:` keys — so the next read always reflects the fresh `click_count`.

### Caching strategies

1. **Read-through** — the repository checks Redis first; on miss it queries PostgreSQL and populates the cache automatically.
2. **Write-through invalidation** — every write deletes the relevant cache keys. The next read repopulates them. This avoids stale reads without write amplification.
3. **Cache-aside (lazy population)** — each repository method explicitly manages `get` / `set` rather than relying on an automatic cache layer.
4. **TTL-based expiry** — entity keys have longer TTLs (5–10 min), analytics keys have short TTLs (30 sec) since they change frequently.
5. **Graceful degradation** — if Redis is unreachable at startup, the factory falls back to plain SA repositories. The API continues to work with zero downtime; only caching is lost.

## Project structure

```
Module6/
├── manage.py
├── requirements.txt
├── pyproject.toml          # ruff / black / mypy / pytest / coverage config
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── alembic/                # SQLAlchemy migrations (Alembic)
│   ├── env.py
│   └── versions/
└── src/
    ├── config/             # settings, root urls, asgi/wsgi entrypoints
    ├── database/           # SQLAlchemy models and connection management
    │   ├── __init__.py
    │   ├── connection.py
    │   ├── shortener/
    │   │   └── models.py
    │   └── users/
    │       └── models.py
    └── apps/
        ├── users/          # accounts + JWT auth
        │   ├── api/
        │   ├── models.py   # Django managed=False stub
        │   └── tests/
        └── shortener/      # URL shortening + resolution + analytics
            ├── api/
            │   ├── cache/       # Redis client wrapper
            │   ├── interfaces/  # repository + generator contracts
            │   ├── repositories/ # SA + cached implementations
            │   ├── services/    # business logic + factory
            │   ├── views/       # HTTP layer
            │   ├── serializers/ # input/output validation
            │   └── exceptions/  # domain errors
            ├── models.py   # Django managed=False stubs
            └── tests/
```

## Getting started

### Prerequisites

- Python 3.12+
- PostgreSQL (running locally, or reachable from wherever the app runs)
- Redis (running locally, or reachable from wherever the app runs)
- Docker + Docker Compose (only if you use the Docker route below)

### 1. Clone and configure

```bash
git clone <this-repo>
cd Module6
cp .env.example .env
# edit .env — at minimum set SECRET_KEY and your PostgreSQL credentials
```

### 2a. Run with Docker (recommended)

```bash
docker compose up --build
```

This runs migrations automatically, then starts the API on **http://localhost:8000**. The container connects to PostgreSQL via `host.docker.internal` (i.e. Postgres runs on your host machine, not in a container) — make sure it's running and `DB_HOST`/`DB_PORT`/credentials in `.env` match. Redis runs inside Docker on port `6380` (mapped from container port `6379`).

### 2b. Run locally without Docker

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

Make sure Redis is running locally on port `6379` (the default). If you use a different port, set `REDIS_URL` in `.env` accordingly.

(`manage.py` adds `src/` to `sys.path` itself, so no `PYTHONPATH` is needed here — only for running `pytest` directly, below.)

Either way, once it's running:

- API base URL: `http://localhost:8000/api/v1/`
- Interactive docs: `http://localhost:8000/api/v1/docs/`

## Environment variables

Set these in `.env` (see `.env.example`):

| Variable | Purpose | Example |
|---|---|---|
| `SECRET_KEY` | Django's cryptographic signing key | `django-insecure-...` (generate your own for anything beyond local dev) |
| `DEBUG` | Django debug mode | `True` / `False` |
| `ALLOWED_HOSTS` | Comma-separated allowed `Host` headers | `127.0.0.1,localhost` |
| `DB_ENGINE` | Django database backend | `django.db.backends.postgresql` |
| `DB_NAME` | Database name | `url_shortener` |
| `DB_USER` | Database user | `postgres` |
| `DB_PASSWORD` | Database password | — |
| `DB_HOST` | Database host | `127.0.0.1` (or `host.docker.internal` under Docker) |
| `DB_PORT` | Database port | `5432` |
| `REDIS_URL` | Redis connection URL | `redis://127.0.0.1:6379/0` (or `redis://redis:6379/0` inside Docker) |

## API reference

All routes are versioned under `/api/v1/`. Endpoints marked require `Authorization: Bearer <access-token>`.

### Auth (`apps/users`)

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/auth/register/` | Create a new user account |
| `POST` | `/api/v1/auth/login/` | Authenticate, receive `access` + `refresh` tokens |
| `POST` | `/api/v1/auth/logout/` | Blacklist a refresh token |
| `POST` | `/api/v1/auth/token/refresh/` | Exchange a refresh token for a new access token |

### URLs (`apps/shortener`)

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/urls/` | Shorten a URL with optional title, tags, and expiry |
| `GET` | `/api/v1/urls/mine/` | List the caller's own shortened URLs (keyset pagination) |
| `GET` | `/api/v1/urls/top/` | Leaderboard of the caller's most-clicked URLs |
| `PATCH` | `/api/v1/urls/{id}/` | Update one of the caller's URLs |
| `DELETE` | `/api/v1/urls/{id}/` | Delete one of the caller's URLs |
| `GET` | `/api/v1/urls/{id}/analytics/` | Click analytics (countries, referrers, hourly distribution) |
| `GET` | `/api/v1/urls/{id}/analytics/timeseries/` | Daily click counts over the last N days |
| `GET` | `/api/v1/{short_code}/` | Look up the original URL — public, no auth, records a click |

### Sample requests & responses

**Create a short URL** (with tags)

```
POST /api/v1/urls/
Content-Type: application/json
Authorization: Bearer <access-token>

{
  "original_url": "https://github.com/AmaliTech-Training-Academy/BackEnd-Labs",
  "title": "BackEnd Labs Repo",
  "tags": ["github", "backend"]
}
```
```json
{
  "id": 10,
  "original_url": "https://github.com/AmaliTech-Training-Academy/BackEnd-Labs",
  "short_code": "VGQVRJx",
  "short_url": "http://localhost:8000/api/v1/VGQVRJx/",
  "title": "BackEnd Labs Repo",
  "tags": ["github", "backend"],
  "click_count": 0,
  "is_active": true,
  "expires_at": null,
  "last_accessed_at": null,
  "created_at": "2026-08-26T22:46:29.583176+02:00",
  "updated_at": "2026-08-26T22:46:29.621860+02:00"
}
```

**List my URLs** (with keyset pagination)

```
GET /api/v1/urls/mine/?limit=20
Authorization: Bearer <access-token>
```
```json
{
  "results": [
    {
      "id": 10,
      "original_url": "https://github.com/AmaliTech-Training-Academy/BackEnd-Labs",
      "short_code": "VGQVRJx",
      "short_url": "http://localhost:8000/api/v1/VGQVRJx/",
      "title": "BackEnd Labs Repo",
      "tags": ["github", "backend"],
      "click_count": 5,
      "is_active": true,
      "expires_at": null,
      "last_accessed_at": "2026-08-26T22:50:00.000000+02:00",
      "created_at": "2026-08-26T22:46:29.583176+02:00",
      "updated_at": "2026-08-26T22:46:29.621860+02:00"
    }
  ],
  "next_cursor": "eyJpZCI6IDEwLCAiY3JlYXRlZF9hdCI6ICIyMDI2LTA4LTI2VDIyOjQ2OjI5LjU4MzE3NiswMjowMCJ9",
  "has_more": false
}
```

Query parameters for filtering:

| Param | Type | Description |
|---|---|---|
| `search` | string | Search in short_code, title, or original_url |
| `is_active` | boolean | Filter by active status |
| `tag` | string | Filter by tag name |
| `created_after` | datetime | Only URLs created after this datetime |
| `created_before` | datetime | Only URLs created before this datetime |
| `min_clicks` | int | Minimum click count |
| `max_clicks` | int | Maximum click count |
| `ordering` | string | Sort by: `created_at`, `-created_at`, `click_count`, `-click_count`, `title`, `-title` |
| `cursor` | string | Keyset pagination cursor from a previous response |
| `limit` | int | Results per page (1–100, default 20) |

**Resolve a short code** (public — records a click)

```
GET /api/v1/VGQVRJx/
```
```json
{
  "original_url": "https://github.com/AmaliTech-Training-Academy/BackEnd-Labs"
}
```

**Update one of my URLs**

```
PATCH /api/v1/urls/10/
Content-Type: application/json
Authorization: Bearer <access-token>

{
  "original_url": "https://github.com/AmaliTech-Training-Academy"
}
```
```json
{
  "id": 10,
  "original_url": "https://github.com/AmaliTech-Training-Academy",
  "short_code": "VGQVRJx",
  "short_url": "http://localhost:8000/api/v1/VGQVRJx/",
  "title": "BackEnd Labs Repo",
  "tags": ["github", "backend"],
  "click_count": 5,
  "is_active": true,
  "expires_at": null,
  "last_accessed_at": "2026-08-26T22:50:00.000000+02:00",
  "created_at": "2026-08-26T22:46:29.583176+02:00",
  "updated_at": "2026-08-26T22:55:00.000000+02:00"
}
```

**Delete one of my URLs**

```
DELETE /api/v1/urls/10/
Authorization: Bearer <access-token>
```
```json
{
  "message": "URL deleted successfully."
}
```

**Click analytics**

```
GET /api/v1/urls/10/analytics/
Authorization: Bearer <access-token>
```
```json
{
  "url_id": 10,
  "short_code": "VGQVRJx",
  "stats": {
    "total_clicks": 5,
    "unique_countries": 2,
    "top_referer": "https://github.com",
    "last_clicked_at": "2026-08-26T22:50:00.000000+02:00"
  },
  "countries": [
    {"country": "US", "clicks": 3, "percentage": 60.0},
    {"country": "GH", "clicks": 2, "percentage": 40.0}
  ],
  "referrers": [
    {"referer": "https://github.com", "clicks": 4, "percentage": 80.0}
  ],
  "hourly_distribution": [
    {"hour": 0, "clicks": 0},
    {"hour": 1, "clicks": 0},
    "...",
    {"hour": 22, "clicks": 5},
    {"hour": 23, "clicks": 0}
  ],
  "recent_clicks": [
    {
      "id": 5,
      "ip_address": "172.22.0.1",
      "country": "US",
      "referer": "https://github.com",
      "clicked_at": "2026-08-26T22:50:00.000000+02:00"
    }
  ]
}
```

**Error responses** — a missing/invalid token:

```json
{ "detail": "Authentication credentials were not provided." }
```
*(`401 Unauthorized`)*

...an unknown short code, or a URL that exists but belongs to someone else:

```json
{ "detail": "URL with short code 'doesnotexist' was not found." }
```
*(`404 Not Found`)*

## Interactive API docs

Once the server is running:

- **Swagger UI** — `http://localhost:8000/api/v1/docs/` — click "Authorize" and paste an access token to try protected endpoints.
- **Redoc** — `http://localhost:8000/api/v1/redoc/`
- **Raw OpenAPI schema** — `http://localhost:8000/api/v1/schema/`

## Running the tests

Test tooling (`pytest`, `pytest-django`, `pytest-cov`) isn't part of the runtime `requirements.txt` — install it separately, once:

```bash
pip install -r requirements-dev.txt
```

Then, from the project root:

```bash
pytest --cov=apps --cov-report=term-missing
```

(`pythonpath` and `DJANGO_SETTINGS_MODULE` are already configured in `pyproject.toml`, so no environment variables are needed — plain `pytest` works too.)

## Code quality

This project uses `pre-commit` to run formatting/linting/type-checking before every commit:

```bash
pip install pre-commit
pre-commit install
```

Hooks: `black` (format), `ruff` (lint + format), `mypy` (type-check), trailing whitespace. Run them all manually with:

```bash
pre-commit run --all-files
```

## Design notes

A couple of deliberate trade-offs worth knowing about:

- **SQLAlchemy as the sole data layer.** Django models are minimal `managed=False` stubs. All business logic, queries, and serialization go through SQLAlchemy models. This was chosen because SA gives more control over session management, eager loading (`selectinload`), and query composition — and avoids Django ORM's implicit lazy-loading pitfalls across session boundaries.
- **`GET /api/v1/{short_code}/` returns `200` with `{"original_url": ...}` rather than a real `302` redirect.** This makes the endpoint testable from any client — including Swagger UI's "Try it out," which can't meaningfully follow a redirect to a cross-origin target. If this service needs to work as actual clickable short links later, this endpoint is the one to change back to a redirect.
- **Ownership failures return `404`, not `403`.** Trying to update or delete a URL you don't own is indistinguishable from that URL not existing at all — this avoids leaking which IDs belong to other users.
- **`POST /api/v1/urls/` requires authentication**, so every created URL has a real owner (no anonymous links).
- **Alembic for SA migrations.** Schema changes are managed through Alembic rather than Django's migration framework, keeping the two ORMs cleanly separated.
