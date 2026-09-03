# API Gateway

The single front door for **client** traffic in the URL-shortener
microservices split ([`../microservices`](../microservices)). `auth`,
`shortener`, and `analytics` publish no host ports of their own; they're
reachable only from inside the Docker network this gateway also sits on.
Service-to-service calls (the shortener ownership lookup, click ingestion)
deliberately do **not** go through here — see
[Service-to-service traffic](#service-to-service-traffic).

This is a plain `nginx:alpine` image (see the `gateway` service in
[`../microservices/docker-compose.yml`](../microservices/docker-compose.yml))
configured by the single file in this folder — [`nginx.conf`](nginx.conf) —
using the official image's built-in `/etc/nginx/templates/*.template`
`envsubst` mechanism. Compose bind-mounts it into the container as
`/etc/nginx/templates/default.conf.template` (not `nginx.conf.template`)
specifically so the generated file lands at `/etc/nginx/conf.d/default.conf`,
*replacing* the base image's own demo server block on `:80` instead of
running alongside it as a second, competing one. There's no custom
Dockerfile for it, and no other config file in this folder.

## Routing table

| Path prefix | Routed to | Gated by `auth_request`? |
|---|---|---|
| `/api/v1/auth/` | auth | No — this *is* how you get a token |
| `/admin/` | auth (Django admin) | No |
| `/api/docs/<service>/`, `/api/schema/<service>/` | that service | No |
| `/api/v1/urls/` | shortener | **Yes** |
| `/api/v1/analytics/` | analytics | **Yes** |
| `/api/v1/internal/`, `/internal/` | — | Blocked (`404`) — see below |
| `/api/v1/` (everything else — resolve) | shortener | No |
| `/` (the short link itself, e.g. `/abc123`) | shortener | No |

Backend hostnames (`auth`, `shortener`, `analytics`) are resolved per
request via Docker's embedded DNS (`resolver 127.0.0.11`) combined with
`set $var http://service:port; proxy_pass $var...;`, rather than once at
nginx startup — so a container recreated independently mid-run doesn't
leave nginx proxying to a stale IP.

## Centralized authentication (`auth_request`)

Before, `shortener` and `analytics` each verified a caller's JWT themselves,
independently, on every request — a REST call to auth's internal endpoint
from inside each service (`apps.common.jwt_auth.RemoteJWTAuthentication`,
now removed). That verification now happens **once, here**, using nginx's
[`auth_request`](https://nginx.org/en/docs/http/ngx_http_auth_request_module.html)
module:

1. A request to a protected location (`/api/v1/urls/`, `/api/v1/analytics/`)
   triggers an internal subrequest to `/internal/verify`.
2. That subrequest proxies to auth's
   `GET /api/v1/auth/internal/token/validate/` — forwarding the client's
   `Authorization` header, plus the shared `X-Internal-Token` secret nginx
   itself attaches (`auth_request` subrequests carry headers but never a
   body, so the token travels as `Authorization: Bearer <token>`, not JSON).
3. Auth returns **401**/**403** for anything invalid, or **200** with the
   identity claims as response headers (`X-User-Id`, `X-Username`,
   `X-User-Tier`, `X-User-Is-Premium`) for a valid token.
4. `auth_request_set` captures those headers into nginx variables, which are
   then forwarded to the upstream via `proxy_set_header` — **replacing**
   whatever the original client sent under those same header names, so a
   client can't forge its own identity headers.
5. `shortener`/`analytics` read them via
   `apps.<service>.api.authentication.GatewayAuthentication` — no network
   call, no local JWT decoding, on every request.

A 401/403 from the subrequest short-circuits the whole request via
`error_page 401 403 = @unauthorized`, returning a small JSON body before the
request ever reaches shortener or analytics.

## Service-to-service traffic

The shortener→analytics click-event delivery and analytics→shortener
ownership lookup are **not** proxied here — they call each other directly,
container-to-container, over the same internal Docker network
(`http://shortener:8000`, `http://analytics:8000`; see each service's
`SHORTENER_SERVICE_URL`/`ANALYTICS_SERVICE_URL`). They're authenticated with
the shared `X-Internal-Token` header (checked by Django's own
`HasInternalServiceToken` permission) rather than a user's JWT, so they gain
nothing from this gateway's `auth_request` check — routing them through here
too would just be an extra hop. `/api/v1/internal/` and `/internal/` are
explicitly blocked (`404`) at the gateway rather than left to fall through
to some other service's routes by accident.

## Known simplification

Docs/schema aren't multiplexed under a single path for each service the way
`/api/v1/urls/`, etc. are — each service's own drf-spectacular Swagger UI
assumes it's the only thing on the host, so all three define docs at the
same literal `/api/v1/docs/` path. The `/api/docs/<service>/` and
`/api/schema/<service>/` routes work around that with a `rewrite`, but a
generated schema that references *other* absolute paths (rare, but
possible) could still point at the wrong place. A real deployment fronting
a browser client heavily would give each service its own subdomain instead.
