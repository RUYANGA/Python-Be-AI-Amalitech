"""Lightweight profiling decorators for service and repository methods.

Two opt-in helpers are provided:

- ``@profiled`` runs the wrapped method under :mod:`cProfile` and logs the
  top rows by cumulative time. Use it when you need to know not only how
  long something took, but where the time went.
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
import io
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


def profiled(
    enabled: bool | None = None,
    *,
    sort_by: str = "cumulative",
    top_rows: int = _DEFAULT_TOP_ROWS,
) -> Callable[[F], F]:
    """Profile the decorated method with :mod:`cProfile`.

    Logs ``func.__qualname__`` followed by the ``top_rows`` heaviest rows
    (sorted by ``sort_by``) at INFO level.
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
                stream = io.StringIO()
                pstats.Stats(profiler, stream=stream).sort_stats(sort_by).print_stats(top_rows)
                logger.info("profile.%s\n%s", func.__qualname__, stream.getvalue())

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
