"""Tests for :mod:`student_analytics.rolling_average`."""

from __future__ import annotations

import pytest

from student_analytics.analytics.rolling_average import RollingAverageCalculator
from student_analytics.exceptions import InvalidGradeError


class TestRollingAverageCalculator:
    @pytest.mark.parametrize("bad_window", [0, -1, -50])
    def test_non_positive_window_raises(self, bad_window: int) -> None:
        with pytest.raises(ValueError, match="window_size must be a positive integer"):
            RollingAverageCalculator(window_size=bad_window)

    def test_window_size_and_initial_state(self) -> None:
        rolling_calculator = RollingAverageCalculator(window_size=3)
        assert rolling_calculator.window_size == 3
        assert rolling_calculator.sample_count == 0
        assert rolling_calculator.current_average == 0.0
        assert rolling_calculator.snapshot() == []

    def test_add_returns_updated_average(self) -> None:
        rolling_calculator = RollingAverageCalculator(window_size=3)
        assert rolling_calculator.add(80.0) == pytest.approx(80.0)
        assert rolling_calculator.add(90.0) == pytest.approx(85.0)
        assert rolling_calculator.add(70.0) == pytest.approx(80.0)

    def test_window_eviction(self) -> None:
        rolling_calculator = RollingAverageCalculator(window_size=2)
        rolling_calculator.add(80.0)
        rolling_calculator.add(90.0)
        average = rolling_calculator.add(70.0)  # 80.0 is evicted
        assert average == pytest.approx(80.0)
        assert rolling_calculator.snapshot() == [90.0, 70.0]

    def test_extend_returns_running_averages(self) -> None:
        rolling_calculator = RollingAverageCalculator(window_size=2)
        averages = rolling_calculator.extend([80.0, 90.0, 100.0])
        assert averages == pytest.approx([80.0, 85.0, 95.0])

    def test_rejects_non_numeric_input(self) -> None:
        rolling_calculator = RollingAverageCalculator(window_size=2)
        with pytest.raises(InvalidGradeError):
            rolling_calculator.add("hello")  # type: ignore[arg-type]

    def test_rejects_boolean_input(self) -> None:
        rolling_calculator = RollingAverageCalculator(window_size=2)
        # bool is a subclass of int but semantically inappropriate as a grade.
        with pytest.raises(InvalidGradeError):
            rolling_calculator.add(True)  # type: ignore[arg-type]

    def test_reset_clears_samples(self) -> None:
        rolling_calculator = RollingAverageCalculator(window_size=3)
        rolling_calculator.extend([80.0, 90.0, 70.0])
        assert rolling_calculator.sample_count == 3
        rolling_calculator.reset()
        assert rolling_calculator.sample_count == 0
        assert rolling_calculator.current_average == 0.0

    def test_accepts_ints(self) -> None:
        rolling_calculator = RollingAverageCalculator(window_size=2)
        assert rolling_calculator.add(80) == pytest.approx(80.0)
        assert rolling_calculator.add(90) == pytest.approx(85.0)
