#!/usr/bin/env python3
"""Professional CLI report for the Student Grade Analytics Tool.

Usage:
    python scripts/run_report.py --input data/sample_students.csv

Displays a formatted analytics report directly in the terminal using
the existing analysis pipeline. The report prioritises clarity: labels
are unambiguous (per-student GPA vs. raw grade scores), every table is
consistently aligned, and each section ends with a plain-language note
that explains how to read the numbers.
"""

import argparse
import sys
from collections import Counter, defaultdict
from datetime import datetime
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
ROLLING_WINDOW_SIZE = 3

LETTER_RANGES: dict[GradeLetter, str] = {
    GradeLetter.A: "90-100",
    GradeLetter.B: "80-89",
    GradeLetter.C: "70-79",
    GradeLetter.D: "60-69",
    GradeLetter.F: "0-59",
}


def print_separator_line(character: str = "=") -> None:
    """Print a horizontal separator line across the terminal width."""
    print(character * TERMINAL_LINE_WIDTH)


def print_section_heading(title: str) -> None:
    """Print a section heading framed by horizontal separators."""
    print_separator_line()
    print(f"  {title}")
    print_separator_line()


def print_note(note: str) -> None:
    """Print an indented plain-language note explaining a section."""
    print(f"  Note: {note}")
    print()


def build_progress_bar(value: int, total: int, width: int = 30) -> str:
    """Return an ASCII bar representing ``value/total``."""
    filled = int(width * value / total) if total else 0
    return "█" * filled + "░" * (width - filled)


def print_formatted_field(name: str, value: object) -> None:
    """Print a left-aligned label followed by a right-aligned value."""
    print(f"  {name:<30} {value!s:>10}")


def display_executive_summary_section(all_students: list[Student]) -> None:
    """Print the key takeaways of the dataset in plain language."""
    print_section_heading("WHAT THIS REPORT TELLS YOU")
    total_grades = sum(len(student.grades) for student in all_students)
    average_gpa = sum(student.gpa for student in all_students) / len(all_students)
    mean_score = GradeStatistics().compute_summary(all_students)["mean"]
    top_student = max(all_students, key=lambda student: student.gpa)
    grade_distribution = GradeDistributionAggregator().aggregate(all_students)
    most_common_letter = max(grade_distribution, key=grade_distribution.__getitem__)
    grades_at_or_above_b = grade_distribution[GradeLetter.A] + grade_distribution[GradeLetter.B]
    major_counts = Counter(student.major for student in all_students)
    most_common_major, most_common_major_count = major_counts.most_common(1)[0]
    bullets = [
        f"{len(all_students)} students, {total_grades} grades recorded across "
        f"{len(major_counts)} majors.",
        f"Performance is strong: {grades_at_or_above_b} of {total_grades} grades "
        f"({100.0 * grades_at_or_above_b / total_grades:.0f}%) are a B or better.",
        f"The average student GPA is {average_gpa:.2f}; the mean score across all "
        f"{total_grades} grades is {mean_score:.2f}.",
        f"Best performer: {top_student.full_name} ({top_student.student_id}, "
        f"{top_student.major}) with a GPA of {top_student.gpa:.2f}.",
        f"The most common letter grade is {most_common_letter.value} and the most "
        f"popular major is {most_common_major} ({most_common_major_count} students).",
    ]
    for bullet in bullets:
        print(f"  • {bullet}")
    print()


def display_overview_section(all_students: list[Student]) -> None:
    """Print student/grade counts and the extremes of per-student GPA."""
    print_section_heading("OVERVIEW")
    total_grades = sum(len(student.grades) for student in all_students)
    print_formatted_field("Total students", len(all_students))
    print_formatted_field("Total grades", total_grades)
    print_formatted_field("Unique majors", len({student.major for student in all_students}))
    print_formatted_field("Year groups", len({student.year for student in all_students}))
    average_gpa = sum(student.gpa for student in all_students) / len(all_students)
    highest_gpa = max(student.gpa for student in all_students)
    lowest_gpa = min(student.gpa for student in all_students)
    print_formatted_field("Average student GPA", f"{average_gpa:.2f}")
    print_formatted_field("Best student GPA", f"{highest_gpa:.2f}")
    print_formatted_field("Lowest student GPA", f"{lowest_gpa:.2f}")
    print_note(
        "GPA is each student's average course score; the overall mean of "
        "all raw grades appears in the Statistics section."
    )


def display_top_performers_section(all_students: list[Student]) -> None:
    """Print the top performers ranked across the whole school by GPA."""
    print_section_heading("TOP PERFORMERS")
    ranking_aggregator = OrderedReportAggregator()
    top_performers = ranking_aggregator.top_performers(all_students, limit=10)
    student_lookup_map = {student.student_id: student for student in all_students}
    print(f"  {'Rank':<6} {'ID':<8} {'Name':<24}")
    print_separator_line("-")
    for rank, (student_id, _gpa_score) in enumerate(top_performers.items(), 1):
        current_student = student_lookup_map[student_id]
        print(f"  {rank:<6} {student_id:<8} {current_student.full_name:<24}")
    print_note("Top performers across the whole school, ranked by overall GPA.")


