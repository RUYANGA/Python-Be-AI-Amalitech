# Enterprise-Grade URL Shortener Microservice

A production-style URL shortening service built with Django REST Framework. It provides JWT-authenticated user accounts and a short-link API: create, list, update, and delete your own links, and resolve any short code back to its original URL.

Built as an AmaliTech Training Academy project to demonstrate a clean, layered Django/DRF architecture — not just "make the endpoint work," but views, serializers, services, and repositories each with a single, testable responsibility.

## Contents

- [Features](#features)
- [Tech stack](#tech-stack)
- [Architecture](#architecture)
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
- **Owner-scoped management** — list, update, and delete only the short links you created; anyone else's return `404`, not `403`, so link IDs can't be probed.
- **Public resolution** — look up the original URL for any short code, no login required.
- **OpenAPI 3 schema** — full interactive documentation via Swagger UI and Redoc, generated from the code (`drf-spectacular`).
- **100% test coverage** on both apps, enforced via `pytest-cov`.

## Tech stack

| Layer | Choice |
|---|---|
| Language / runtime | Python 3.12 |
| Framework | Django 6.1, Django REST Framework |
| Auth | `djangorestframework-simplejwt` (JWT, with token blacklisting) |
| Database | PostgreSQL |
| API docs | `drf-spectacular` (OpenAPI 3, Swagger UI, Redoc) |
| Server | Uvicorn (ASGI) |
| Testing | pytest, pytest-django, pytest-cov |
| Linting / formatting | ruff, black, mypy, pre-commit |
| Containerization | Docker, Docker Compose |

## Architecture

Each Django app (`apps/users`, `apps/shortener`) follows the same layered structure under `api/`, so once you understand one, you understand both:

```
api/
├── views/         # Thin HTTP layer: parse request, call a service, shape the response
├── serializers/    # Validate input / shape output — no business logic
├── services/       # Business logic, framework-agnostic where practical
├── interfaces/      # Abstract contracts services depend on (Dependency Inversion)
├── repositories/    # Only place that touches the Django ORM directly
├── exceptions/      # Domain errors, translated to HTTP status codes by views
└── urls.py
```

This keeps the ORM at a single boundary (the repository), lets services be unit-tested with mock repositories instead of a database, and means swapping a data store or generation algorithm later doesn't ripple through the views.

`apps/shortener`'s ownership check lives in the **service** layer (`update_owned` / `delete_owned`), not the view — so "is this actually yours?" is enforced in exactly one place, and it deliberately raises the same "not found" error for both "doesn't exist" and "exists but isn't yours," so a caller can't use the API to enumerate other users' link IDs.

## Project structure

```
Module5/
├── manage.py
├── requirements.txt
├── pyproject.toml          # ruff / black / mypy / pytest / coverage config
├── docker-compose.yml
├── Dockerfile
├── .env.example
└── src/
    ├── config/             # settings, root urls, asgi/wsgi entrypoints
    └── apps/
        ├── users/          # accounts + JWT auth
        │   ├── api/
        │   ├── models.py
        │   ├── admin.py
        │   └── tests/
        └── shortener/      # URL shortening + resolution
            ├── api/
            ├── models.py
            ├── admin.py
            └── tests/
```

## Getting started

### Prerequisites

- Python 3.12+
- PostgreSQL (running locally, or reachable from wherever the app runs)
- Docker + Docker Compose (only if you use the Docker route below)

### 1. Clone and configure

```bash
git clone <this-repo>
cd Module5
cp .env.example .env
# edit .env — at minimum set SECRET_KEY and your PostgreSQL credentials
```

### 2a. Run with Docker (recommended)

```bash
docker compose up --build
```

This runs migrations automatically, then starts the API on **http://localhost:8000**. The container connects to PostgreSQL via `host.docker.internal` (i.e. Postgres runs on your host machine, not in a container) — make sure it's running and `DB_HOST`/`DB_PORT`/credentials in `.env` match.

### 2b. Run locally without Docker

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser   # optional, for /admin/
python manage.py runserver 0.0.0.0:8000
```

(`manage.py` adds `src/` to `sys.path` itself, so no `PYTHONPATH` is needed here — only for running `pytest` directly, below.)

Either way, once it's running:

- API base URL: `http://localhost:8000/api/v1/`
- Interactive docs: `http://localhost:8000/api/v1/docs/`
- Admin site: `http://localhost:8000/admin/`

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

## API reference

All routes are versioned under `/api/v1/`. Endpoints marked 🔒 require `Authorization: Bearer <access-token>`.

### Auth (`apps/users`)

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/auth/register/` | Create a new user account |
| `POST` | `/api/v1/auth/login/` | Authenticate, receive `access` + `refresh` tokens |
| `POST` | `/api/v1/auth/logout/` 🔒 | Blacklist a refresh token |
| `POST` | `/api/v1/auth/token/refresh/` | Exchange a refresh token for a new access token |

### URLs (`apps/shortener`)

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/urls/` 🔒 | Shorten a URL (owned by the caller) |
| `GET` | `/api/v1/urls/mine/` 🔒 | List the caller's own shortened URLs |
| `PATCH` | `/api/v1/urls/{id}/` 🔒 | Update one of the caller's URLs — `404` if it isn't theirs |
| `DELETE` | `/api/v1/urls/{id}/` 🔒 | Delete one of the caller's URLs — `404` if it isn't theirs |
| `GET` | `/api/v1/{short_code}/` | Look up the original URL for a short code — public, no auth |

### Sample requests & responses

**Register**

```
POST /api/v1/auth/register/
Content-Type: application/json

{
  "username": "jane_doe",
  "first_name": "Jane",
  "last_name": "Doe",
  "email": "jane@example.com",
  "password": "StrongPass123"
}
```
```json
{
  "message": "User registered successfully.",
  "user": {
    "id": 6,
    "username": "jane_doe",
    "first_name": "Jane",
    "last_name": "Doe",
    "email": "jane@example.com"
  }
}
```

**Login**

```
POST /api/v1/auth/login/
Content-Type: application/json

{
  "username": "jane_doe",
  "password": "StrongPass123"
}
```
```json
{
  "message": "Login successful.",
  "user": {
    "id": 6,
    "username": "jane_doe",
    "first_name": "Jane",
    "last_name": "Doe",
    "email": "jane@example.com"
  },
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Create a short URL** 🔒

```
POST /api/v1/urls/
Content-Type: application/json
Authorization: Bearer <access-token>

{
  "original_url": "https://github.com/AmaliTech-Training-Academy/BackEnd-Labs"
}
```
```json
{
  "id": 14,
  "original_url": "https://github.com/AmaliTech-Training-Academy/BackEnd-Labs",
  "short_code": "8Sy6Xqy",
  "short_url": "http://127.0.0.1:8000/api/v1/8Sy6Xqy/",
  "created_at": "2026-08-09T19:45:51.236693+02:00"
}
```

**List my URLs** 🔒

```
GET /api/v1/urls/mine/
Authorization: Bearer <access-token>
```
```json
[
  {
    "id": 14,
    "original_url": "https://github.com/AmaliTech-Training-Academy/BackEnd-Labs",
    "short_code": "8Sy6Xqy",
    "short_url": "http://127.0.0.1:8000/api/v1/8Sy6Xqy/",
    "created_at": "2026-08-09T19:45:51.236693+02:00"
  }
]
```

**Resolve a short code** (public — no `Authorization` header needed)

```
GET /api/v1/8Sy6Xqy/
```
```json
{
  "original_url": "https://github.com/AmaliTech-Training-Academy/BackEnd-Labs"
}
```

**Update one of my URLs** 🔒

```
PATCH /api/v1/urls/14/
Content-Type: application/json
Authorization: Bearer <access-token>

{
  "original_url": "https://github.com/AmaliTech-Training-Academy"
}
```
```json
{
  "id": 14,
  "original_url": "https://github.com/AmaliTech-Training-Academy",
  "short_code": "8Sy6Xqy",
  "short_url": "http://127.0.0.1:8000/api/v1/8Sy6Xqy/",
  "created_at": "2026-08-09T19:45:51.236693+02:00"
}
```

**Delete one of my URLs** 🔒

```
DELETE /api/v1/urls/14/
Authorization: Bearer <access-token>
```
```json
{
  "message": "URL deleted successfully."
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

```bash
export PYTHONPATH=src
export DJANGO_SETTINGS_MODULE=config.settings
python -m pytest src/apps --cov=apps --cov-report=term-missing
```

Sample output:

```
.......................................................................  [100%]

Name                                              Stmts   Miss  Cover
---------------------------------------------------------------------
...
---------------------------------------------------------------------
TOTAL                                               468      0   100%
71 passed in 39.66s
```

## Code quality

This project uses `pre-commit` to run formatting/linting/type-checking before every commit:

```bash
pip install pre-commit
pre-commit install
```

Hooks: `black` (format), `ruff` (lint), `mypy` (type-check). Run them all manually with:

```bash
pre-commit run --all-files
```

## Design notes

A couple of deliberate trade-offs worth knowing about:

- **`GET /api/v1/{short_code}/` returns `200` with `{"original_url": ...}` rather than a real `302` redirect.** This makes the endpoint testable from any client — including Swagger UI's "Try it out," which can't meaningfully follow a redirect to a cross-origin target (the browser's `fetch()` follows the `302` and then gets CORS-blocked by the destination site). The trade-off: a real browser hitting a short link sees this JSON instead of landing on the target page. If this service needs to work as actual clickable short links later, this endpoint is the one to change back to a redirect.
- **Ownership failures return `404`, not `403`.** Trying to update or delete a URL you don't own is indistinguishable from that URL not existing at all — this avoids leaking which IDs belong to other users.
- **`POST /api/v1/urls/` requires authentication**, so every created URL has a real owner (no anonymous links).
