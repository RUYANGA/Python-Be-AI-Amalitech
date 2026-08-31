# Shortener Service

Owns URL shortening, tagging, RBAC, and tier limits for the URL shortener
microservices split. Has no `users` table of its own — every request is
authenticated by asking `auth` to verify the caller's token.

| Owns | Never touches |
|---|---|
| `urls`/`tags` tables, RBAC, tier limits, short-code generation | users, click data |

## How this service depends on / is depended on by others

- **Calls `auth`**: every authenticated request verifies its JWT by calling
  `auth`'s internal gRPC server (`AuthTokenValidation.ValidateAccessToken`) —
  this service holds no signing/verification key of its own.
- **Calls nothing else.** Click tracking is one-way: this service *publishes*
  a `ClickRecorded` event to Kafka and moves on; it never calls `analytics`.
- **Is called by `analytics`**: `analytics` has no `urls` table, so it asks
  this service's internal gRPC server (`ShortenerOwnership.GetOwner`) "does
  this short code exist, and who owns it?" for its premium analytics
  endpoint.

## API

Base path: `/api/v1/` (web process, port 8000 in-container / **8002**
published).

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/urls/` | Authenticated | Create a shortened URL |
| `GET` | `/urls/mine/` | Authenticated | List the caller's own URLs (cursor-paginated, filterable) |
| `GET` | `/urls/{short_code}/` | Authenticated + owner | Retrieve one of the caller's own URLs |
| `PATCH` | `/urls/{short_code}/` | Authenticated + owner | Update title/original URL/tags/expiry |
| `DELETE` | `/urls/{short_code}/` | Authenticated + owner | Delete an owned URL |
| `GET` | `/api/v1/{short_code}/` | Public | JSON resolve — `{"original_url": ...}`, records a click |
| `GET` | `/{short_code}/` | Public | **The actual short link** — 302 redirect, records a click |

A non-owner touching someone else's `{short_code}` gets `404`, not `403` —
deliberately, so a write attempt can't be used to probe whether a code
exists. Interactive docs: `/api/v1/docs/` (Swagger UI), `/api/v1/redoc/`.

## Internal gRPC — `:50051`

`ShortenerOwnership.GetOwner` answers "does this short code exist, and who
owns it?" for `analytics`. Authenticated with a shared secret
(`INTERNAL_SERVICE_TOKEN`) passed as gRPC metadata (`x-internal-token`) —
never exposed over HTTP. Served by its own process:
`python manage.py serve_grpc`.

## Data model

`URL`, table `urls`:

| Field | Type | Notes |
|---|---|---|
| `original_url` | `str` (≤2048) | |
| `short_code` | `str` (≤10) | unique, indexed |
| `title` | `str` | optional |
| `owner_id` | `int` | **plain integer, not a FK** — the owning user lives in `auth`'s database; enforced via the JWT `user_id` claim, not a database join |
| `click_count` | `int` | no longer live — see [Known simplifications](../README.md#known-simplifications) |
| `is_active` | `bool` | default `True` |
| `expires_at` | `datetime` | optional |
| `tags` | M2M → `Tag` | |

`Tag`, table `tags`: `name` (unique).

## Business logic worth knowing about

- **Short-code generation** (`Base62ShortCodeGenerator`): CSPRNG over
  `[A-Za-z0-9]`, 7 characters by default (~3.5×10¹² keyspace); retries up to
  5 times on a collision before giving up.
- **Free-tier cap**: non-premium owners are capped at 10 *active* URLs;
  the 11th create attempt returns `403`. Premium owners are unlimited.
- **Custom aliases are premium-only**: a free-tier `custom_alias` request
  returns `403`; an already-taken alias returns a distinct conflict error.
  Alias format: `^[A-Za-z0-9_-]{3,10}$`.
- **Read-through Redis cache** (`CachedURLRepository`): caches
  lookup-by-code, lookup-by-id, existence checks, and list pages, with
  write-through invalidation. The per-owner active-URL *count* is
  deliberately never cached, since tier-quota correctness depends on it
  being exact.
- **Click publishing** (`ClickEventPublisher`): fire-and-forget publish to
  the Kafka `clicks` topic on every redirect/resolve. Publish failures are
  logged and swallowed, never raised — the highest-traffic path in the
  system must never fail because Kafka or `analytics` is down.

## Environment variables

| Var | Default | Purpose |
|---|---|---|
| `DEBUG` | `True` | Django debug mode |
| `SECRET_KEY` | *(required)* | Django secret key (not used for JWT here) |
| `ALLOWED_HOSTS` | `*` | Comma-separated allowed hosts |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` | *(required)* | Postgres connection |
| `REDIS_URL` | `redis://127.0.0.1:6379/0` | Backs the read-through URL cache |
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9094` | Where click events are published |
| `AUTH_GRPC_URL` | `localhost:50052` | Where to verify JWTs — auth's gRPC server |
| `INTERNAL_SERVICE_TOKEN` | `""` | Shared secret for gRPC calls in both directions (to auth, from analytics) — must match all three services' copies |

## Logs

Written to stdout (`docker compose logs -f shortener`) and, alongside that,
to `logs/shortener.log` on disk — rotated at 10MB, keeping 5 backups. The
`shortener-grpc` container shares the same log file (same bind mount,
`./logs:/app/logs`), so its own gRPC-server logs land there too.

## Running it standalone

```bash
cp .env.example .env   # fill in real secrets
docker compose up --build
```

Brings up its own Postgres, Redis, Kafka broker, the web process (`:8002`),
and the ownership gRPC server (`:50051`). Needs a reachable `auth` gRPC
server to verify tokens (`AUTH_GRPC_URL`, defaults to a standalone `auth`'s
`host.docker.internal:50052`) — without one, every authenticated request
fails with `401`. Without an `analytics` consumer, published click events
just accumulate harmlessly in the local Kafka topic. Docs at
http://localhost:8002/api/v1/docs/.

This is one of two ways to run this service — see
[../README.md](../README.md) for running all three services together
instead. The two are mutually exclusive (same container names/ports);
`docker compose down` whichever is up before starting the other.

## Tests

```bash
docker compose run --rm shortener sh -c "pip install -r requirements-dev.txt && pytest -q"
```

`test_smoke.py` proves: anonymous create is rejected (401); an authenticated
create sets the correct `owner_id` (201); the redirect endpoint 302s to the
original URL; a non-owner's `PATCH` returns 404; the owner's `PATCH`
succeeds; an 11th URL from a free user is rejected (403); a premium user can
use a custom alias while a free user cannot.