SUBJECT_COLUMNS = ["MA", "CS", "PH", "EN"]


def course_subject(course_code: str) -> str:
    """Return the subject-family prefix of a course code.

    E.g. ``"CS101"``, ``"CS201"`` and ``"CS303"`` all map to ``"CS"``.
    """
    return course_code.rstrip("0123456789")


def display_top_performers_by_year_section(all_students: list[Student]) -> None:
    """Print a per-year table with subject averages and an overall average.

    Students in the same year study the same courses, so each row shows a
    student's average in each subject followed by their overall average.
    Only the subjects that year actually studies are shown as columns, and
    rows are ranked by overall average within the year.
    """
    print_section_heading("TOP PERFORMERS BY YEAR")
    students_by_year = StudentGroupAggregator().group_by_year(all_students)
    for year in sorted(students_by_year):
        year_students = students_by_year[year]
        ranked = sorted(year_students, key=lambda student: (-student.gpa, student.student_id))[:5]
        student_label = "student" if len(ranked) == 1 else "students"
        subjects_studied: set[str] = set()
        for student in year_students:
            for grade in student.grades:
                subjects_studied.add(course_subject(grade.course.code))
        subject_columns = [s for s in SUBJECT_COLUMNS if s in subjects_studied]

        print(f"  Year {year}  ({len(ranked)} {student_label})")
        header = f"    {'Rank':<6}{'ID':<7}{'Name':<19}"
        for subject in subject_columns:
            header += f"{subject:>7}"
        header += f"{'Avg':>8}"
        print(header)
        print_separator_line("-")
        for rank, student in enumerate(ranked, 1):
            subject_scores: dict[str, list[float]] = defaultdict(list)
            for grade in student.grades:
                subject_scores[course_subject(grade.course.code)].append(grade.score)
            row = f"    {rank:<6}{student.student_id:<7}{student.full_name:<19}"
            for subject in subject_columns:
                scores = subject_scores.get(subject, [])
                value = f"{sum(scores) / len(scores):.1f}" if scores else "-"
                row += f"{value:>7}"
            row += f"{student.gpa:>8.2f}"
            print(row)
        print()
    print_note(
        "Each subject column is the student's average in that subject; Avg "
        "is the student's overall average. Students in the same year study "
        "the same courses, so only those subjects are listed."
    )


def display_grade_distribution_section(all_students: list[Student]) -> None:
    """Print a letter-grade histogram with counts, percentages, and ranges."""
    print_section_heading("GRADE DISTRIBUTION")
    grade_distribution = GradeDistributionAggregator().aggregate(all_students)
    total_grades = sum(grade_distribution.values())
    print(f"  {'Letter':<8} {'Range':<8} {'Count':<8} {'%':>8}  Histogram")
    print_separator_line("-")
    for grade_letter in GradeLetter:
        letter_count = grade_distribution[grade_letter]
        letter_percentage = 100.0 * letter_count / total_grades if total_grades else 0.0
        histogram_bar = build_progress_bar(letter_count, total_grades)
        print(
            f"  {grade_letter.value:<8} {LETTER_RANGES[grade_letter]:<8} "
            f"{letter_count:<8} {letter_percentage:>7.1f}%  {histogram_bar}"
        )
    print_separator_line("-")
    print(f"  {'TOTAL':<8} {'':<8} {total_grades:<8} {'100.0%':>8}")
    print()


def display_statistics_section(all_students: list[Student]) -> None:
    """Print mean, median, mode, percentiles, and extremes of raw scores."""
    total_grades = sum(len(student.grades) for student in all_students)
    print_section_heading(f"STATISTICS — ALL {total_grades} GRADES")
    statistics_summary = GradeStatistics().compute_summary(all_students)
    for key, label in [
        ("mean", "Mean score"),
        ("median", "Median score"),
        ("mode", "Most common score"),
        ("percentile_25", "25th percentile"),
        ("percentile_75", "75th percentile"),
        ("highest", "Highest score"),
        ("lowest", "Lowest score"),
    ]:
        print_formatted_field(label, f"{statistics_summary[key]:.2f}")
    print_note(
        "A percentile describes where a grade sits: the 25th percentile of "
        f"{statistics_summary['percentile_25']:.2f} means a quarter of all grades "
        "are at or below that score."
    )


def _print_count_table(group_header: str, counts: list[tuple[str, int]]) -> None:
    """Print a compact summary table of group labels and student counts."""
    total = sum(count for _, count in counts)
    label = "students" if total != 1 else "student"
    print(f"  {group_header:<8} {'Count':>5}   Distribution ({total} {label})")
    print_separator_line("-")
    for group_name, count in counts:
        bar = build_progress_bar(count, total, width=30)
        print(f"  {group_name:<8} {count:>5}   {bar}")
    print()


