# URL Shortener — Microservices Edition

A URL shortener split into three independently deployable services —
**auth**, **shortener**, and **analytics** — each with its own database,
sitting behind a single nginx **API gateway** ([`../gateway`](../gateway)) —
the only container reachable from outside the Docker network. Every *client*
request goes through it, which centralizes JWT verification in one place
instead of each service doing it independently. Service-to-service calls are
a separate concern: they go directly, container-to-container, over the same
internal network, still plain REST (JSON over HTTP) authenticated with a
shared internal token — the gateway has nothing to do with them.

## Why split it this way

See the conversation that led here for the full reasoning; in short, each
service owns one bounded context's data and nothing else:

| Service | Owns | Never touches |
|---|---|---|
| **auth** | `users` table, JWT issuance | URLs, clicks |
| **shortener** | `urls`/`tags` tables, RBAC, tier limits | users, click data |
| **analytics** | `clicks` table, aggregate reporting | users, URL metadata |

## Architecture

```
                              clients
                                 │
                                 ▼
                      ┌─────────────────────┐
                      │   gateway  :8080     │   nginx (../gateway)
                      │  (only published     │   auth_request → auth,
                      │   port in the stack) │   then path-based routing
                      └───┬───────┬───────┬──┘
                          │       │       │
                     ┌────▼──┐ ┌──▼────┐ ┌▼─────────┐
                     │ auth  │ │shortener│ │analytics │   internal-only —
                     └───┬───┘ └───┬────┘ └────┬─────┘   no host ports
                         │         │           │
                     ┌───▼───┐ ┌───▼─────┐ ┌───▼──────┐
                     │auth-db│ │shortener│ │analytics │
                     │  pg   │ │ -db  pg │ │  -db  pg │
                     └───────┘ └─────────┘ └──────────┘

        At the gateway, for every client request to a protected route:

        gateway ◀── auth_request ──  every /api/v1/urls/ and
                                      /api/v1/analytics/ request
        GET /api/v1/auth/internal/token/validate/
        "is this access token valid, and whose is it?" (asked once, here)

        Service-to-service, bypassing the gateway entirely:

        shortener ──▶ analytics   POST /api/v1/internal/clicks/
        "record this click" (fire-and-forget, off shortener's hot path)

        analytics ──▶ shortener   GET /api/v1/internal/urls/{short_code}/owner/
        "does this short code exist, and who owns it?"
```

`auth`, `shortener`, and `analytics` publish no host ports at all — the
gateway is the only container reachable from outside the Docker network.
That's specifically about *client* traffic, though: the two service-to-service
calls above go straight from one container to the other over the same
internal network, not through the gateway — see
[`../gateway`](../gateway#service-to-service-traffic) for why.

### The three cross-service seams, and why each is shaped the way it is

1. **Identity: centralized at the gateway, not re-verified per service.**
   `auth` is the only service that ever signs or verifies a JWT — it uses its
   own `SECRET_KEY` (HS256), which never leaves that process. `shortener` and
   `analytics` have no signing/verification key, and don't call auth
   themselves either: the gateway verifies the token **once**, via nginx's
   `auth_request` module (a subrequest to auth's internal endpoint,
   authenticated with the shared `INTERNAL_SERVICE_TOKEN` header — see
   [`../gateway`](../gateway)), then forwards the claims it got back as
   trusted `X-User-*` headers. Each service just reads those headers
   (`apps/<service>/api/authentication.py`, `GatewayAuthentication`) and
   builds a `RemoteUser` from them — no network call, no local `users` table,
   on every request. The trade-off is the same as before: this still adds one
   HTTP round-trip on the way in (auth being able to rotate its signing key,
   or revoke tokens, without redeploying the other two services), it just
   happens once at the edge instead of once per service. A user's premium
   upgrade still doesn't take effect until their token refreshes (access
   tokens are short-lived — 15 minutes — specifically to bound that
   staleness).

2. **Click tracking: fire-and-forget REST, then write-behind via Celery —
   two separate hops, neither of them a synchronous write.** The redirect
   endpoint (`GET /{short_code}/`) is the highest-traffic, unauthenticated,
   latency-critical path in the system. It must never block on — or fail
   because of — analytics being slow or down. So `shortener` dispatches a
   `POST /api/v1/internal/clicks/` directly to `analytics`
   (`ANALYTICS_SERVICE_URL=http://analytics:8000`, not through the gateway)
   on a background thread (`ClickEventPublisher`, backed by a small
   `ThreadPoolExecutor`) and returns immediately; a delivery failure is
   logged and swallowed, never raised back to the caller. `analytics`
   doesn't write the `Click` row (or do the geo lookup) in that request
   either — `ClickIngestView` just validates the payload and enqueues
   `track_click_task` onto its own Celery worker
   (`apps.analytics.tasks`), returning `202 Accepted` immediately. The
   actual database write happens on `analytics-worker`, off both request
   paths.

