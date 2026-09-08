# Auth Service

Owns user identity for the URL shortener microservices split. Issues and
verifies JWTs — every other service treats it as the single source of truth
for "who is this, and are they premium," and holds no copy of the `users`
table itself.

| Owns | Never touches |
|---|---|
| `users` table, registration/login, JWT issuance & verification | URLs, click data |

## How other services depend on this one

Neither `shortener` nor `analytics` calls this service directly anymore —
the API gateway (`../gateway`) does, once per request, via nginx's
`auth_request` module, then forwards the claims as trusted headers. This
service holds the only signing/verification key in the system and calls
nothing else itself; it is the leaf of the dependency graph.

## API

Base path: `/api/v1/auth/` (web process, port 8000 in-container — not
published directly; reachable through the gateway on **:8080**).

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/register/` | Public | Create a new user account |
| `POST` | `/login/` | Public | Exchange username/password for an `access`/`refresh` token pair; rate-limited |
| `POST` | `/logout/` | Authenticated | Blacklist a refresh token |
| `POST` | `/token/refresh/` | Public | Exchange a refresh token for a new access token |
| `POST` | `/internal/token/validate/` | `X-Internal-Token` | Body-based verification contract: `{"token": "..."}` → JSON claims |
| `GET` | `/internal/token/validate/` | `X-Internal-Token` | Header-based contract used by the gateway's `auth_request` — `Authorization: Bearer <token>` in, claims as response headers out |

Interactive docs: `/api/v1/docs/` (Swagger UI), `/api/v1/redoc/`. Both
internal-endpoint methods are excluded from both — they're not for
browser/client use.

Also, outside the `/api/v1/auth/` base path above: `GET /health/` — public,
liveness/readiness (DB + Redis check), `200`/`503`.

## Internal token validation

`/api/v1/auth/internal/token/validate/` verifies an access token and returns
the claims embedded in it (`user_id`, `username`, `is_premium`, `tier`) —
either as a JSON body (`POST`, for direct/manual calls) or as response
headers (`GET`, what the gateway's `auth_request` actually uses — see
[`../../gateway`](../../gateway)). Authenticated with a shared secret
(`INTERNAL_SERVICE_TOKEN`) sent as the `X-Internal-Token` header — the same
web process that serves public traffic on `:8000`, no separate port or
protocol.

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
  signature (over REST).

## Environment variables

| Var | Default | Purpose |
|---|---|---|
| `DEBUG` | `True` | Django debug mode |
| `SECRET_KEY` | *(required)* | Django secret key; also the JWT HS256 signing key |
| `ALLOWED_HOSTS` | `*` | Comma-separated allowed hosts |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` | *(required)* | Postgres connection |
| `REDIS_URL` | `redis://127.0.0.1:6379/0` | Backs the login rate limiter |
| `INTERNAL_SERVICE_TOKEN` | `""` | Shared secret authenticating REST calls to this service — must match shortener's and analytics' copy |

## Logs

One structured JSON object per line (`config/json_logging.py`), written to
stdout (`docker compose logs -f auth`) and, alongside that, to
`logs/auth.log` on disk — rotated at 10MB, keeping 5 backups. `500`s
(`django.request`) and security warnings (`django.security.*`) are logged
explicitly so neither is silently dropped. When running via Docker, `logs/`
is a bind mount (`./logs:/app/logs`), so it lands in this directory on the
host, not just inside the container.

## Running it

Part of the single combined stack — see [`../README.md`](../README.md):

```bash
cd ..                              # microservices/
cp .env.example .env               # fill in real secrets
docker compose up --build
```

Publishes no host port of its own; reachable through the gateway on
`http://localhost:8080/api/v1/auth/...`.

## Tests

```bash
cd ..                              # microservices/
docker compose run --rm auth sh -c "pip install -r requirements-dev.txt && pytest -q"
```

`test_smoke.py` proves: register → login returns a token pair; the access
token actually carries the cross-service claims; invalid credentials are
rejected (401); repeated failed logins trip the rate limiter (429).
