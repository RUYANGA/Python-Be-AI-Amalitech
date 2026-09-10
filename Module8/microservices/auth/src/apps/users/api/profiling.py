"""Lightweight profiling decorators for service and repository methods.

Two opt-in helpers are provided:

- ``@profiled`` runs the wrapped method under :mod:`cProfile` and logs the
  top rows by cumulative time as structured data (under the ``profile``
  key), so log lines stay valid, parseable JSON instead of an embedded
  text table. Use it when you need to know not only how long something
  took, but where the time went.
- ``@timed`` is the cheap, inline alternative: it logs a single
  elapsed-time line per call with no cProfile overhead. Suitable for hot
  paths where profiling would distort the measurement.

Both are no-ops when disabled, so they can stay on the hot path in
production. They are enabled by passing ``enabled=True`` explicitly, or by
default when ``settings.DEBUG`` (or ``settings.PROFILING_ENABLED``) is
truthy.
"""

from __future__ import annotations

import cProfile
import functools
import logging
import pstats
import time
from collections.abc import Callable
from typing import Any, TypeVar, cast

from django.conf import settings

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

_DEFAULT_TOP_ROWS: int = 15
_WARNING_MS: float = 50.0


def _is_enabled(enabled: bool | None) -> bool:
    if enabled is not None:
        return enabled
    return bool(getattr(settings, "PROFILING_ENABLED", getattr(settings, "DEBUG", False)))


def _stats_rows(stats: pstats.Stats, top_rows: int) -> list[dict[str, Any]]:
    """Return the ``top_rows`` heaviest functions, in ``stats``'s sorted order, as plain dicts."""
    rows = []
    for filename, lineno, funcname in stats.fcn_list[:top_rows]:
        call_count, num_calls, tottime, cumtime = stats.stats[(filename, lineno, funcname)][:4]
        rows.append(
            {
                "function": f"{filename}:{lineno}({funcname})",
                "calls": num_calls if call_count == num_calls else f"{num_calls}/{call_count}",
                "tottime": round(tottime, 6),
                "percall_tottime": round(tottime / num_calls, 6) if num_calls else 0.0,
                "cumtime": round(cumtime, 6),
                "percall_cumtime": round(cumtime / call_count, 6) if call_count else 0.0,
            }
        )
    return rows


def profiled(
    enabled: bool | None = None,
    *,
    sort_by: str = "cumulative",
    top_rows: int = _DEFAULT_TOP_ROWS,
) -> Callable[[F], F]:
    """Profile the decorated method with :mod:`cProfile`.

    Logs ``func.__qualname__`` at INFO level, with the ``top_rows`` heaviest
    rows (sorted by ``sort_by``) attached as structured data under the
    ``profile`` key — see :class:`config.json_logging.JSONFormatter`.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not _is_enabled(enabled):
                return func(*args, **kwargs)
            profiler = cProfile.Profile()
            try:
                return profiler.runcall(func, *args, **kwargs)
            finally:
                stats = pstats.Stats(profiler).sort_stats(sort_by)
                logger.info(
                    "profile.%s",
                    func.__qualname__,
                    extra={
                        "profile": {
                            "function": func.__qualname__,
                            "sort_by": sort_by,
                            "total_calls": stats.total_calls,
                            "primitive_calls": stats.prim_calls,
                            "total_time_seconds": round(stats.total_tt, 6),
                            "rows": _stats_rows(stats, top_rows),
                        }
                    },
                )

        return cast(F, wrapper)

    return decorator


def timed(enabled: bool | None = None, *, warning_ms: float = _WARNING_MS) -> Callable[[F], F]:
    """Log the elapsed wall time of the decorated method.

    Calls slower than ``warning_ms`` are logged at WARNING level, faster
    ones at DEBUG level, so slow queries stand out without flooding logs.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not _is_enabled(enabled):
                return func(*args, **kwargs)
            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                elapsed_ms = (time.perf_counter() - start) * 1000.0
                log = logger.warning if elapsed_ms >= warning_ms else logger.debug
                log("timed.%s elapsed_ms=%.3f", func.__qualname__, elapsed_ms)

        return cast(F, wrapper)

    return decorator