def display_students_by_major_section(all_students: list[Student]) -> None:
    """Print student counts grouped by their declared major."""
    print_section_heading("STUDENTS BY MAJOR")
    students_by_major = StudentGroupAggregator().group_by_major(all_students)
    counts = sorted(
        ((major, len(students)) for major, students in students_by_major.items()),
        key=lambda item: item[1],
        reverse=True,
    )
    _print_count_table("Major", counts)
    print_note("Student counts per declared major.")


def display_students_by_year_section(all_students: list[Student]) -> None:
    """Print student counts grouped by their academic year."""
    print_section_heading("STUDENTS BY YEAR")
    students_by_year = StudentGroupAggregator().group_by_year(all_students)
    counts = sorted(
        ((f"Year {year}", len(students)) for year, students in students_by_year.items()),
        key=lambda item: item[0],
    )
    _print_count_table("Year", counts)
    print_note("Student counts per academic year.")


def display_rolling_averages_section(all_students: list[Student]) -> None:
    """Print per-student course scores with the rolling average.

    Each course column shows the student's actual recorded score (matching
    the source CSV); the final Avg column is the rolling average of the
    latest ``window`` grades, recomputed after each course is completed.
    """
    print_section_heading(f"ROLLING AVERAGES (window={ROLLING_WINDOW_SIZE})")
    students_by_year = StudentGroupAggregator().group_by_year(all_students)
    for year in sorted(students_by_year):
        year_students = sorted(students_by_year[year], key=lambda student: student.student_id)
        course_columns: list[str] = []
        for student in year_students:
            ordered_grades = sorted(student.grades, key=lambda grade: grade.semester)
            for grade in ordered_grades:
                if grade.course.code not in course_columns:
                    course_columns.append(grade.course.code)
        column_headers = "".join(f"{code:>8}" for code in course_columns)
        print(f"  Year {year}")
        print(f"    {'ID':<8}{'Name':<22}{column_headers}{'Avg':>8}")
        print_separator_line("-")
        for student in year_students:
            ordered_grades = sorted(student.grades, key=lambda grade: grade.semester)
            scores_by_code = {grade.course.code: grade.score for grade in ordered_grades}
            rolling_calculator = RollingAverageCalculator(window_size=ROLLING_WINDOW_SIZE)
            final_average = rolling_calculator.extend(grade.score for grade in ordered_grades)[-1]
            row = f"    {student.student_id:<8}{student.full_name:<22}"
            row += "".join(f"{scores_by_code[code]:>8.1f}" for code in course_columns)
            row += f"{final_average:>8.1f}"
            print(row)
        print()
    print_note(
        f"Each course column is the student's actual recorded score; Avg is "
        f"the rolling mean of the latest {ROLLING_WINDOW_SIZE} grades, "
        "recomputed as each new course is completed. Students in the same "
        "year study the same courses."
    )


def display_per_student_breakdown_section(all_students: list[Student]) -> None:
    """Print a per-student table of subject averages grouped by year.

    Students in the same year study the same courses, so each year's table
    shows Rank, ID, Name, the subject averages that year actually studies,
    and the overall average (Avg).
    """
    print_section_heading("PER-STUDENT BREAKDOWN")
    students_by_year = StudentGroupAggregator().group_by_year(all_students)
    for year in sorted(students_by_year):
        year_students = students_by_year[year]
        ranked = sorted(year_students, key=lambda student: (-student.gpa, student.student_id))
        subjects_studied: set[str] = set()
        for student in year_students:
            for grade in student.grades:
                subjects_studied.add(course_subject(grade.course.code))
        subject_columns = [s for s in SUBJECT_COLUMNS if s in subjects_studied]
        student_label = "student" if len(ranked) == 1 else "students"
        print(f"  Year {year}  ({len(ranked)} {student_label})")
        header = f"    {'Rank':<6}{'ID':<7}{'Name':<19}"
        for subject in subject_columns:
            header += f"{subject:>7}"
        header += f"{'Avg':>8}"
        print(header)
        print_separator_line("-")
        for rank, student in enumerate(ranked, 1):
            subject_scores: dict[str, list[float]] = defaultdict(list)
            for grade in student.grades:
                subject_scores[course_subject(grade.course.code)].append(grade.score)
            row = f"    {rank:<6}{student.student_id:<7}{student.full_name:<19}"
            for subject in subject_columns:
                scores = subject_scores.get(subject, [])
                value = f"{sum(scores) / len(scores):.1f}" if scores else "-"
                row += f"{value:>7}"
            row += f"{student.gpa:>8.2f}"
            print(row)
        print()
    print_note(
        "Subject columns are each student's average in that subject; Avg is "
        "their overall average. Students in the same year study the same courses."
    )


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
    print(
        f"   Generated: {datetime.now():%Y-%m-%d %H:%M:%S}   Source: {parsed_arguments.input.name}"
    )
    print_separator_line("=")
    print()

    display_executive_summary_section(all_students)
    display_overview_section(all_students)
    display_top_performers_section(all_students)
    display_top_performers_by_year_section(all_students)
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
