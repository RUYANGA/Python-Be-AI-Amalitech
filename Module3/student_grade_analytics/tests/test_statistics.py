"""Tests for :mod:`student_analytics.statistics`."""

from __future__ import annotations

import pytest

from student_analytics.analytics.statistics import GradeStatistics
from student_analytics.models import Student


class TestGradeStatistics:
    def test_empty_scores_produce_zeros(self) -> None:
        stats = GradeStatistics()
        assert stats.mean([]) == 0.0
        assert stats.median([]) == 0.0
        assert stats.mode([]) == 0.0
        assert stats.percentile([], percentile=50.0) == 0.0

    def test_mean_median_mode(self) -> None:
        stats = GradeStatistics()
        scores = [70.0, 80.0, 90.0, 80.0]
        assert stats.mean(scores) == pytest.approx(80.0)
        assert stats.median(scores) == pytest.approx(80.0)
        assert stats.mode(scores) == pytest.approx(80.0)

    def test_mode_tie_returns_smallest(self) -> None:
        stats = GradeStatistics()
        # Both 70 and 90 appear twice — tie broken to smaller value.
        assert stats.mode([70.0, 90.0, 70.0, 90.0]) == pytest.approx(70.0)

    def test_percentile_single_value(self) -> None:
        stats = GradeStatistics()
        assert stats.percentile([85.0], percentile=50.0) == pytest.approx(85.0)

    def test_percentile_boundaries(self) -> None:
        stats = GradeStatistics()
        scores = [10.0, 20.0, 30.0, 40.0, 50.0]
        assert stats.percentile(scores, percentile=0.0) == pytest.approx(10.0)
        assert stats.percentile(scores, percentile=100.0) == pytest.approx(50.0)
        assert stats.percentile(scores, percentile=50.0) == pytest.approx(30.0)

    @pytest.mark.parametrize("bad_percentile", [-1.0, 100.5])
    def test_percentile_rejects_out_of_range(self, bad_percentile: float) -> None:
        with pytest.raises(ValueError, match="percentile must be in"):
            GradeStatistics().percentile([1.0, 2.0], percentile=bad_percentile)

    def test_compute_summary_with_students(self, sample_students: list[Student]) -> None:
        summary = GradeStatistics().compute_summary(sample_students)
        # Scores: 85, 95, 72, 68, 55
        assert summary["highest"] == pytest.approx(95.0)
        assert summary["lowest"] == pytest.approx(55.0)
        assert summary["mean"] == pytest.approx(75.0)
        assert summary["median"] == pytest.approx(72.0)
        assert set(summary) == {
            "mean",
            "median",
            "mode",
            "percentile_25",
            "percentile_75",
            "highest",
            "lowest",
        }

    def test_compute_summary_with_empty_input(self) -> None:
        summary = GradeStatistics().compute_summary([])
        for value in summary.values():
            assert value == 0.0
