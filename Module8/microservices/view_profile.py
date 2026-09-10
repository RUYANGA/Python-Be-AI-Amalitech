#!/usr/bin/env python3
"""Pretty-print a profile.log (JSON-lines) file as readable tables.

Usage: ./view_profile.py [path/to/profile.log]
"""

from __future__ import annotations

import json
import sys

_STRIP_PREFIXES = (
    "/opt/venv/lib/python3.12/site-packages/",
    "/app/src/",
    "/usr/local/lib/python3.12/",
)


def _shorten(function: str) -> str:
    for prefix in _STRIP_PREFIXES:
        if function.startswith(prefix):
            return function[len(prefix) :]
    return function


def main(path: str) -> None:
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            profile = record.get("extra", {}).get("profile")
            if not profile:
                continue

            print(f"\n=== {record['timestamp']}  {profile['function']} ===")
            print(
                f"{profile['total_calls']} calls "
                f"({profile['primitive_calls']} primitive), "
                f"{profile['total_time_seconds'] * 1000:.3f} ms total "
                f"(sorted by {profile['sort_by']})"
            )
            print(f"{'function':<65} {'calls':>8} {'tottime':>10} {'cumtime':>10}")
            print("-" * 96)
            for row in profile["rows"]:
                print(
                    f"{_shorten(row['function']):<65} "
                    f"{str(row['calls']):>8} "
                    f"{row['tottime'] * 1000:>8.3f}ms "
                    f"{row['cumtime'] * 1000:>8.3f}ms"
                )


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "shortener/logs/profile.log")
