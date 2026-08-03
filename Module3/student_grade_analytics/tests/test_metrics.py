"""Tests for :mod:`student_analytics.analytics.metrics`."""

import pytest

from student_analytics.analytics.metrics import (
    GradeDistributionMetric,
    MetricCalculator,
    RollingAveragesMetric,
    StatisticsMetric,
    StudentsByMajorMetric,
    StudentsByYearMetric,
    TopPerformersMetric,
    build_default_metrics,
    ensure_unique_metric_keys,
)
from student_analytics.models import Student


class TestGradeDistributionMetric:
    def test_default_aggregator(self, sample_students: list[Student]) -> None:
        metric = GradeDistributionMetric()
        result = metric.compute(sample_students)
        assert result["A"] == 1  # 95.0
        assert result["F"] == 1  # 55.0

    def test_custom_aggregator(self, sample_students: list[Student]) -> None:
        from student_analytics.analytics.aggregators import GradeDistributionAggregator

        metric = GradeDistributionMetric(aggregator=GradeDistributionAggregator())
        assert metric.compute(sample_students)["B"] == 1  # 85.0

    def test_empty_input_has_all_letters(self) -> None:
        result = GradeDistributionMetric().compute([])
        assert result == {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}


class TestStudentsByMajorMetric:
    def test_default_aggregator(self, sample_students: list[Student]) -> None:
        metric = StudentsByMajorMetric()
        assert metric.compute(sample_students) == {
            "CS": ["S001", "S003"],
            "MATH": ["S002"],
        }

    def test_custom_aggregator(self, sample_students: list[Student]) -> None:
        from student_analytics.analytics.aggregators import StudentGroupAggregator

        metric = StudentsByMajorMetric(aggregator=StudentGroupAggregator())
        assert metric.compute(sample_students)["MATH"] == ["S002"]


class TestStudentsByYearMetric:
    def test_default_aggregator(self, sample_students: list[Student]) -> None:
        metric = StudentsByYearMetric()
        assert metric.compute(sample_students) == {
            "1": ["S003"],
            "2": ["S001"],
            "3": ["S002"],
        }

    def test_custom_aggregator(self, sample_students: list[Student]) -> None:
        from student_analytics.analytics.aggregators import StudentGroupAggregator

        metric = StudentsByYearMetric(aggregator=StudentGroupAggregator())
        assert metric.compute(sample_students)["3"] == ["S002"]


class TestTopPerformersMetric:
    def test_default_aggregator(self, sample_students: list[Student]) -> None:
        metric = TopPerformersMetric()
        result = metric.compute(sample_students)
        assert result[0] == {"student_id": "S001", "gpa": 90.0}

    def test_custom_aggregator_and_limit(self, sample_students: list[Student]) -> None:
        from student_analytics.analytics.aggregators import OrderedReportAggregator

        metric = TopPerformersMetric(aggregator=OrderedReportAggregator(), limit=1)
        assert len(metric.compute(sample_students)) == 1

    def test_gpas_are_rounded(self, sample_students: list[Student]) -> None:
        metric = TopPerformersMetric()
        assert metric.compute(sample_students)[0]["gpa"] == 90.0


class TestStatisticsMetric:
    def test_default_calculator(self, sample_students: list[Student]) -> None:
        metric = StatisticsMetric()
        assert metric.compute(sample_students)["mean"] == 75.0

    def test_custom_calculator(self, sample_students: list[Student]) -> None:
        from student_analytics.analytics.statistics import GradeStatistics

        metric = StatisticsMetric(statistics=GradeStatistics())
        assert metric.compute(sample_students)["highest"] == 95.0


class TestRollingAveragesMetric:
    def test_compute_orders_grades_by_semester(self, sample_students: list[Student]) -> None:
        metric = RollingAveragesMetric(window_size=2)
        # S001: Fall2023=85, Spring2024=95 -> rolling: [85.0, 90.0]
        assert metric.compute(sample_students)["S001"] == pytest.approx([85.0, 90.0])


class TestBuildDefaultMetrics:
    def test_returns_all_six_metric_sections(self) -> None:
        metrics = build_default_metrics(top_performer_limit=5, rolling_window_size=3)
        assert len(metrics) == 6
        assert {metric.key for metric in metrics} == {
            "grade_distribution",
            "students_by_major",
            "students_by_year",
            "top_performers",
            "statistics",
            "rolling_averages",
        }

    def test_every_metric_conforms_to_protocol(self) -> None:
        metrics = build_default_metrics(top_performer_limit=5, rolling_window_size=3)
        assert all(isinstance(metric, MetricCalculator) for metric in metrics)


class TestEnsureUniqueMetricKeys:
    def test_unique_keys_pass(self) -> None:
        ensure_unique_metric_keys([GradeDistributionMetric(), StatisticsMetric()])

    def test_duplicate_keys_raise(self) -> None:
        with pytest.raises(ValueError, match="must be unique"):
            ensure_unique_metric_keys([GradeDistributionMetric(), GradeDistributionMetric()])
