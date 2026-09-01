# URL Shortener — Microservices Edition

A three-way split of the [Module7](../README.md) monolith into independently
deployable services: **auth**, **shortener**, and **analytics**, each with its
own database. There is no unified gateway in front of them — clients call
each service directly on its own port — and every service-to-service call is
plain REST (JSON over HTTP), authenticated with a shared internal token. This
lives alongside the monolith (`../src/`) as a separate, self-contained
implementation — nothing here touches or depends on it.

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
        clients ──▶ auth :8001    shortener :8002    analytics :8003
                        │               │                  │
                    ┌───▼───┐       ┌───▼───┐          ┌───▼───┐
                    │auth-db│       │shortener│        │analytics│
                    │  pg   │       │  -db pg │        │  -db pg │
                    └───────┘       └────┬────┘        └────┬────┘
                                          │                  │
                                          │   POST /internal/ │
                                          │   clicks/ (REST)  │
                                          └────────▶──────────┘

        auth :8001         ◀── REST ──  shortener, analytics
        POST /api/v1/auth/internal/token/validate/
        "is this access token valid, and whose is it?"

        shortener :8002    ◀── REST ──  analytics
        GET /api/v1/internal/urls/{short_code}/owner/
        "does this short code exist, and who owns it?"
```

Each service is also reachable directly on its own port — there is no
gateway/reverse proxy in front of them. There is no separate broker or
internal-only port either: every cross-service call is a normal HTTP request
against the same web process (`:8000` inside each container) that serves
public traffic, distinguished only by the `X-Internal-Token` header.

### The three cross-service seams, and why each is shaped the way it is

1. **Identity: a REST call, not a shared key or a database join.** `auth` is
   the only service that ever signs or verifies a JWT — it uses its own
   `SECRET_KEY` (HS256), which never leaves that process. `shortener` and
   `analytics` have no signing/verification key at all: every authenticated
   request calls `auth`'s internal endpoint
   (`POST /api/v1/auth/internal/token/validate/`, authenticated with a shared
   `INTERNAL_SERVICE_TOKEN` header) to verify the token and get back its claims
   (`apps/common/jwt_auth.py`, `RemoteJWTAuthentication`), then build a
   `RemoteUser` from the response — no local `users` table. The trade-off:
   this adds one HTTP round-trip to every authenticated request (in exchange
   for auth being able to rotate its signing key, or revoke tokens, without
   redeploying the other two services). A user's premium upgrade still
   doesn't take effect until their token refreshes (access tokens are
   short-lived — 15 minutes — specifically to bound that staleness).

2. **Click tracking: fire-and-forget REST, not a synchronous write.** The
   redirect endpoint (`GET /{short_code}/`) is the highest-traffic,
   unauthenticated, latency-critical path in the system. It must never
   block on — or fail because of — analytics being slow or down. So
   `shortener` dispatches a `POST /api/v1/internal/clicks/` to analytics on a
   background thread (`ClickEventPublisher`, backed by a small
   `ThreadPoolExecutor`) and returns immediately; a delivery failure is
   logged and swallowed, never raised back to the caller. `analytics`
   receives the click synchronously on that endpoint and does the geo
   lookup + write in the same request.

3. **Ownership lookup: the other synchronous REST call.** `analytics` has no
   `urls` table, so "does this short code exist, and is it owned by the
   caller?" (needed for `GET /api/v1/analytics/{short_code}/`) is answered by
   calling shortener's internal endpoint
   (`GET /api/v1/internal/urls/{short_code}/owner/`), also authenticated with
   `INTERNAL_SERVICE_TOKEN`. A failed lookup fails *closed* (treated as "not
   found"), so a down shortener service can't leak anyone's analytics — it
   just makes analytics briefly unavailable too.

## Running it

Two ways to run this, and they're genuinely alternatives — pick one:

**All three services together** (this top-level `docker-compose.yml`), for
integration testing or demoing the whole system:

```bash
cp .env.example .env              # then fill in real secrets
docker compose up --build
```

**Each service completely on its own** — its own `docker-compose.yml`, own
database, own Redis, nothing else required to start it. This is the
"one team, one service, one checkout" way to run it, and it's how you'd work
on just one service without needing the others up at all:

```bash
cd auth                           # or shortener/, or analytics/
cp .env.example .env              # fill in real secrets
docker compose up --build
```

Each standalone service reuses the same container names/ports as its
counterpart in the combined stack, so the two are mutually exclusive —
`docker compose down` whichever is up before starting the other. Verified
this actually works end to end: a token issued by standalone `auth`
validates against standalone `shortener` over REST
(`AUTH_SERVICE_URL=http://host.docker.internal:8001`), and standalone
`analytics` reaches standalone `shortener`'s ownership endpoint over
`SHORTENER_SERVICE_URL=http://host.docker.internal:8002`. Click delivery
works the same way in reverse — point standalone `shortener`'s
`ANALYTICS_SERVICE_URL` at a reachable `analytics`, or leave it unset and
publish attempts just fail closed (logged, swallowed; redirects keep working).

