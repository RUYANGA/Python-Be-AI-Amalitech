# Analytics Service

Owns click data and the premium "detailed analytics" endpoint for the URL
shortener microservices split. Has no `users` or `urls` table of its own —
identity comes from a verified JWT, and URL ownership is confirmed by
asking `shortener`.

| Owns | Never touches |
|---|---|
| `clicks` table, aggregate/time-series reporting | users, URL metadata |

## How this service depends on / is depended on by others

- **Calls `auth`**: every request to the analytics endpoint verifies its JWT
  by calling `auth`'s internal gRPC server
  (`AuthTokenValidation.ValidateAccessToken`) — this service holds no
  signing/verification key of its own.
- **Calls `shortener`**: the *only* synchronous cross-service call this
  service makes at request time is `ShortenerOwnership.GetOwner` — "does
  this short code exist, and is it owned by the caller?" A failed lookup
  (including a down `shortener`) fails **closed**: treated as "not found,"
  so a `shortener` outage can never leak someone else's analytics, it just
  makes this endpoint briefly unavailable too.
- **Is called by nothing.** No other service depends on `analytics`.
- Click data itself arrives one-way, asynchronously, over Kafka — `shortener`
  publishes, this service's worker consumes. Not a request-time dependency.

## API

Base path: `/api/v1/` (web process, port 8000 in-container / **8003**
published). This is the only HTTP endpoint in the service:

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/analytics/{short_code}/` | Authenticated + premium + owner | Click stats, geo/referrer breakdowns, hourly distribution, and a daily time series for a URL you own |

Query param: `days` (default `30`) — how far back the time series covers.
Returns `401` unauthenticated, `403` for a non-premium caller, `404` if the
code doesn't exist or isn't owned by the caller. Interactive docs:
`/api/v1/docs/` (Swagger UI), `/api/v1/redoc/`.

## Data model

`Click`, table `clicks`:

| Field | Type | Notes |
|---|---|---|
| `short_code` | `str` (≤10) | plain string, no FK — matches what `shortener` publishes |
| `ip_address` | IP | optional |
| `user_agent` | `str` | |
| `country` | `str` (2-char) | resolved offline at ingest time |
| `city` | `str` | present on the model but not currently populated by the ingest pipeline |
| `referer` | `str` (URL) | |
| `clicked_at` | `datetime` | auto-set, indexed together with `short_code` and `country` for the aggregate queries |

## Business logic worth knowing about

- **Premium-gated** (`IsPremiumUser`): the entire endpoint requires
  `user.is_premium_tier` — a free-tier caller gets `403` regardless of
  ownership.
- **Ownership-then-aggregate** (`AnalyticsService`): confirms ownership via
  the `shortener` gRPC call first, then assembles aggregate stats, country
  and referrer breakdowns, an hourly distribution, recent clicks, and a
  `days`-bounded daily time series — all from this service's own `clicks`
  table.
- **Click ingestion** (`consume_clicks` management command): a long-running
  Kafka consumer, running in its own container (`analytics-worker`)
  separate from the web process so ingestion never competes with serving
  the analytics endpoint. Commits offsets manually, only after a successful
  write — a crash mid-batch redelivers the message on restart instead of
  silently dropping it.
- **Geo lookup** (`GeoIP2FastLocator`): offline IP→country resolution (no
  external API call) done at ingest time, deliberately moved off
  `shortener`'s hot redirect path.

## Environment variables

| Var | Default | Purpose |
|---|---|---|
| `DEBUG` | `True` | Django debug mode |
| `SECRET_KEY` | *(required)* | Django secret key |
| `ALLOWED_HOSTS` | `*` | Comma-separated allowed hosts |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` | *(required)* | Postgres connection |
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9096` | How `consume_clicks` receives click events from shortener |
| `AUTH_GRPC_URL` | `localhost:50052` | Where to verify JWTs — auth's gRPC server |
| `SHORTENER_GRPC_URL` | `localhost:50051` | Where to look up URL ownership — shortener's gRPC server |
| `INTERNAL_SERVICE_TOKEN` | `""` | Shared secret for both outbound gRPC calls — must match all three services' copies |

## Running it standalone

```bash
cp .env.example .env   # fill in real secrets
docker compose up --build
```

Brings up its own Postgres, Kafka broker, the web process (`:8003`), and the
`analytics-worker` consumer. Needs a reachable `auth` gRPC server to verify
tokens and a reachable `shortener` gRPC server for the ownership check
(both default to a standalone counterpart's `host.docker.internal` address)
— without `shortener`, `GET /api/v1/analytics/{short_code}/` fails closed
(`404`) for everything, which is expected in isolation. Docs at
http://localhost:8003/api/v1/docs/.

This is one of two ways to run this service — see
[../README.md](../README.md) for running all three services together
instead. The two are mutually exclusive (same container names/ports);
`docker compose down` whichever is up before starting the other.

## Tests

```bash
docker compose run --rm analytics sh -c "pip install -r requirements-dev.txt && pytest -q"
```

`test_smoke.py` proves: a non-premium caller is rejected (403); a code owned
by someone else is rejected (404), via a mocked ownership client; and the
full happy path — an owned code with two recorded clicks, both from the
same country — returns 200 with the correct aggregate stats and country
breakdown.
