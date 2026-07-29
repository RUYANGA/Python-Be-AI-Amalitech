#!/usr/bin/env python3
"""Professional CLI report for the Student Grade Analytics Tool.

Usage:
    python scripts/run_report.py --input data/sample_students.csv

Displays a formatted analytics report directly in the terminal using
the existing analysis pipeline.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from student_analytics.analytics.aggregators import (
    GradeDistributionAggregator,
    OrderedReportAggregator,
    StudentGroupAggregator,
)
from student_analytics.analytics.rolling_average import RollingAverageCalculator
from student_analytics.analytics.statistics import GradeStatistics
from student_analytics.exceptions import AnalyticsError
from student_analytics.io.readers import CSVStudentReader
from student_analytics.models import GradeLetter, Student

W = 72


def sep(char: str = "=") -> None:
    """Print a horizontal separator line."""
    print(char * W)


def heading(text: str) -> None:
    """Print a section heading with separators."""
    sep()
    print(f"  {text}")
    sep()


def bar(value: int, total: int, width: int = 30) -> str:
    """Return an ASCII bar representing ``value/total``."""
    filled = int(width * value / total) if total else 0
    return "█" * filled + "░" * (width - filled)


def fmt(name: str, value: object, suffix: str = "") -> None:
    """Print a formatted key-value pair."""
    print(f"  {name:<30} {value!s:>10}{suffix}")


def show_overview(students: list[Student]) -> None:
    """Print total student / grade counts and GPA extremes."""
    heading("OVERVIEW")
    total_grades = sum(len(s.grades) for s in students)
    fmt("Total students", len(students))
    fmt("Total grades", total_grades)
    majors = Counter(s.major for s in students)
    fmt("Unique majors", len(majors))
    years = Counter(s.year for s in students)
    fmt("Year groups", len(years))
    avg_gpa = sum(s.gpa for s in students) / len(students) if students else 0.0
    fmt("Average GPA (all)", f"{avg_gpa:.2f}")
    high = max(s.gpa for s in students) if students else 0.0
    low = min(s.gpa for s in students) if students else 0.0
    fmt("Highest GPA", f"{high:.2f}")
    fmt("Lowest GPA", f"{low:.2f}")
    print()


def show_grade_distribution(students: list[Student]) -> None:
    """Print a letter-grade histogram with counts and percentages."""
    heading("GRADE DISTRIBUTION")
    agg = GradeDistributionAggregator()
    distro = agg.aggregate(students)
    total = sum(distro.values())
    print(f"  {'Letter':<8} {'Count':<8} {'%':<8}  Distribution")
    sep("-")
    for letter in GradeLetter:
        count = distro[letter]
        pct = 100.0 * count / total if total else 0.0
        print(f"  {letter.value:<8} {count:<8} {pct:>6.1f}%  {bar(count, total)}")
    sep("-")
    print(f"  {'TOTAL':<8} {total:<8} {'100.0%':<8}")
    print()


def show_top_performers(students: list[Student]) -> None:
    """Print a ranked table of students ordered by GPA."""
    heading("TOP PERFORMERS")
    agg = OrderedReportAggregator()
    top = agg.top_performers(students, limit=10)
    student_map = {s.student_id: s for s in students}
    print(f"  {'Rank':<6} {'ID':<8} {'Name':<24} {'Major':<8} {'GPA':<8}")
    sep("-")
    for rank, (sid, gpa) in enumerate(top.items(), 1):
        s = student_map[sid]
        print(f"  {rank:<6} {sid:<8} {s.full_name:<24} {s.major:<8} {gpa:<8.2f}")
    print()


def show_students_by_major(students: list[Student]) -> None:
    """Print students grouped by declared major."""
    heading("STUDENTS BY MAJOR")
    agg = StudentGroupAggregator()
    by_major = agg.group_by_major(students)
    for major in sorted(by_major):
        group = sorted(by_major[major], key=lambda s: s.student_id)
        names = ", ".join(f"{s.full_name} ({s.student_id})" for s in group)
        print(f"  {major:<8} ({len(group):>2})  {names}")
    print()


def show_students_by_year(students: list[Student]) -> None:
    """Print students grouped by academic year."""
    heading("STUDENTS BY YEAR")
    year_labels = {1: "Freshman", 2: "Sophomore", 3: "Junior", 4: "Senior"}
    agg = StudentGroupAggregator()
    by_year = agg.group_by_year(students)
    for year in sorted(by_year):
        group = sorted(by_year[year], key=lambda s: s.student_id)
        label = year_labels.get(year, f"Year {year}")
        names = ", ".join(f"{s.full_name} ({s.student_id})" for s in group)
        print(f"  {label:<12} ({len(group):>2})  {names}")
    print()


def show_statistics(students: list[Student]) -> None:
    """Print mean, median, mode, percentiles, and extremes."""
    heading("STATISTICS")
    stats = GradeStatistics()
    summary = stats.compute_summary(students)
    for key, label in [
        ("mean", "Mean"),
        ("median", "Median"),
        ("mode", "Mode"),
        ("percentile_25", "25th Percentile"),
        ("percentile_75", "75th Percentile"),
        ("highest", "Highest Score"),
        ("lowest", "Lowest Score"),
    ]:
        fmt(label, f"{summary[key]:.2f}")
    print()


def show_rolling_averages(students: list[Student]) -> None:
    """Print per-student rolling averages over semesters."""
    heading("ROLLING AVERAGES (window=3)")
    for student in sorted(students, key=lambda s: s.student_id):
        calc = RollingAverageCalculator(window_size=3)
        ordered = sorted(student.grades, key=lambda g: g.semester)
        avgs = [f"{v:.1f}" for v in calc.extend(g.score for g in ordered)]
        print(f"  {student.student_id:<8} {student.full_name:<24}  {' → '.join(avgs)}")
    print()


def show_per_student(students: list[Student]) -> None:
    """Print a line per student with grades and GPA."""
    heading("PER-STUDENT BREAKDOWN")
    for student in sorted(students, key=lambda s: s.full_name):
        semester_grades = sorted(student.grades, key=lambda g: g.semester)
        grades_str = ", ".join(f"{g.course.code}:{g.score:.0f}" for g in semester_grades)
        print(
            f"  {student.full_name:<24} {student.student_id:<8} "
            f"{student.major:<6} Yr{student.year:<3} "
            f"GPA: {student.gpa:<6.2f}  |  {grades_str}"
        )
    print()


def main() -> int:
    """Parse args, run the pipeline, and display the CLI report."""
    parser = argparse.ArgumentParser(
        prog="run_report",
        description="Run the student analytics pipeline and display a professional CLI report.",
    )
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "data" / "sample_students.csv",
        help="Path to the input CSV file.",
    )
    args = parser.parse_args()

    try:
        reader = CSVStudentReader(path=args.input)
        students = reader.read()
    except AnalyticsError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if not students:
        print("No student records found.", file=sys.stderr)
        return 1

    sep("=")
    print("   STUDENT GRADE ANALYTICS REPORT")
    print(f"   Generated: {__import__('datetime').datetime.now():%Y-%m-%d %H:%M:%S}")
    print(f"   Source:    {args.input.name}")
    sep("=")
    print()

    show_overview(students)
    show_top_performers(students)
    show_grade_distribution(students)
    show_statistics(students)
    show_students_by_major(students)
    show_students_by_year(students)
    show_rolling_averages(students)
    show_per_student(students)

    sep("=")
    print(
        f"   Report complete — {len(students)} students, "
        f"{sum(len(s.grades) for s in students)} grades processed."
    )
    sep("=")
    return 0


if __name__ == "__main__":
    sys.exit(main())
