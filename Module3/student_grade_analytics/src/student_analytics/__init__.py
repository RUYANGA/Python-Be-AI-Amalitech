"""Student Grade Analytics package.

A SOLID-designed toolkit for parsing student CSV records, computing
statistical summaries with advanced Python collections, and emitting
JSON reports.
"""

from student_analytics.analytics.aggregators import (
    GradeDistributionAggregator,
    OrderedReportAggregator,
    StudentGroupAggregator,
)
from student_analytics.analytics.analyzer import StudentGradeAnalyzer
from student_analytics.analytics.builder import ReportPayloadBuilder
from student_analytics.analytics.metrics import (
    GradeDistributionMetric,
    MetricCalculator,
    RollingAveragesMetric,
    StatisticsMetric,
    StudentsByMajorMetric,
    StudentsByYearMetric,
    TopPerformersMetric,
)
from student_analytics.analytics.rolling_average import RollingAverageCalculator
from student_analytics.analytics.statistics import GradeStatistics
from student_analytics.exceptions import (
    AnalyticsError,
    InvalidGradeError,
    ReportWriteError,
    StudentDataError,
)
from student_analytics.io.readers import CSVStudentReader
from student_analytics.io.writers import JSONReportWriter
from student_analytics.models.models import (
    Course,
    Grade,
    GradeLetter,
    ReportPayload,
    Student,
)

__all__ = [
    "AnalyticsError",
    "CSVStudentReader",
    "Course",
    "Grade",
    "GradeDistributionAggregator",
    "GradeDistributionMetric",
    "GradeLetter",
    "GradeStatistics",
    "InvalidGradeError",
    "JSONReportWriter",
    "MetricCalculator",
    "OrderedReportAggregator",
    "ReportPayload",
    "ReportPayloadBuilder",
    "ReportWriteError",
    "RollingAverageCalculator",
    "RollingAveragesMetric",
    "StatisticsMetric",
    "Student",
    "StudentDataError",
    "StudentGradeAnalyzer",
    "StudentGroupAggregator",
    "StudentsByMajorMetric",
    "StudentsByYearMetric",
    "TopPerformersMetric",
]

__version__ = "1.0.0"
