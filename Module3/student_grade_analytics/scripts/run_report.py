#!/usr/bin/env python3
"""Professional CLI report for the Student Grade Analytics Tool.

Usage:
    python scripts/run_report.py --input data/sample_students.csv

Displays a formatted analytics report directly in the terminal using
the existing analysis pipeline.
"""


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

TERMINAL_LINE_WIDTH = 72


def print_separator_line(character: str = "=") -> None:
    """Print a horizontal separator line."""
    print(character * TERMINAL_LINE_WIDTH)


def print_section_heading(title: str) -> None:
    """Print a section heading with separators."""
    print_separator_line()
    print(f"  {title}")
    print_separator_line()


def build_progress_bar(value: int, total: int, width: int = 30) -> str:
    """Return an ASCII bar representing ``value/total``."""
    filled = int(width * value / total) if total else 0
    return "█" * filled + "░" * (width - filled)


def print_formatted_field(name: str, value: object, suffix: str = "") -> None:
    """Print a formatted key-value pair."""
    print(f"  {name:<30} {value!s:>10}{suffix}")


def display_overview_section(all_students: list[Student]) -> None:
    """Print total student / grade counts and GPA extremes."""
    print_section_heading("OVERVIEW")
    total_grades = sum(len(student.grades) for student in all_students)
    print_formatted_field("Total students", len(all_students))
    print_formatted_field("Total grades", total_grades)
    major_counts = Counter(student.major for student in all_students)
    print_formatted_field("Unique majors", len(major_counts))
    year_counts = Counter(student.year for student in all_students)
    print_formatted_field("Year groups", len(year_counts))
    average_gpa = (
        sum(student.gpa for student in all_students) / len(all_students)
        if all_students
        else 0.0
    )
    print_formatted_field("Average GPA (all)", f"{average_gpa:.2f}")
    highest_gpa = max(student.gpa for student in all_students) if all_students else 0.0
    lowest_gpa = min(student.gpa for student in all_students) if all_students else 0.0
    print_formatted_field("Highest GPA", f"{highest_gpa:.2f}")
    print_formatted_field("Lowest GPA", f"{lowest_gpa:.2f}")
    print()


def display_grade_distribution_section(all_students: list[Student]) -> None:
    """Print a letter-grade histogram with counts and percentages."""
    print_section_heading("GRADE DISTRIBUTION")
    distribution_aggregator = GradeDistributionAggregator()
    grade_distribution = distribution_aggregator.aggregate(all_students)
    total_grades = sum(grade_distribution.values())
    print(f"  {'Letter':<8} {'Count':<8} {'%':<8}  Distribution")
    print_separator_line("-")
    for grade_letter in GradeLetter:
        letter_count = grade_distribution[grade_letter]
        letter_percentage = 100.0 * letter_count / total_grades if total_grades else 0.0
        histogram_bar = build_progress_bar(letter_count, total_grades)
        print(
            f"  {grade_letter.value:<8} {letter_count:<8} "
            f"{letter_percentage:>6.1f}%  {histogram_bar}"
        )
    print_separator_line("-")
    print(f"  {'TOTAL':<8} {total_grades:<8} {'100.0%':<8}")
    print()


def display_top_performers_section(all_students: list[Student]) -> None:
    """Print a ranked table of students ordered by GPA."""
    print_section_heading("TOP PERFORMERS")
    ranking_aggregator = OrderedReportAggregator()
    top_performers = ranking_aggregator.top_performers(all_students, limit=10)
    student_lookup_map = {student.student_id: student for student in all_students}
    print(f"  {'Rank':<6} {'ID':<8} {'Name':<24} {'Major':<8} {'GPA':<8}")
    print_separator_line("-")
    for rank, (student_id, gpa_score) in enumerate(top_performers.items(), 1):
        current_student = student_lookup_map[student_id]
        print(
            f"  {rank:<6} {student_id:<8} {current_student.full_name:<24} "
            f"{current_student.major:<8} {gpa_score:<8.2f}"
        )
    print()


