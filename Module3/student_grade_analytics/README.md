# Student Grade Analytics Tool

A production-grade Python analytics pipeline that ingests student records
from a CSV file, aggregates them with the standard library's advanced
collections (`Counter`, `defaultdict`, `OrderedDict`, `deque`), and emits
a rich JSON report.

The project follows the **SOLID** principles from top to bottom, ships
with a professional logging setup, is fully type-hinted, and is verified
by **`ruff`**, **`black`**, **`mypy --strict`**, and **`pytest`** with
**100% branch coverage**.

---

## Table of Contents

1. [Features](#features)
2. [Project Structure](#project-structure)
3. [SOLID Design](#solid-design)
4. [Installation](#installation)
5. [Usage](#usage)
6. [Sample Input & Output](#sample-input--output)
7. [Collection Performance Notes](#collection-performance-notes)
8. [Development](#development)

---

## Features

- **Advanced collections** — `Counter`, `defaultdict`, `OrderedDict`, and `deque` back distinct, single-responsibility aggregators.
- **Dataclasses & `NamedTuple`** — `Student`, `Grade`, and `Course` model the domain declaratively.
- **`TypedDict`** — the JSON output shape is captured by the `ReportPayload` type.
- **Strict typing** — every public callable is annotated and passes `mypy --strict`.
- **Robust I/O** — CSV read/JSON write goes through context managers with translated exceptions.
- **Rolling averages** — a `deque(maxlen=N)` supplies O(1) windowed means.
- **Professional logging** — a single call to `configure_logging` produces timestamped, level-tagged, source-attributed logs to both stderr and a file in `logs/`.
- **CLI** — `student-analytics --input students.csv --output report.json`.
- **Terminal report** — `python scripts/run_report.py` prints a professional formatted report directly to the console with tables, histograms, and per-student breakdowns, and also writes the same analytics as JSON to `reports/report.json`.
- **100% test coverage** — every branch is exercised by `pytest`.

---

## Project Structure

```
student_grade_analytics/
├── data/
│   └── sample_students.csv           # Example CSV input
├── logs/
│   ├── .gitkeep                      # Ensures logs/ is tracked
│   └── student_analytics.log         # Appended log output (gitignored)
├── reports/
│   └── report.json                   # Generated JSON analytics report
├── scripts/
│   ├── run_demo.py                   # End-to-end demo runner
│   └── run_report.py                 # Professional CLI report display
├── src/
│   └── student_analytics/
│       ├── __init__.py               # Public API exports
│       ├── cli.py                    # argparse-based entry point
│       ├── analytics/                # Business logic layer
│       │   ├── __init__.py
│       │   ├── aggregators.py        # Counter / defaultdict / OrderedDict
│       │   ├── analyzer.py           # Orchestrator (composition root)
│       │   ├── builder.py            # ReportPayloadBuilder (payload assembly)
│       │   ├── metrics.py            # MetricCalculator protocol + metrics
│       │   ├── rolling_average.py    # deque-based rolling mean
│       │   └── statistics.py         # mean / median / mode / percentiles
│       ├── exceptions/               # Exception hierarchy
│       │   ├── __init__.py
│       │   └── exceptions.py
│       ├── io/                       # I/O layer
│       │   ├── __init__.py
│       │   ├── readers.py            # CSVStudentReader
│       │   └── writers.py            # JSONReportWriter
│       ├── logger/                   # Logging configuration
│       │   ├── __init__.py
│       │   └── logger.py
│       └── models/                   # Data models
│           ├── __init__.py
│           ├── models.py             # Dataclasses, NamedTuple, TypedDict, Enum
│           └── protocols.py          # Structural protocols (DIP)
├── tests/
│   ├── conftest.py
│   ├── test_aggregators.py
│   ├── test_analyzer.py
│   ├── test_builder.py
│   ├── test_cli.py
│   ├── test_exceptions.py
│   ├── test_logger.py
│   ├── test_metrics.py
│   ├── test_models.py
│   ├── test_protocols.py
│   ├── test_readers.py
│   ├── test_rolling_average.py
│   ├── test_statistics.py
│   └── test_writers.py
├── pyproject.toml
├── requirements.txt
├── .gitignore
└── README.md
```

---

## SOLID Design

| Principle | Where it lives |
|-----------|----------------|
| **S**ingle Responsibility | Each module does one thing: `readers` reads, `writers` writes, `statistics` computes, `aggregators` aggregates, `metrics.py` computes one metric each, `builder.py` assembles the payload, `analyzer.py` only orchestrates. |
| **O**pen/Closed | New readers or writers implement the protocols in `models/protocols.py`; new report sections are added as extra `MetricCalculator` implementations in `metrics.py` — `analyzer.py` and `builder.py` never have to change. |
| **L**iskov Substitution | `StudentReader`, `ReportWriter`, and `MetricCalculator` protocols guarantee any conforming class is interchangeable. |
| **I**nterface Segregation | Narrow protocols (`StudentReader`, `ReportWriter`, `MetricCalculator`) instead of fat "IOService" or "Analyzer" classes — clients depend only on the methods they actually use. |
| **D**ependency Inversion | `StudentGradeAnalyzer` depends only on the abstractions (`StudentReader`, `ReportWriter`, `MetricCalculator`, `ReportPayloadBuilder`), not on concrete classes; the CLI is the composition root. |

---

## Installation

```bash
# Python 3.11+
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -e ".[dev]"              # installs runtime + dev tools
```

---

## Usage

### Terminal report

Print a formatted analytics report directly to the console. This also runs
the same data through the standard analytics pipeline and writes the JSON
report to `reports/report.json` (unless a different `--output` is given):

```bash
python scripts/run_report.py
```

With a custom input file and/or output path:

```bash
python scripts/run_report.py --input path/to/students.csv --output path/to/report.json
```

### CLI (JSON report only)

Run the pipeline headlessly and write only the JSON report, without the
terminal display:

```bash
student-analytics --input data/sample_students.csv --output reports/report.json
```

### As a library

```python
from pathlib import Path

from student_analytics import (
    CSVStudentReader,
    JSONReportWriter,
    StudentGradeAnalyzer,
)

analyzer = StudentGradeAnalyzer(
    reader=CSVStudentReader(Path("data/sample_students.csv")),
    writer=JSONReportWriter(Path("reports/report.json")),
    top_performer_limit=5,
    rolling_window_size=3,
)
report = analyzer.run()
print(f"Generated report for {report['total_students']} students.")
```

---

## Sample Input & Output

### Input — `data/sample_students.csv`

```csv
student_id,first_name,last_name,major,year,course_code,course_name,credits,semester,score
S003,Alice,Johnson,CS,1,CS101,Intro to CS,3,Fall2023,54.2
S003,Alice,Johnson,CS,1,MA101,Calculus I,4,Fall2023,63.7
S003,Alice,Johnson,CS,1,EN101,English Composition,3,Spring2024,66.2
...
```

### Terminal output — `python scripts/run_report.py`

```
========================================================================
   STUDENT GRADE ANALYTICS REPORT
   Generated: 2026-08-03 12:59:50   Source: sample_students.csv
========================================================================

========================================================================
  WHAT THIS REPORT TELLS YOU
========================================================================
  • 40 students, 120 grades recorded across 3 majors.
  • Performance is strong: 34 of 120 grades (28%) are a B or better.
  • The average student GPA is 71.44; the mean score across all 120 grades is 71.44.
  • Best performer: Jack Taylor (S012, MATH) with a GPA of 94.03.
  • The most common letter grade is C and the most popular major is CS (16 students).

========================================================================
  OVERVIEW
========================================================================
  Total students                         40
  Total grades                          120
  Unique majors                           3
  Year groups                             4
  Average student GPA                 71.44
  Best student GPA                    94.03
  Lowest student GPA                  51.73
  Note: GPA is each student's average course score; the overall mean of all raw grades appears in the Statistics section.

========================================================================
  TOP PERFORMERS
========================================================================
  Rank   ID       Name
------------------------------------------------------------------------
  1      S012     Jack Taylor
  2      S040     Nathan Cox
  3      S026     Xavier Green
  4      S025     Wendy Scott
  5      S032     Daniel Ross
  6      S037     Julia Ward
  7      S028     Zachary Carter
  8      S011     Ivy Chen
  9      S008     Frank Miller
  10     S038     Kyle Hayes
  Note: Top performers across the whole school, ranked by overall GPA.

========================================================================
  TOP PERFORMERS BY YEAR
========================================================================
  Year 1  (5 students)
    Rank  ID     Name                    MA     CS     EN     Avg
------------------------------------------------------------------------
    1     S012   Jack Taylor           85.1   98.5   98.5   94.03
    2     S011   Ivy Chen              83.2   70.6   87.6   80.47
    3     S008   Frank Miller          81.2   72.7   86.6   80.17
    4     S009   Grace Lee             79.5   65.5   89.8   78.27
    5     S014   Leo Garcia            73.7   53.6   66.4   64.57

  Year 2  (5 students)
    Rank  ID     Name                    MA     CS     Avg
------------------------------------------------------------------------
    1     S020   Rachel King           80.6   77.6   79.60
    2     S017   Olivia Clark          74.3   84.1   77.57
    3     S021   Sam Moore             80.7   68.7   76.67
    4     S023   Uma Baker             69.0   89.5   75.80
    5     S005   Carol Brown           70.8   76.2   72.60

  Year 3  (5 students)
    Rank  ID     Name                    MA     CS     Avg
------------------------------------------------------------------------
    1     S026   Xavier Green          87.6   92.4   89.17
    2     S025   Wendy Scott           83.5   87.3   84.77
    3     S028   Zachary Carter        74.8   94.9   81.47
    4     S002   Jane Smith            82.6   72.1   79.10
    5     S027   Yvonne Nelson         78.5   80.2   79.03

  Year 4  (5 students)
    Rank  ID     Name                    CS     PH     Avg
------------------------------------------------------------------------
    1     S040   Nathan Cox            90.8   90.2   90.37
    2     S032   Daniel Ross           81.4   82.8   82.37
    3     S037   Julia Ward            91.0   77.2   81.77
    4     S038   Kyle Hayes            84.3   77.5   79.77
    5     S033   Emily Morgan          60.8   71.0   67.60

  Note: Each subject column is the student's average in that subject; Avg is the student's overall average. Students in the same year study the same courses, so only those subjects are listed.

========================================================================
  GRADE DISTRIBUTION
========================================================================
  Letter   Range    Count           %  Histogram
------------------------------------------------------------------------
  A        90-100   11           9.2%  ██░░░░░░░░░░░░░░░░░░░░░░░░░░░░
  B        80-89    23          19.2%  █████░░░░░░░░░░░░░░░░░░░░░░░░░
  C        70-79    30          25.0%  ███████░░░░░░░░░░░░░░░░░░░░░░░
  D        60-69    30          25.0%  ███████░░░░░░░░░░░░░░░░░░░░░░░
  F        0-59     26          21.7%  ██████░░░░░░░░░░░░░░░░░░░░░░░░
------------------------------------------------------------------------
  TOTAL             120        100.0%

========================================================================
  STATISTICS — ALL 120 GRADES
========================================================================
  Mean score                          71.44
  Median score                        71.45
  Most common score                   72.70
  25th percentile                     61.55
  75th percentile                     81.12
  Highest score                       98.50
  Lowest score                        43.80
  Note: A percentile describes where a grade sits: the 25th percentile of 61.55 means a quarter of all grades are at or below that score.

========================================================================
  STUDENTS BY MAJOR
========================================================================
  Major    Count   Distribution (40 students)
------------------------------------------------------------------------
  CS          16   ████████████░░░░░░░░░░░░░░░░░░
  MATH        14   ██████████░░░░░░░░░░░░░░░░░░░░
  PHYS        10   ███████░░░░░░░░░░░░░░░░░░░░░░░

  Note: Student counts per declared major.

========================================================================
  STUDENTS BY YEAR
========================================================================
  Year     Count   Distribution (40 students)
------------------------------------------------------------------------
  Year 1      10   ███████░░░░░░░░░░░░░░░░░░░░░░░
  Year 2      10   ███████░░░░░░░░░░░░░░░░░░░░░░░
  Year 3      10   ███████░░░░░░░░░░░░░░░░░░░░░░░
  Year 4      10   ███████░░░░░░░░░░░░░░░░░░░░░░░

  Note: Student counts per academic year.

========================================================================
  ROLLING AVERAGES (window=3)
========================================================================
  Year 1
    ID      Name                     CS101   MA101   EN101     Avg
------------------------------------------------------------------------
    S003    Alice Johnson             54.2    63.7    66.2    61.4
    S007    Eve Davis                 64.3    58.9    61.1    61.4
    S008    Frank Miller              72.7    81.2    86.6    80.2
    S009    Grace Lee                 65.5    79.5    89.8    78.3
    S010    Henry Wilson              67.1    55.6    68.4    63.7
    S011    Ivy Chen                  70.6    83.2    87.6    80.5
    S012    Jack Taylor               98.5    85.1    98.5    94.0
    S013    Karen White               62.4    56.9    71.1    63.5
    S014    Leo Garcia                53.6    73.7    66.4    64.6
    S015    Mona Patel                50.7    58.9    53.4    54.3

  Year 2
    ID      Name                     CS201   MA201   MA202     Avg
------------------------------------------------------------------------
    S001    John Doe                  65.0    79.8    69.5    71.4
    S005    Carol Brown               76.2    76.2    65.4    72.6
    S016    Nick Adams                81.1    72.6    59.7    71.1
    S017    Olivia Clark              84.1    73.5    75.1    77.6
    S018    Peter Lewis               68.9    69.0    62.5    66.8
    S019    Quinn Young               47.3    56.8    57.0    53.7
    S020    Rachel King               77.6    92.0    69.2    79.6
    S021    Sam Moore                 68.7    96.4    64.9    76.7
    S022    Tina Hall                 66.4    73.1    72.4    70.6
    S023    Uma Baker                 89.5    59.6    78.3    75.8

  Year 3
    ID      Name                     CS301   MA301   MA302     Avg
------------------------------------------------------------------------
    S002    Jane Smith                72.1    79.9    85.3    79.1
    S006    David Miller              81.5    69.7    81.6    77.6
    S024    Victor Hill               81.1    72.7    66.1    73.3
    S025    Wendy Scott               87.3    90.1    76.9    84.8
    S026    Xavier Green              92.4    82.9    92.2    89.2
    S027    Yvonne Nelson             80.2    84.2    72.7    79.0
    S028    Zachary Carter            94.9    70.0    79.5    81.5
    S029    Aisha Wright              54.4    61.1    71.4    62.3
    S030    Brian Torres              63.0    54.9    61.8    59.9
    S031    Chloe Foster              60.4    43.8    51.0    51.7

  Year 4
    ID      Name                     CS303   PH401   PH402     Avg
------------------------------------------------------------------------
    S004    Bob Williams              64.3    56.8    53.0    58.0
    S032    Daniel Ross               81.4    85.0    80.7    82.4
    S033    Emily Morgan              60.8    74.7    67.3    67.6
    S034    George Price              56.3    74.9    71.5    67.6
    S035    Hannah Reed               50.0    56.6    73.9    60.2
    S036    Ian Bell                  56.0    53.5    46.4    52.0
    S037    Julia Ward                91.0    81.6    72.7    81.8
    S038    Kyle Hayes                84.3    77.1    77.9    79.8
    S039    Laura Bennett             65.4    61.7    59.1    62.1
    S040    Nathan Cox                90.8    94.1    86.2    90.4

  Note: Each course column is the student's actual recorded score; Avg is the rolling mean of the latest 3 grades, recomputed as each new course is completed. Students in the same year study the same courses.

========================================================================
  PER-STUDENT BREAKDOWN
========================================================================
  Year 1  (10 students)
    Rank  ID     Name                    MA     CS     EN     Avg
------------------------------------------------------------------------
    1     S012   Jack Taylor           85.1   98.5   98.5   94.03
    2     S011   Ivy Chen              83.2   70.6   87.6   80.47
    3     S008   Frank Miller          81.2   72.7   86.6   80.17
    4     S009   Grace Lee             79.5   65.5   89.8   78.27
    5     S014   Leo Garcia            73.7   53.6   66.4   64.57
    6     S010   Henry Wilson          55.6   67.1   68.4   63.70
    7     S013   Karen White           56.9   62.4   71.1   63.47
    8     S007   Eve Davis             58.9   64.3   61.1   61.43
    9     S003   Alice Johnson         63.7   54.2   66.2   61.37
    10    S015   Mona Patel            58.9   50.7   53.4   54.33

  Year 2  (10 students)
    Rank  ID     Name                    MA     CS     Avg
------------------------------------------------------------------------
    1     S020   Rachel King           80.6   77.6   79.60
    2     S017   Olivia Clark          74.3   84.1   77.57
    3     S021   Sam Moore             80.7   68.7   76.67
    4     S023   Uma Baker             69.0   89.5   75.80
    5     S005   Carol Brown           70.8   76.2   72.60
    6     S001   John Doe              74.7   65.0   71.43
    7     S016   Nick Adams            66.2   81.1   71.13
    8     S022   Tina Hall             72.8   66.4   70.63
    9     S018   Peter Lewis           65.8   68.9   66.80
    10    S019   Quinn Young           56.9   47.3   53.70

  Year 3  (10 students)
    Rank  ID     Name                    MA     CS     Avg
------------------------------------------------------------------------
    1     S026   Xavier Green          87.6   92.4   89.17
    2     S025   Wendy Scott           83.5   87.3   84.77
    3     S028   Zachary Carter        74.8   94.9   81.47
    4     S002   Jane Smith            82.6   72.1   79.10
    5     S027   Yvonne Nelson         78.5   80.2   79.03
    6     S006   David Miller          75.7   81.5   77.60
    7     S024   Victor Hill           69.4   81.1   73.30
    8     S029   Aisha Wright          66.2   54.4   62.30
    9     S030   Brian Torres          58.3   63.0   59.90
    10    S031   Chloe Foster          47.4   60.4   51.73

  Year 4  (10 students)
    Rank  ID     Name                    CS     PH     Avg
------------------------------------------------------------------------
    1     S040   Nathan Cox            90.8   90.2   90.37
    2     S032   Daniel Ross           81.4   82.8   82.37
    3     S037   Julia Ward            91.0   77.2   81.77
    4     S038   Kyle Hayes            84.3   77.5   79.77
    5     S033   Emily Morgan          60.8   71.0   67.60
    6     S034   George Price          56.3   73.2   67.57
    7     S039   Laura Bennett         65.4   60.4   62.07
    8     S035   Hannah Reed           50.0   65.2   60.17
    9     S004   Bob Williams          64.3   54.9   58.03
    10    S036   Ian Bell              56.0   50.0   51.97

  Note: Subject columns are each student's average in that subject; Avg is their overall average. Students in the same year study the same courses.

========================================================================
   Report complete — 40 students, 120 grades processed.
   JSON report written to: reports/report.json
========================================================================
```

### Output — `reports/report.json`

Written by both `student-analytics` and `python scripts/run_report.py` for
the full `data/sample_students.csv` (40 students, 120 grades). Lists are
truncated below with `...` for brevity — the real file enumerates every
student:

```json
{
  "generated_at": "2026-08-03T10:54:26.400130+00:00",
  "total_students": 40,
  "grade_distribution": {"A": 11, "B": 23, "C": 30, "D": 30, "F": 26},
  "students_by_major": {
    "CS": ["S001", "S003", "S006", "..."],
    "MATH": ["S002", "S005", "S009", "..."],
    "PHYS": ["S004", "S007", "S010", "..."]
  },
  "students_by_year": {
    "1": ["S003", "S007", "S008", "..."],
    "2": ["S001", "S005", "S016", "..."],
    "3": ["S002", "S006", "S024", "..."],
    "4": ["S004", "S032", "S033", "..."]
  },
  "top_performers": [
    {"student_id": "S012", "gpa": 94.03},
    {"student_id": "S040", "gpa": 90.37},
    {"student_id": "S026", "gpa": 89.17},
    {"student_id": "S025", "gpa": 84.77},
    {"student_id": "S032", "gpa": 82.37}
  ],
  "statistics": {
    "mean": 71.44,
    "median": 71.45,
    "mode": 72.7,
    "percentile_25": 61.55,
    "percentile_75": 81.12,
    "highest": 98.5,
    "lowest": 43.8
  },
  "rolling_averages": {
    "S003": [54.2, 58.95, 61.37],
    "S007": [64.3, 61.6, 61.43],
    "...": ["..."]
  }
}
```

---

## Collection Performance Notes

| Collection | Use case in this project | Complexity | Memory footprint |
|-----------|--------------------------|------------|------------------|
| `Counter` | Grade-letter distribution | `O(N)` build, `O(1)` lookups | ~ `O(K)` where K = distinct keys |
| `defaultdict(list)` | Group students by major/year | `O(N)` build, `O(1)` insert | ~ `O(N)` |
| `OrderedDict` | Top performers ranking | Preserves insertion order | Same as `dict` in CPython 3.7+, but explicit intent |
| `deque(maxlen=N)` | Rolling averages | O(1) append + auto-evict | Fixed `O(N)` |

**Why `deque` for rolling averages?** A list-based window would either
require an `O(N)` slice on each update (to drop the oldest sample) or a
manual index that leaks state; `deque(maxlen=N)` gives us both amortised
`O(1)` append and automatic eviction with zero bookkeeping.

**Why `OrderedDict` for `top_performers` even in modern Python?**
Dictionaries preserve insertion order since 3.7, but using `OrderedDict`
makes the intent explicit and communicates to readers that the ordering
matters for the payload — an example of choosing the collection that
best expresses the domain.

---

## Development

### Run every quality gate

```bash
ruff check src tests            # linting + import sorting + docstyle
black --check src tests         # formatting
mypy src                        # strict static typing
pytest                          # tests + 100% branch coverage
```
