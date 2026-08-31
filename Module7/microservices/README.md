# URL Shortener — Microservices Edition

A three-way split of the [Module7](../README.md) monolith into independently
deployable services: **auth**, **shortener**, and **analytics**, each with its
own database, fronted by a single Traefik gateway. This lives alongside the
monolith (`../src/`) as a separate, self-contained implementation — nothing
here touches or depends on it.

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
                    ┌─────────────┐
        clients ──▶ │   Traefik   │  :8090
                    │  (gateway)  │
                    └──────┬──────┘
             ┌─────────────┼─────────────┐
             ▼              ▼              ▼
        ┌────────┐    ┌───────────┐   ┌───────────┐
        │  auth  │    │ shortener │   │ analytics │
        │ :8001  │    │  :8002    │   │  :8003    │
        └───┬────┘    └─────┬─────┘   └─────┬─────┘
            │               │               │
        ┌───▼───┐       ┌───▼───┐       ┌───▼───┐
        │auth-db│       │shortener│     │analytics│
        │  pg   │       │  -db pg │     │  -db pg │
        └───────┘       └────┬────┘     └────┬────┘
                              │               │
                              │   "clicks"     │
                              └──────Kafka─────┘
                                     ▲
                                     │ consumer group
                              ┌──────┴───────┐
                              │analytics-     │
                              │worker         │
                              │(consume_clicks)│
                              └───────────────┘

        shortener  ◀── HTTP (internal, shared-secret) ──  analytics
        "does this short code exist, and who owns it?"
```

### The two cross-service seams, and why each is shaped the way it is

1. **Identity: JWT claims, not a database join.** `auth` signs access tokens
   with an RSA private key (RS256) and embeds `user_id`, `username`,
   `is_premium`, and `tier` as claims. `shortener` and `analytics` verify the
   signature with auth's *public* key (`apps/common/jwt_auth.py`,
   `RemoteJWTAuthentication`) and build a `RemoteUser` straight from the
   claims — no network call to auth, no local `users` table. The trade-off:
   a user's premium upgrade doesn't take effect until their token refreshes
   (access tokens are short-lived — 15 minutes — specifically to bound that
   staleness).

2. **Click tracking: one-way event stream, not a synchronous write.** The
   redirect endpoint (`GET /{short_code}/`) is the highest-traffic,
   unauthenticated, latency-critical path in the system. It must never
   block on — or fail because of — analytics being slow or down. So
   `shortener` publishes a `ClickRecorded` event to a Kafka topic
   (`clicks`) and returns immediately — `produce()` only enqueues the
   message locally; `analytics-worker` consumes it independently via a
   consumer group with manual offset commits (a crash mid-batch just
   redelivers the message on restart instead of silently dropping it)
   and does the geo lookup + write.

3. **The one synchronous call: ownership.** `analytics` has no `urls` table,
   so "does this short code exist, and is it owned by the caller?" (needed
   for `GET /api/v1/analytics/{short_code}/`) is answered by calling
   shortener's internal API (`GET /api/v1/internal/urls/{short_code}/`),
   authenticated with a static shared secret (`INTERNAL_SERVICE_TOKEN`), not
   a user JWT. A failed lookup fails *closed* (treated as "not found"), so a
   down shortener service can't leak anyone's analytics — it just makes
   analytics briefly unavailable too.

## Running it

Two ways to run this, and they're genuinely alternatives — pick one:

**All three services together** (this top-level `docker-compose.yml`), for
integration testing or demoing the whole system through the gateway:

```bash
./scripts/generate_jwt_keys.sh    # once — writes keys/jwt-{private,public}.pem
cp .env.example .env              # then fill in real secrets
docker compose up --build
```

**Each service completely on its own** — its own `docker-compose.yml`, own
database, own Redis/Kafka, nothing else required to start it. This is the
"one team, one service, one checkout" way to run it, and it's how you'd work
on just one service without needing the others up at all:

```bash
./scripts/generate_jwt_keys.sh    # once, from this directory, if keys/ is empty
cd auth                           # or shortener/, or analytics/
cp .env.example .env              # fill in real secrets
docker compose up --build
```

Each standalone service reuses the same container names/ports as its
counterpart in the combined stack, so the two are mutually exclusive —
`docker compose down` whichever is up before starting the other. Verified
this actually works end to end: a token issued by standalone `auth`
validates against standalone `shortener` (they share the same key files on
disk via `../keys`), and standalone `analytics` reaches standalone
`shortener`'s internal ownership endpoint over `host.docker.internal:8002`.
The one thing that *doesn't* cross when each service is fully standalone is
click data — `shortener` and `analytics` each get their own isolated Kafka
broker in that mode, so the `clicks` topic between them has no shared
transport (point both at the same `KAFKA_BOOTSTRAP_SERVERS` if you want
that to work too).

Gateway (what a client/frontend actually talks to): `http://localhost:8090`

Direct per-service access — Swagger UI, debugging, bypasses the gateway:

| Service | Docs |
|---|---|
| auth | http://localhost:8001/api/v1/docs/ |
| shortener | http://localhost:8002/api/v1/docs/ |
| analytics | http://localhost:8003/api/v1/docs/ |

Traefik dashboard (dev only): http://localhost:8091

### Endpoints (through the gateway)

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

`/api/v1/internal/urls/{short_code}/` (shortener) is deliberately **not**
routed through the gateway — it's service-to-service only, reached over the
Docker network directly.

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
table, the plain-integer `owner_id`, the ownership round-trip, the event
publish/consume path), not business logic that hasn't changed.

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
- **One shared Redis** backs the login rate limiter and the URL cache (two
  unrelated per-service concerns, not a message bus — that's Kafka's job
  now). True isolation would give each service its own instance; this is
  the common, pragmatic middle ground as long as key namespaces don't
  collide (`auth:*`, `url:*`).
- **Single-node Kafka (KRaft, no Zookeeper)**, one partition on the `clicks`
  topic. Enough to prove out the fire-and-forget publish / consumer-group
  read pattern; a real deployment would run a proper multi-broker cluster
  with replication.
- **No observability stack.** A request that spans all three services has
  no distributed tracing here — `docker compose logs -f` per-service is the
  debugging story. Adding OpenTelemetry + Jaeger/Tempo would be the natural
  next step, not a redesign.
- **No API gateway auth/rate-limiting plugins.** Traefik here does pure
  routing (static file-based, not Docker-label auto-discovery — the Docker
  socket route hit an API-version mismatch on this host, and file-based
  config is arguably more appropriate for a fixed, small set of routes
  anyway). Each service still enforces its own auth and the login rate
  limiter independently.
- **Single-host Docker Compose, not Kubernetes.** Enough to prove out
  independent databases, independent deploys, and the event-driven
  decoupling. A move to Kubernetes would change *how* these run, not the
  service boundaries themselves.
