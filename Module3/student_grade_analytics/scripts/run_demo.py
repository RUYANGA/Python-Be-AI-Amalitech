"""End-to-end demo script for the student analytics tool.

Reads the sample CSV file and writes a JSON report using the default
pipeline configuration.
"""

from __future__ import annotations

import logging
from pathlib import Path

from student_analytics import (
    CSVStudentReader,
    JSONReportWriter,
    StudentGradeAnalyzer,
)
from student_analytics.logger import configure_logging

PROJECT_ROOT_DIRECTORY = Path(__file__).resolve().parent.parent
SOURCE_CSV_FILE_PATH = PROJECT_ROOT_DIRECTORY / "data" / "sample_students.csv"
DESTINATION_JSON_FILE_PATH = PROJECT_ROOT_DIRECTORY / "reports" / "report.json"


def main() -> None:
    """Run the demo pipeline and print a summary line."""
    configure_logging(level=logging.INFO)
    pipeline_analyzer = StudentGradeAnalyzer(
        reader=CSVStudentReader(SOURCE_CSV_FILE_PATH),
        writer=JSONReportWriter(DESTINATION_JSON_FILE_PATH),
    )
    report_payload = pipeline_analyzer.run()
    print(
        f"Generated analytics report for {report_payload['total_students']} students "
        f"-> {DESTINATION_JSON_FILE_PATH.relative_to(PROJECT_ROOT_DIRECTORY)}"
    )


if __name__ == "__main__":
    main()
