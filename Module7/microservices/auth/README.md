# Auth Service

Owns user identity for the URL shortener microservices split. Issues and
verifies JWTs — every other service treats it as the single source of truth
for "who is this, and are they premium," and holds no copy of the `users`
table itself.

| Owns | Never touches |
|---|---|
| `users` table, registration/login, JWT issuance & verification | URLs, click data |

## How other services depend on this one

`shortener` and `analytics` both verify a caller's access token by calling
this service's internal gRPC server (`AuthTokenValidation.ValidateAccessToken`,
`:50052`) and building an identity from the claims it returns — neither holds
a signing or verification key of its own. This service calls nothing else; it
is the leaf of the dependency graph.

## API

Base path: `/api/v1/auth/` (web process, port 8000 in-container / **8001**
published).

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/register/` | Public | Create a new user account |
| `POST` | `/login/` | Public | Exchange username/password for an `access`/`refresh` token pair; rate-limited |
| `POST` | `/logout/` | Authenticated | Blacklist a refresh token |
| `POST` | `/token/refresh/` | Public | Exchange a refresh token for a new access token |

Interactive docs: `/api/v1/docs/` (Swagger UI), `/api/v1/redoc/`.

## Internal gRPC — `:50052`

`AuthTokenValidation.ValidateAccessToken` verifies an access token and
returns the claims embedded in it (`user_id`, `username`, `is_premium`,
`tier`). Authenticated with a shared secret (`INTERNAL_SERVICE_TOKEN`)
passed as gRPC metadata (`x-internal-token`) — never exposed over HTTP.
Served by its own process: `python manage.py serve_grpc`.

## Data model

`User` (extends Django's `AbstractUser`), table `users`:

| Field | Type | Notes |
|---|---|---|
| `is_premium` | `bool` | default `False` |
| `tier` | `str` | `free` / `basic` / `pro` / `enterprise`, default `free` |
| `email` | `str` | unique |

`is_premium_tier` (property): `True` if `is_premium` is set, or `tier` is
`pro`/`enterprise`. This is the *only* copy of identity in the whole
system — `shortener` and `analytics` never query it; they read
`user_id`/`is_premium`/`tier` off the JWT claims embedded at login.

## JWT

Signed and verified with **HS256** using this service's own `SECRET_KEY` —
no keypair, and no signing key material ever leaves this process. Access
tokens live 15 minutes, refresh tokens 1 day. Custom claims embedded at
login: `username`, `is_premium`, `tier` — everything the other two services
need to know about the caller without a database lookup.

## Business logic worth knowing about

- **Login rate limiting** (`RedisLoginRateLimiter`): 5 failed attempts for a
  username within 60 seconds blocks that username for 30 minutes
  (`429 Too Many Requests` with `Retry-After`).
- **Token issuance** (`JWTTokenService`): wraps
  `djangorestframework-simplejwt`; every access token carries the claims the
  other services need, so they never call back here except to verify the
  signature (over gRPC).

## Environment variables

| Var | Default | Purpose |
|---|---|---|
| `DEBUG` | `True` | Django debug mode |
| `SECRET_KEY` | *(required)* | Django secret key; also the JWT HS256 signing key |
| `ALLOWED_HOSTS` | `*` | Comma-separated allowed hosts |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` | *(required)* | Postgres connection |
| `REDIS_URL` | `redis://127.0.0.1:6379/0` | Backs the login rate limiter |
| `INTERNAL_SERVICE_TOKEN` | `""` | Shared secret authenticating gRPC calls to this service — must match shortener's and analytics' copy |

## Running it standalone

```bash
cp .env.example .env   # fill in real secrets
docker compose up --build
```

Brings up its own Postgres, Redis, the web process (`:8001`), and the gRPC
token-validation server (`:50052`). Docs at
http://localhost:8001/api/v1/docs/.

This is one of two ways to run this service — see
[../README.md](../README.md) for running all three services together
instead. The two are mutually exclusive (same container names/ports);
`docker compose down` whichever is up before starting the other.

## Tests

```bash
docker compose run --rm auth sh -c "pip install -r requirements-dev.txt && pytest -q"
```

`test_smoke.py` proves: register → login returns a token pair; the access
token actually carries the cross-service claims; invalid credentials are
rejected (401); repeated failed logins trip the rate limiter (429).
