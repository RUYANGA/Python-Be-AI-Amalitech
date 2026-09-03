# URL Shortener — Microservices Edition

A three-way split of the [Module7](../README.md) monolith into independently
deployable services: **auth**, **shortener**, and **analytics**, each with its
own database, sitting behind a single nginx **API gateway**
([`../gateway`](../gateway)) — the only container reachable from outside the
Docker network. Every *client* request goes through it, which centralizes JWT
verification in one place instead of each service doing it independently.
Service-to-service calls are a separate concern: they go directly,
container-to-container, over the same internal network, still plain REST
(JSON over HTTP) authenticated with a shared internal token — the gateway
has nothing to do with them. This lives alongside the monolith (`../src/`) as
a separate, self-contained implementation — nothing here touches or depends
on it.

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

2. **Click tracking: fire-and-forget REST, not a synchronous write.** The
   redirect endpoint (`GET /{short_code}/`) is the highest-traffic,
   unauthenticated, latency-critical path in the system. It must never
   block on — or fail because of — analytics being slow or down. So
   `shortener` dispatches a `POST /api/v1/internal/clicks/` directly to
   `analytics` (`ANALYTICS_SERVICE_URL=http://analytics:8000`, not through
   the gateway) on a background thread (`ClickEventPublisher`, backed by a
   small `ThreadPoolExecutor`) and returns immediately; a delivery failure
   is logged and swallowed, never raised back to the caller. `analytics`
   receives the click synchronously on that endpoint and does the geo
   lookup + write in the same request.

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
| Auth docs | http://localhost:8080/api/docs/auth/ |
| Shortener docs | http://localhost:8080/api/docs/shortener/ |
| Analytics docs | http://localhost:8080/api/docs/analytics/ |

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
- **The gateway's upstream hostnames are resolved once, at nginx startup.**
  `auth`/`shortener`/`analytics` are addressed by Docker Compose service name
  in nginx `upstream {}` blocks, which nginx resolves once when it starts —
  not re-resolved if a backend container is recreated independently mid-run.
  Fine for `docker compose up`; a rolling redeploy of one service alone would
  need an `nginx -s reload` (or a `resolver` + variable-based `proxy_pass`)
  to pick up its new IP. See [`../gateway`](../gateway).
- **Docs/schema aren't multiplexed behind the gateway.** Each service's own
  drf-spectacular Swagger UI still assumes it's the only thing on the host —
  fine for shortener/analytics (routed to the fallback `/api/v1/` location),
  but auth's own `/api/v1/docs/` isn't reachable through the gateway at all
  without colliding with shortener's. A real deployment would give each
  service its own subdomain, or run drf-spectacular with an
  `X-Forwarded-Prefix`-aware `SCRIPT_NAME`.
- **Single-host Docker Compose, not Kubernetes.** Enough to prove out
  independent databases and independent deploys. A move to Kubernetes would
  change *how* these run, not the service boundaries themselves.
