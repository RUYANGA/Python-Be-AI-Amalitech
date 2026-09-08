#!/usr/bin/env bash
# Lints and type-checks all three microservices from one place, using
# the shared config in pyproject.toml.
#
# ruff and black work per-file, so they run across the whole tree in
# one shot. mypy builds a cross-file module graph, and each service
# defines its own top-level apps/config packages — pointing it at all
# three trees in a single invocation fails with "Duplicate module named
# 'apps'" — so it runs once per service instead, each scoped to just
# that service's src/.
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHON=.venv/bin/python
[ -x "$PYTHON" ] || { echo "No .venv found — run: python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt" >&2; exit 1; }

echo "==> ruff"
.venv/bin/ruff check microservices

echo "==> black --check"
.venv/bin/black --check microservices

for service in auth shortener analytics; do
  echo "==> mypy ($service)"
  .venv/bin/mypy --config-file=pyproject.toml "microservices/$service/src"
done

echo "All checks passed."
