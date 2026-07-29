"""End-to-end demo script for the student analytics tool.

Reads ``data/sample_students.csv`` and writes ``reports/report.json`` using
the default pipeline configuration.
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

ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH = ROOT / "data" / "sample_students.csv"
OUTPUT_PATH = ROOT / "reports" / "report.json"


def main() -> None:
    """Run the demo pipeline and print a summary line."""
    configure_logging(level=logging.INFO)
    analyzer = StudentGradeAnalyzer(
        reader=CSVStudentReader(INPUT_PATH),
        writer=JSONReportWriter(OUTPUT_PATH),
    )
    report = analyzer.run()
    print(
        f"Generated analytics report for {report['total_students']} students "
        f"-> {OUTPUT_PATH.relative_to(ROOT)}"
    )


if __name__ == "__main__":
    main()
