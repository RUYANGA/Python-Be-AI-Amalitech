"""Analytics — re-exports all public symbols from the analytics sub-package."""

from student_analytics.analytics.aggregators import (
    GradeDistributionAggregator,
    OrderedReportAggregator,
    StudentGroupAggregator,
)
from student_analytics.analytics.analyzer import (
    DEFAULT_ROLLING_WINDOW_SIZE,
    DEFAULT_TOP_PERFORMER_LIMIT,
    StudentGradeAnalyzer,
)
from student_analytics.analytics.rolling_average import RollingAverageCalculator
from student_analytics.analytics.statistics import GradeStatistics

__all__ = [
    "DEFAULT_ROLLING_WINDOW_SIZE",
    "DEFAULT_TOP_PERFORMER_LIMIT",
    "GradeDistributionAggregator",
    "GradeStatistics",
    "OrderedReportAggregator",
    "RollingAverageCalculator",
    "StudentGradeAnalyzer",
    "StudentGroupAggregator",
]
