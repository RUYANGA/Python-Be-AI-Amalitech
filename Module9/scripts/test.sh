#!/usr/bin/env bash
# Runs each service's test suite the way it's actually meant to run —
# inside its own Docker container, against its own database/Redis/Kafka
# — never as a bare `pytest` on the host.
#
# This can't be a single `pytest` invocation the way linting is a single
# `ruff check` for the whole tree: Django settings are a process-global
# singleton, and each service has its own `config.settings` module, its
# own database, and needs its own container's network to reach its own
# Postgres/Redis/Kafka. That's the same reason mypy (see lint.sh) needs
# one invocation per service — just a harder version of it, since a bare
# host `pytest` also has no Postgres/Redis/Kafka to connect to at all.
set -euo pipefail
cd "$(dirname "$0")/../microservices"

for service in auth shortener analytics; do
  echo "==> pytest ($service)"
  docker compose run --rm "$service" sh -c "pip install -q -r requirements-dev.txt && pytest -q"
done

echo "All tests passed."
