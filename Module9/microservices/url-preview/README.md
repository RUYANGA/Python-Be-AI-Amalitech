# URL Preview Service

Fetches title/description/favicon for a destination URL, resiliently (retry
with backoff, plus a Redis-backed circuit breaker per domain). Has no
`users` table, no domain tables at all, and no client-facing endpoint — it
exists purely to be called internally by `shortener` right after a URL is
created.

| Owns | Never touches |
|---|---|
| Preview-fetch logic (retry/backoff, SSRF guard, per-domain circuit breaker), the result cache | `urls`/`tags` tables, users, click data |

## How this service depends on / is depended on by others

- **Is called by `shortener` directly**: shortener POSTs the destination URL
  here after creating a shortened link, fire-and-forget via Celery — see
  `shortener/README.md`. This is the only caller; there is no client-facing
  route for the fetch endpoint at all (not even through the gateway).
- **Calls arbitrary destination sites**: the one outbound network call this
  service makes is the actual preview fetch (`HTMLPreviewFetcher`), against
  whatever URL the caller submits — see the SSRF guard below for why that's
  treated as untrusted input.
- **Trusts nothing about identity**: unlike `shortener`/`analytics`, this
  service has no JWT, no gateway-forwarded headers, and no local users table
  at all — its only route is gated purely by a shared internal token.

## API

Base path: `/api/v1/` (web process, port 8000 in-container; not routed
through the gateway at all, since it's never called by a browser/client —
reachable directly at `localhost:8003`, loopback-only, for debugging).

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/internal/preview/` | `X-Internal-Token` | Fetch title/description/favicon for `{"url": ...}` |
| `GET` | `/health/` | Public | Liveness/readiness — DB + Redis check, `200`/`503` |

Interactive docs: `/api/v1/docs/` (Swagger UI), `/api/v1/redoc/`. The
internal endpoint is excluded from both — it's not for browser/client use.

## Business logic worth knowing about

- **`PreviewService`** (`apps.preview.api.services.preview_service`) is the
  orchestrator: validates the URL, guards against SSRF, checks a short
  result cache, consults the circuit breaker, then retries the fetch.
- **SSRF guard**: before any network call, `PreviewService` resolves the
  submitted URL's hostname (`socket.getaddrinfo`) and rejects it
  (`InvalidURLError`) if any resolved address is private, loopback,
  link-local, reserved, or multicast (`ipaddress.ip_address(...).is_*`) — a
  DNS resolution failure is also wrapped as `InvalidURLError` rather than
  leaking a raw socket exception. This matters because this service fetches
  arbitrary attacker-influenceable URLs into the internal Docker network; a
  URL pointed at `169.254.169.254` or `127.0.0.1` never reaches
  `requests.get`.
- **Retry with backoff** (`call_with_backoff`,
  `apps.preview.api.services.retry`): a single fetch attempt lives in
  `HTMLPreviewFetcher` and never retries itself; `PreviewService` wraps it
  in up to `PREVIEW_MAX_ATTEMPTS` (default `3`) tries, sleeping
  `PREVIEW_RETRY_BASE_DELAY * 2**attempt + random.uniform(0,
  PREVIEW_RETRY_BASE_DELAY)` seconds between them (exponential backoff with
  jitter, so a burst of retries against the same flaky domain doesn't
  synchronize into a thundering herd).
- **`DomainCircuitBreaker`** (`apps.preview.api.services.circuit_breaker`):
  Redis-backed, keyed per domain, shared across replicas. A domain's
  failure counter (`preview:circuit:fail:{domain}`, sliding ~120s window)
  reaching `PREVIEW_CIRCUIT_FAILURE_THRESHOLD` (default `5`) opens the
  circuit (`preview:circuit:open:{domain}`) for `PREVIEW_CIRCUIT_OPEN_SECONDS`
  (default `60`) — while open, `PreviewService.fetch` raises
  `CircuitOpenError` immediately, with **no network call at all**. Once the
  open-key's TTL expires, the next call is naturally allowed through again
  as a trial ("half-open"). A success (`record_success`) clears both the
  open-key and the failure counter outright.
- **Result cache**: a successful fetch is cached at
  `preview:cache:{sha256(url)}` for `PREVIEW_CACHE_TTL` seconds (default
  `600`) — failures are never cached, so a transient outage doesn't get
  "stuck" negative.
- **HTML parsing** (`HTMLPreviewFetcher`): one streamed `GET`, capped at
  `PREVIEW_MAX_BODY_BYTES` (default 2MB) so a huge or slow-drip response
  body can't exhaust memory or hold a worker open. Parsed with
  `BeautifulSoup(html, "html.parser")` (stdlib parser backend, no `lxml`
  dependency): `<title>`, then `<meta property="og:description">` falling
  back to `<meta name="description">`, then `<link rel="icon">`/`<link
  rel="shortcut icon">` falling back to `{scheme}://{netloc}/favicon.ico`.
  Any failure — a network error, a non-2xx response, or a non-HTML
  `Content-Type` — raises `PreviewFetchError`.