3. **Ownership lookup: the other synchronous REST call.** `analytics` has no
   `urls` table, so "does this short code exist, and is it owned by the
   caller?" (needed for `GET /api/v1/analytics/{short_code}/`) is answered by
   calling shortener's internal endpoint directly
   (`SHORTENER_SERVICE_URL=http://shortener:8000`,
   `GET /api/v1/internal/urls/{short_code}/owner/`), also authenticated with
   `INTERNAL_SERVICE_TOKEN`. A failed lookup fails *closed* (treated as "not
   found"), so a down shortener service can't leak anyone's analytics — it
   just makes analytics briefly unavailable too. Neither of these two calls
   goes through the gateway — see [`../gateway`](../gateway) for why.

### Background processing, logging, and health

- **Celery workers, one per service that needs one.** `shortener-worker` +
  `shortener-beat` run the nightly `archive_expired_urls` job
  (`CELERY_BEAT_SCHEDULE`, 02:00) that deactivates any URL past its
  `expires_at` — going through the same cached repository a normal edit
  would, so the cache is invalidated the same way. `analytics-worker` runs
  the write-behind click task described above. Each service's Celery
  broker lives on its **own Redis DB index** on the shared Redis instance
  (`/1` for shortener, `/2` for analytics) — deliberately *not* the same DB
  as the `REDIS_URL` cache, and not shared between the two services either:
  Celery's redis transport consumes an entire queue with a plain `BRPOP` on
  a fixed key (`celery` by default) with no per-app prefix, so two services
  sharing one DB would each `BRPOP` the *other's* tasks off the same list —
  and a message popped by the wrong worker is simply dropped, not requeued.
- **Structured JSON logging.** Every service's `LOGGING` config
  (`config/json_logging.py`) renders one JSON object per line — to both
  stdout (`docker compose logs -f`) and the rotating `logs/<service>.log`
  file — instead of free text, with `django.request` (500s) and
  `django.security.*` (disallowed hosts, CSRF failures, ...) wired to
  explicit loggers so neither is silently dropped.
- **`GET /health/`, per service.** Checks a real database round-trip and a
  Redis `PING`, returning `200 {"status": "ok", "checks": {...}}` or `503`
  with the failing check named. No authentication — called by
  `docker-compose`'s own `healthcheck:` blocks (which is what gates
  `depends_on: condition: service_healthy` between services, and why
  `analytics`/`shortener-worker`/etc. only start once their dependencies
  have actually finished migrating, not just booted) and by external
  monitoring. The gateway has its own, unrelated `GET /health` — a plain
  liveness check that nginx itself is up, nothing about any backend.

## Running it

One way to run this — the whole stack, behind the gateway, via the one
`docker-compose.yml` in this directory (and the one `Dockerfile`, shared by
all three Django services):

```bash
cp .env.example .env              # then fill in real secrets
docker compose up --build
```

`auth`, `shortener`, and `analytics` publish no host ports — everything goes
through the gateway on **`:8080`**:

| What | URL |
|---|---|
| Gateway (everything) | http://localhost:8080/ |
| Auth docs | http://localhost:8080/api/v1/docs/auth/ |
| Shortener docs | http://localhost:8080/api/v1/docs/shortener/ |
| Analytics docs | http://localhost:8080/api/v1/docs/analytics/ |

### Endpoints

All paths below are relative to the gateway (`http://localhost:8080`) — see
[`../gateway`](../gateway) for the full routing table.

| Method | Path | Service |
|---|---|---|
| `POST` | `/api/v1/auth/register/` | auth |
| `POST` | `/api/v1/auth/login/` | auth |
| `POST` | `/api/v1/auth/logout/` | auth |
| `POST` | `/api/v1/auth/token/refresh/` | auth |
| `POST` | `/api/v1/urls/` | shortener |
| `GET` | `/api/v1/urls/mine/` | shortener |
| `GET`/`PATCH`/`DELETE` | `/api/v1/urls/{short_code}/` | shortener |
| `GET` | `/api/v1/{short_code}/` | shortener (JSON resolve) |
| `GET` | `/{short_code}/` | shortener (302 redirect — the actual short link) |
| `GET` | `/api/v1/analytics/{short_code}/` | analytics (premium only) |
| `GET` | `/health/` | each service (auth/shortener/analytics) — DB + Redis check |
| `GET` | `/health` | gateway — nginx liveness only |

