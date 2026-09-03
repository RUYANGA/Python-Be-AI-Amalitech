# Analytics Service

Owns click data and the premium "detailed analytics" endpoint for the URL
shortener microservices split. Has no `users` or `urls` table of its own,
and never verifies a JWT itself — the API gateway (`../gateway`) does that
once, up front, and forwards the verified identity as trusted headers. URL
ownership is confirmed by asking `shortener` directly, over the internal
Docker network — not through the gateway, which is for client-facing
traffic only.

| Owns | Never touches |
|---|---|
| `clicks` table, aggregate/time-series reporting | users, URL metadata |

## How this service depends on / is depended on by others

- **Trusts the gateway for identity**: every request to the analytics
  endpoint arrives with `X-User-*` headers already set by the gateway's
  `auth_request` check against `auth`
  (`apps.analytics.api.authentication.GatewayAuthentication`) — this service
  holds no signing/verification key, and makes no network call to
  authenticate a request.
- **Calls `shortener` directly**: the *only* synchronous cross-service call
  this service makes at request time is
  `GET /api/v1/internal/urls/{short_code}/owner/`
  (`SHORTENER_SERVICE_URL=http://shortener:8000` — not through the gateway)
  — "does this short code exist, and is it owned by the caller?" A failed
  lookup (including a down `shortener`) fails **closed**: treated as "not
  found," so a `shortener` outage can never leak someone else's analytics,
  it just makes this endpoint briefly unavailable too.
- **Is called by `shortener` directly**: click data arrives one-way,
  synchronously from shortener's point of view but off its hot path —
  shortener dispatches `POST /api/v1/internal/clicks/` straight to this
  service on a background thread on every redirect/resolve; this service
  records it (and does the geo lookup) immediately on receipt.

## API

Base path: `/api/v1/` (web process, port 8000 in-container — not published
directly; reachable through the gateway on **:8080**):

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/analytics/{short_code}/` | Authenticated + premium + owner | Click stats, geo/referrer breakdowns, hourly distribution, and a daily time series for a URL you own |
| `POST` | `/internal/clicks/` | `X-Internal-Token` | Record a click event — called by shortener only |

Query param on the analytics endpoint: `days` (default `30`) — how far back
the time series covers. Returns `401` unauthenticated, `403` for a
non-premium caller, `404` if the code doesn't exist or isn't owned by the
caller. Interactive docs: `/api/v1/docs/` (Swagger UI), `/api/v1/redoc/`.
The internal endpoint is excluded from both — it's not for browser/client
use.

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
  the `shortener` REST call first, then assembles aggregate stats, country
  and referrer breakdowns, an hourly distribution, recent clicks, and a
  `days`-bounded daily time series — all from this service's own `clicks`
  table.
- **Click ingestion** (`ClickIngestView`, `POST /api/v1/internal/clicks/`):
  handled synchronously, on the same web process that serves the analytics
  endpoint — there's no separate worker process. Shortener already keeps
  this off its own hot path by dispatching the request on a background
  thread, so this endpoint can afford to do the geo lookup and write inline.
- **Geo lookup** (`GeoIP2FastLocator`): offline IP→country resolution (no
  external API call) done at ingest time, deliberately kept off
  `shortener`'s hot redirect path.

## Environment variables

| Var | Default | Purpose |
|---|---|---|
| `DEBUG` | `True` | Django debug mode |
| `SECRET_KEY` | *(required)* | Django secret key |
| `ALLOWED_HOSTS` | `*` | Comma-separated allowed hosts |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` | *(required)* | Postgres connection |
| `SHORTENER_SERVICE_URL` | `http://shortener:8000` | Where to look up URL ownership — called directly, not through the gateway |
| `INTERNAL_SERVICE_TOKEN` | `""` | Shared secret for the ownership-lookup REST call, and for verifying inbound click-ingestion calls — must match all three services' copies |

## Logs

Written to stdout (`docker compose logs -f analytics`) and, alongside that,
to `logs/analytics.log` on disk — rotated at 10MB, keeping 5 backups.

## Running it

Part of the single combined stack — see [`../README.md`](../README.md):

```bash
cd ..                              # microservices/
cp .env.example .env               # fill in real secrets
docker compose up --build
```

Publishes no host port of its own; reachable through the gateway on
`http://localhost:8080/api/v1/analytics/...`. Needs a reachable `shortener`
for the ownership check — without it, `GET /api/v1/analytics/{short_code}/`
fails closed (`404`) for everything.

## Tests

```bash
cd ..                              # microservices/
docker compose run --rm analytics sh -c "pip install -r requirements-dev.txt && pytest -q"
```

`test_smoke.py` proves: a non-premium caller is rejected (403); a code owned
by someone else is rejected (404), via a mocked ownership client; and the
full happy path — an owned code with two recorded clicks, both from the
same country — returns 200 with the correct aggregate stats and country
breakdown.
