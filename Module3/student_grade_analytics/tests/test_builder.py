"""Tests for :mod:`student_analytics.analytics.builder`."""

from typing import cast

import pytest

from student_analytics.analytics.builder import ReportPayloadBuilder
from student_analytics.analytics.metrics import (
    GradeDistributionMetric,
    MetricCalculator,
    StatisticsMetric,
    build_default_metrics,
)
from student_analytics.models import Student


class CustomMetric:
    """A user-defined metric demonstrating the Open/Closed Principle."""

    key = "custom"

    def compute(self, students: list[Student]) -> object:
        return len(students)


class TestReportPayloadBuilder:
    def test_build_merges_every_metric(self, sample_students: list[Student]) -> None:
        metrics = build_default_metrics(top_performer_limit=2, rolling_window_size=2)
        builder = ReportPayloadBuilder(metrics=metrics)
        payload = builder.build(sample_students)
        assert payload["total_students"] == 3
        assert payload["generated_at"].endswith("+00:00")
        assert payload["grade_distribution"]["A"] == 1
        assert len(payload["top_performers"]) == 2

    def test_build_includes_custom_metric(self, sample_students: list[Student]) -> None:
        builder = ReportPayloadBuilder(metrics=[CustomMetric(), StatisticsMetric()])
        payload = builder.build(sample_students)
        assert cast("dict[str, object]", payload)["custom"] == 3
        assert "statistics" in payload

    def test_rejects_empty_metrics(self) -> None:
        with pytest.raises(ValueError, match="At least one metric"):
            ReportPayloadBuilder()

    def test_rejects_empty_metrics_list(self) -> None:
        with pytest.raises(ValueError, match="At least one metric"):
            ReportPayloadBuilder(metrics=[])

    def test_rejects_duplicate_metric_keys(self) -> None:
        with pytest.raises(ValueError, match="must be unique"):
            ReportPayloadBuilder(metrics=[GradeDistributionMetric(), GradeDistributionMetric()])

    def test_accepts_custom_metrics_without_validation_error(self) -> None:
        builder = ReportPayloadBuilder(metrics=[CustomMetric()])
        assert isinstance(builder, ReportPayloadBuilder)
        assert isinstance(CustomMetric(), MetricCalculator)