Three more endpoints exist purely for service-to-service calls, gated by the
shared `X-Internal-Token` header rather than a user's JWT, excluded from the
public Swagger docs, and (except auth's, which shares its host with the
public auth endpoints) called directly container-to-container — not through
the gateway, which blocks `/api/v1/internal/` entirely:

| Method | Path | Service | Called by |
|---|---|---|---|
| `POST` | `/api/v1/auth/internal/token/validate/` | auth | shortener, analytics |
| `GET` | `/api/v1/internal/urls/{short_code}/owner/` | shortener | analytics |
| `POST` | `/api/v1/internal/clicks/` | analytics | shortener |

RBAC, tier limits (10 active URLs / custom aliases / detailed analytics), and
login rate-limiting are documented in each owning service's own README, under
"Business logic worth knowing about":
[`auth`](auth/README.md#business-logic-worth-knowing-about) for
rate-limiting, [`shortener`](shortener/README.md#business-logic-worth-knowing-about)
for RBAC and tier limits.

### Running each service's tests

```bash
docker compose run --rm auth       sh -c "pip install -r requirements-dev.txt && pytest -q"
docker compose run --rm shortener  sh -c "pip install -r requirements-dev.txt && pytest -q"
docker compose run --rm analytics  sh -c "pip install -r requirements-dev.txt && pytest -q"
```

Each service's `test_smoke.py` covers its own business logic end to end
(auth's rate limiter, shortener's tier limits, analytics' aggregation) —
see each service's own README for exactly what it proves. The other test
files (ownership lookup, click ingest/publish) cover the pieces that are
genuinely new about the split: JWT verification without a local user table,
the plain-integer `owner_id`, and the cross-service REST calls.

## Known simplifications

Being upfront about what this deliberately does *not* do, so it doesn't read
as an oversight:

- **`click_count` / `last_accessed_at` on a URL are no longer live.** They
  were denormalized counters shortener used to update in the same
  transaction as writing a `Click` row — but `Click` now lives in a
  different service's database, so shortener can no longer update them
  atomically (or at all, without a second cross-service call). They're kept
  in the model/API shape for compatibility but will read `0`/`null`. The
  authoritative count is `GET /api/v1/analytics/{short_code}/`'s
  `stats.total_clicks` (premium-gated).
- **One shared Redis** backs the login rate limiter, the URL/analytics
  caches, and both services' Celery brokers — several unrelated per-service
  concerns on one instance. True isolation would give each its own
  instance; this is the common, pragmatic middle ground as long as they
  don't collide — the caches by key namespace (`auth:*`, `url:*`,
  `analytics:*`), the two Celery brokers by DB index (`/1`, `/2`, see
  above) since queue keys aren't namespaced at all.
- **Click delivery still has one fire-and-forget hop.** The write side is
  now durable from the moment `analytics` accepts a click — `track_click_task`
  sits on a Celery/Redis queue until `analytics-worker` processes it, so a
  slow or momentarily-restarting analytics process no longer loses it. What's
  *not* durable is the hop before that: `ClickEventPublisher`'s `POST` from
  `shortener` to `analytics` is still a single REST request on a background
  thread with no retry, so a click can still be silently lost if `analytics`
  is unreachable at the exact moment `shortener` tries to deliver it. Closing
  that gap too would mean putting a message broker in front of that seam as
  well, not just behind analytics' own endpoint.
- **Structured logs, but no distributed tracing.** Every service now emits
  one JSON log line per event (see above) instead of free text, but a
  request that spans all three services still has no correlation ID tying
  its log lines together across process boundaries — `docker compose logs
  -f` per-service is still how you'd follow one. Adding OpenTelemetry +
  Jaeger/Tempo would be the natural next step, not a redesign.
- **Docs/schema are multiplexed via `rewrite`, not natively.** Each service's
  own drf-spectacular Swagger UI still assumes it's the only thing on the
  host — all three define docs/schema at the same literal `/api/v1/docs/`
  and `/api/v1/schema/` paths. The gateway gives each an unambiguous address
  (`/api/v1/docs/<service>/`, `/api/v1/schema/<service>/`) with an nginx
  `rewrite` + `sub_filter`, rather than each service knowing its own mount
  prefix — see [`../gateway`](../gateway#known-simplification) for the one
  edge case that doesn't cover. A real deployment would give each service
  its own subdomain, or run drf-spectacular with an `X-Forwarded-Prefix`-aware
  `SCRIPT_NAME`.
- **Single-host Docker Compose, not Kubernetes.** Enough to prove out
  independent databases and independent deploys. A move to Kubernetes would
  change *how* these run, not the service boundaries themselves.