## Known simplifications

- This service is provisioned with its own Postgres database (`url_preview`)
  for parity with `auth`/`shortener`/`analytics` (the shared `Dockerfile`
  unconditionally runs `manage.py migrate` on start), but has **no domain
  tables of its own** — it's stateless beyond Redis (the result cache and
  the circuit breaker's state). The migration that runs is just Django's
  own `contenttypes`.
- No re-fetch on edit: `shortener` only triggers a preview fetch on URL
  *creation*, not when `original_url` is later changed via `PATCH` — see
  `shortener/README.md`'s own "Known simplifications".

## Environment variables

| Var | Default | Purpose |
|---|---|---|
| `DEBUG` | `True` | Django debug mode |
| `SECRET_KEY` | *(required)* | Django secret key |
| `ALLOWED_HOSTS` | `*` | Comma-separated allowed hosts |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` | *(required)* | Postgres connection |
| `REDIS_URL` | `redis://127.0.0.1:6379/0` | Backs the result cache and the circuit breaker |
| `INTERNAL_SERVICE_TOKEN` | `""` | Shared secret gating the internal preview-fetch endpoint — must match shortener's copy |
| `PREVIEW_FETCH_TIMEOUT` | `5.0` | Per-attempt HTTP request timeout, in seconds |
| `PREVIEW_MAX_ATTEMPTS` | `3` | Retry attempts per fetch, including the first |
| `PREVIEW_RETRY_BASE_DELAY` | `0.5` | Base delay for exponential backoff between attempts, in seconds |
| `PREVIEW_MAX_BODY_BYTES` | `2000000` | Cap on the response body read per fetch |
| `PREVIEW_CIRCUIT_FAILURE_THRESHOLD` | `5` | Failures (within the sliding window) before a domain's circuit opens |
| `PREVIEW_CIRCUIT_OPEN_SECONDS` | `60` | How long an open circuit blocks a domain before the next trial call |
| `PREVIEW_CACHE_TTL` | `600` | How long a successful fetch result is cached, in seconds |

## Logs

One structured JSON object per line (`config/json_logging.py`), written to
stdout (`docker compose logs -f url-preview`) and, alongside that, to
`logs/url-preview.log` on disk — rotated at 10MB, keeping 5 backups. `500`s
(`django.request`) and security warnings (`django.security.*`) are logged
explicitly so neither is silently dropped.

## Running it

Part of the single combined stack — see [`../README.md`](../README.md):

```bash
cd ..                              # microservices/
cp .env.example .env               # fill in real secrets
docker compose up --build
```

Isn't reachable through the gateway at all — from other containers, only
over the internal Docker network (`http://url-preview:8000`); from the host
machine, at `http://localhost:8003/` for debugging only (loopback-only host
port, see
[`../README.md`](../README.md#direct-per-service-access-debugging-only)).

## Tests

```bash
cd ..                              # microservices/
docker compose run --rm url-preview sh -c "pip install -r requirements-dev.txt && pytest -q"
```

`test_html_preview_fetcher.py` covers title/description/favicon extraction,
missing-meta-description and missing-favicon fallbacks, non-HTML
content-types, and non-2xx/connection-error failures. `test_circuit_breaker.py`
proves a domain's circuit opens after `PREVIEW_CIRCUIT_FAILURE_THRESHOLD`
consecutive failures and closes again on a success. `test_preview_service.py`
covers retry-then-succeed, retry-exhausted, a short-circuited call while the
breaker is open (the fetcher is never invoked), and the SSRF guard rejecting
a private-IP target. `test_smoke.py` proves the internal endpoint end-to-end:
a missing `X-Internal-Token` is rejected (403), a valid token with a mocked
fetch returns 200 with the expected JSON shape.
