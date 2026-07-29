"""Command-line interface for the student analytics tool.

The CLI wires the full pipeline together: it parses arguments with
:mod:`argparse`, instantiates the CSV reader and JSON writer, builds the
:class:`StudentGradeAnalyzer`, and invokes it. Exit codes follow the
convention ``0`` for success, ``1`` for application errors, and ``2`` for
argument-parsing failures.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from student_analytics.analytics.analyzer import (
    DEFAULT_ROLLING_WINDOW_SIZE,
    DEFAULT_TOP_PERFORMER_LIMIT,
    StudentGradeAnalyzer,
)
from student_analytics.exceptions import AnalyticsError
from student_analytics.io.readers import CSVStudentReader
from student_analytics.io.writers import JSONReportWriter
from student_analytics.logger import configure_logging, get_logger

_logger = get_logger("cli")


def build_parser() -> argparse.ArgumentParser:
    """Build and return the top-level :class:`argparse.ArgumentParser`."""
    parser = argparse.ArgumentParser(
        prog="student-analytics",
        description=("Process student grades from a CSV file and produce a JSON analytics report."),
    )
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        required=True,
        help="Path to the input CSV file containing student grades.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        required=True,
        help="Path to write the JSON report to.",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=DEFAULT_TOP_PERFORMER_LIMIT,
        help="Number of top-performing students to include in the report.",
    )
    parser.add_argument(
        "--window",
        type=int,
        default=DEFAULT_ROLLING_WINDOW_SIZE,
        help="Window size for the rolling-average calculator.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable DEBUG-level logging.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.

    Args:
        argv: Optional argument vector, primarily useful in tests. When
            ``None`` the arguments are read from :data:`sys.argv`.

    Returns:
        Process exit code: ``0`` on success, ``1`` on a controlled failure,
        ``2`` when argument parsing fails.
    """
    parser = build_parser()
    parsed_arguments = parser.parse_args(argv)
    configure_logging(level=logging.DEBUG if parsed_arguments.verbose else logging.INFO)

    student_reader = CSVStudentReader(path=parsed_arguments.input)
    report_writer = JSONReportWriter(path=parsed_arguments.output)
    analyzer = StudentGradeAnalyzer(
        reader=student_reader,
        writer=report_writer,
        top_performer_limit=parsed_arguments.top,
        rolling_window_size=parsed_arguments.window,
    )
    try:
        payload = analyzer.run()
    except AnalyticsError as error:
        _logger.error("Analytics pipeline failed: %s", error)
        return 1
    _logger.info(
        "Report generated for %d students -> %s",
        payload["total_students"],
        parsed_arguments.output,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