Each service and its docs, called directly — there is no gateway in front of
them:

| Service | Docs |
|---|---|
| auth | http://localhost:8001/api/v1/docs/ |
| shortener | http://localhost:8002/api/v1/docs/ |
| analytics | http://localhost:8003/api/v1/docs/ |

### Endpoints

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

Three more endpoints exist purely for service-to-service calls, gated by the
shared `X-Internal-Token` header rather than a user's JWT, and excluded from
the public Swagger docs:

| Method | Path | Service | Called by |
|---|---|---|---|
| `POST` | `/api/v1/auth/internal/token/validate/` | auth | shortener, analytics |
| `GET` | `/api/v1/internal/urls/{short_code}/owner/` | shortener | analytics |
| `POST` | `/api/v1/internal/clicks/` | analytics | shortener |

RBAC, tier limits (10 active URLs / custom aliases / detailed analytics),
and login rate-limiting all carry over unchanged from the monolith — see its
[README](../README.md) for the exact behavior.

### Running each service's tests

```bash
docker compose run --rm auth       sh -c "pip install -r requirements-dev.txt && pytest -q"
docker compose run --rm shortener  sh -c "pip install -r requirements-dev.txt && pytest -q"
docker compose run --rm analytics  sh -c "pip install -r requirements-dev.txt && pytest -q"
```

These are deliberately *not* a full re-test of every case already covered in
the monolith's suite — each service's `test_smoke.py` proves the things that
are genuinely new about the split (JWT verification without a local user
table, the plain-integer `owner_id`, the ownership round-trip, the
publish/ingest path), not business logic that hasn't changed.

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
  `stats.total_clicks` (premium-gated, same as the monolith).
- **One shared Redis** backs the login rate limiter and the URL cache — two
  unrelated per-service concerns. True isolation would give each service its
  own instance; this is the common, pragmatic middle ground as long as key
  namespaces don't collide (`auth:*`, `url:*`).
- **Click delivery has no retry or durability.** `ClickEventPublisher` fires
  a single REST request on a background thread and gives up on failure —
  there's no queue, no at-least-once redelivery, and a click can be silently
  lost if analytics is down at the exact moment of the request. A real
  deployment that needed a durability guarantee here would put a message
  broker back in front of this seam.
- **No observability stack.** A request that spans all three services has
  no distributed tracing here — `docker compose logs -f` per-service, plus
  each service's own `logs/<service>.log` on disk (rotated, 10MB × 5 files),
  is the debugging story. Adding OpenTelemetry + Jaeger/Tempo would be the
  natural next step, not a redesign.
- **No unified entry point.** There is no gateway/reverse proxy in front of
  the three services — a client talks to whichever one it needs on that
  service's own port. That also means no shared CORS/rate-limiting layer;
  each service still enforces its own auth and the login rate limiter
  independently. A real deployment fronting a browser client would want an
  API gateway (or at least a reverse proxy) back in front of this.
- **Single-host Docker Compose, not Kubernetes.** Enough to prove out
  independent databases and independent deploys. A move to Kubernetes would
  change *how* these run, not the service boundaries themselves.