def display_students_by_major_section(all_students: list[Student]) -> None:
    """Print students grouped by declared major."""
    print_section_heading("STUDENTS BY MAJOR")
    grouping_aggregator = StudentGroupAggregator()
    students_by_major = grouping_aggregator.group_by_major(all_students)
    for major in sorted(students_by_major):
        major_students = sorted(
            students_by_major[major], key=lambda student: student.student_id
        )
        student_list = ", ".join(
            f"{student.full_name} ({student.student_id})" for student in major_students
        )
        print(f"  {major:<8} ({len(major_students):>2})  {student_list}")
    print()


def display_students_by_year_section(all_students: list[Student]) -> None:
    """Print students grouped by academic year."""
    print_section_heading("STUDENTS BY YEAR")
    year_labels = {1: "Freshman", 2: "Sophomore", 3: "Junior", 4: "Senior"}
    grouping_aggregator = StudentGroupAggregator()
    students_by_year = grouping_aggregator.group_by_year(all_students)
    for year in sorted(students_by_year):
        year_students = sorted(
            students_by_year[year], key=lambda student: student.student_id
        )
        year_label = year_labels.get(year, f"Year {year}")
        student_list = ", ".join(
            f"{student.full_name} ({student.student_id})" for student in year_students
        )
        print(f"  {year_label:<12} ({len(year_students):>2})  {student_list}")
    print()


def display_statistics_section(all_students: list[Student]) -> None:
    """Print mean, median, mode, percentiles, and extremes."""
    print_section_heading("STATISTICS")
    grade_statistics = GradeStatistics()
    statistics_summary = grade_statistics.compute_summary(all_students)
    for key, label in [
        ("mean", "Mean"),
        ("median", "Median"),
        ("mode", "Mode"),
        ("percentile_25", "25th Percentile"),
        ("percentile_75", "75th Percentile"),
        ("highest", "Highest Score"),
        ("lowest", "Lowest Score"),
    ]:
        print_formatted_field(label, f"{statistics_summary[key]:.2f}")
    print()


def display_rolling_averages_section(all_students: list[Student]) -> None:
    """Print per-student rolling averages over semesters."""
    print_section_heading("ROLLING AVERAGES (window=3)")
    for student in sorted(all_students, key=lambda student: student.student_id):
        rolling_calculator = RollingAverageCalculator(window_size=3)
        ordered_grades = sorted(student.grades, key=lambda grade: grade.semester)
        semester_averages = [
            f"{average:.1f}"
            for average in rolling_calculator.extend(
                grade.score for grade in ordered_grades
            )
        ]
        print(
            f"  {student.student_id:<8} {student.full_name:<24}  {' → '.join(semester_averages)}"
        )
    print()


def display_per_student_breakdown_section(all_students: list[Student]) -> None:
    """Print a line per student with grades and GPA."""
    print_section_heading("PER-STUDENT BREAKDOWN")
    for student in sorted(all_students, key=lambda student: student.full_name):
        grades_by_semester = sorted(student.grades, key=lambda grade: grade.semester)
        grade_details = ", ".join(
            f"{grade.course.code}:{grade.score:.0f}" for grade in grades_by_semester
        )
        print(
            f"  {student.full_name:<24} {student.student_id:<8} "
            f"{student.major:<6} Yr{student.year:<3} "
            f"GPA: {student.gpa:<6.2f}  |  {grade_details}"
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
    parsed_arguments = parser.parse_args()

    try:
        csv_reader = CSVStudentReader(path=parsed_arguments.input)
        all_students = csv_reader.read()
    except AnalyticsError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    if not all_students:
        print("No student records found.", file=sys.stderr)
        return 1

    print_separator_line("=")
    print("   STUDENT GRADE ANALYTICS REPORT")
    print(f"   Generated: {__import__('datetime').datetime.now():%Y-%m-%d %H:%M:%S}")
    print(f"   Source:    {parsed_arguments.input.name}")
    print_separator_line("=")
    print()

    display_overview_section(all_students)
    display_top_performers_section(all_students)
    display_grade_distribution_section(all_students)
    display_statistics_section(all_students)
    display_students_by_major_section(all_students)
    display_students_by_year_section(all_students)
    display_rolling_averages_section(all_students)
    display_per_student_breakdown_section(all_students)

    print_separator_line("=")
    print(
        f"   Report complete — {len(all_students)} students, "
        f"{sum(len(student.grades) for student in all_students)} grades processed."
    )
    print_separator_line("=")
    return 0


if __name__ == "__main__":
    sys.exit(main())
