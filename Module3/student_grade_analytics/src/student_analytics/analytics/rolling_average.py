"""Rolling average calculator built on top of :class:`collections.deque`.

A ``deque`` with a bounded ``maxlen`` provides O(1) appends *and* automatic
eviction of the oldest sample, giving us a memory-bounded windowed mean in
just a few lines of code.
"""

from collections import deque
from collections.abc import Iterable
from typing import Final

from student_analytics.exceptions import InvalidGradeError
from student_analytics.logger import get_logger

_logger = get_logger("rolling_average")


class RollingAverageCalculator:
    """Compute rolling averages over a fixed-size numeric window."""

    def __init__(self, window_size: int) -> None:
        """Initialise the calculator.

        Args:
            window_size: Positive number of samples to retain.

        Raises:
            ValueError: If ``window_size`` is not a positive integer.
        """
        if window_size <= 0:
            raise ValueError(
                f"window_size must be a positive integer; got {window_size!r}."
            )
        self._window_size: Final[int] = window_size
        self._samples: Final[deque[float]] = deque(maxlen=window_size)
        _logger.debug("RollingAverageCalculator created (window=%d)", window_size)

    @property
    def window_size(self) -> int:
        """Return the configured window size."""
        return self._window_size

    @property
    def sample_count(self) -> int:
        """Return the number of samples currently retained."""
        return len(self._samples)

    def add(self, value: int | float) -> float:
        """Push a value into the window and return the updated average.

        Args:
            value: New sample to append. Must be a finite number.

        Returns:
            The mean of every sample currently retained in the window.

        Raises:
            InvalidGradeError: If ``value`` is not a finite number.
        """
        if not isinstance(value, int | float) or isinstance(value, bool):
            raise InvalidGradeError(f"value must be numeric; got {value!r}.")
        self._samples.append(float(value))
        return self.current_average

    def extend(self, values: Iterable[float]) -> list[float]:
        """Add each value from ``values`` and return a list of averages.

        Args:
            values: Iterable of numeric samples to append in order.

        Returns:
            A list containing the rolling average after each sample was
            added. The list is the same length as ``values``.
        """
        return [self.add(value) for value in values]

    @property
    def current_average(self) -> float:
        """Return the mean of samples in the window (``0.0`` when empty)."""
        if not self._samples:
            return 0.0
        return sum(self._samples) / len(self._samples)

    def reset(self) -> None:
        """Discard every sample currently held in the window."""
        self._samples.clear()
        _logger.debug("RollingAverageCalculator reset")

    def snapshot(self) -> list[float]:
        """Return a copy of the samples currently in the window."""
        return list(self._samples)
