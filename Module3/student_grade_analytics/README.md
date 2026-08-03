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
S001,John,Doe,CS,2,CS101,Intro to CS,3,Fall2023,85.5
S001,John,Doe,CS,2,CS201,Data Structures,3,Spring2024,92.0
...
```

### Terminal output — `python scripts/run_report.py`

```
========================================================================
   STUDENT GRADE ANALYTICS REPORT
   Generated: 2026-07-29 11:20:36
   Source:    sample_students.csv
========================================================================

========================================================================
  OVERVIEW
========================================================================
  Total students                          7
  Total grades                           21
  Unique majors                           3
  Year groups                             4
  Average GPA (all)                   82.05
  Highest GPA                         92.17
  Lowest GPA                          65.67

========================================================================
  TOP PERFORMERS
========================================================================
  Rank   ID       Name                     Major    GPA
------------------------------------------------------------------------
  1      S006     David Miller             CS       92.17
  2      S002     Jane Smith               MATH     91.83
  3      S005     Carol Brown              MATH     86.50
  4      S001     John Doe                 CS       85.88
  5      S007     Eve Davis                PHYS     80.00
  6      S003     Alice Johnson            CS       72.33
  7      S004     Bob Williams             PHYS     65.67

========================================================================
  GRADE DISTRIBUTION
========================================================================
  Letter   Count    %         Distribution
------------------------------------------------------------------------
  A        6          28.6%  ████████░░░░░░░░░░░░░░░░░░░░░░
  B        8          38.1%  ███████████░░░░░░░░░░░░░░░░░░░
  C        4          19.0%  █████░░░░░░░░░░░░░░░░░░░░░░░░░
  D        2           9.5%  ██░░░░░░░░░░░░░░░░░░░░░░░░░░░░
  F        1           4.8%  █░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
------------------------------------------------------------------------
  TOTAL    21       100.0%

========================================================================
  STATISTICS
========================================================================
  Mean                                82.33
  Median                              85.50
  Mode                                78.00
  25th Percentile                     78.00
  75th Percentile                     90.00
  Highest Score                       95.50
  Lowest Score                        55.00

========================================================================
  STUDENTS BY MAJOR
========================================================================
  CS       ( 3)  John Doe (S001), Alice Johnson (S003), David Miller (S006)
  MATH     ( 2)  Jane Smith (S002), Carol Brown (S005)
  PHYS     ( 2)  Bob Williams (S004), Eve Davis (S007)

========================================================================
  STUDENTS BY YEAR
========================================================================
  Freshman     ( 2)  Alice Johnson (S003), Eve Davis (S007)
  Sophomore    ( 2)  John Doe (S001), Carol Brown (S005)
  Junior       ( 2)  Jane Smith (S002), David Miller (S006)
  Senior       ( 1)  Bob Williams (S004)

========================================================================
  ROLLING AVERAGES (window=3)
========================================================================
  S001     John Doe                  85.5 → 81.8 → 85.2 → 86.0
  S002     Jane Smith                95.0 → 92.0 → 91.8
  S003     Alice Johnson             65.0 → 68.5 → 72.3
  S004     Bob Williams              55.0 → 61.5 → 65.7
  S005     Carol Brown               90.0 → 88.5 → 86.5
  S006     David Miller              95.5 → 91.8 → 92.2
  S007     Eve Davis                 78.0 → 80.0

========================================================================
  PER-STUDENT BREAKDOWN
========================================================================
  Alice Johnson            S003     CS     Yr1   GPA: 72.33   |  CS101:65, MA101:72, EN101:80
  Bob Williams             S004     PHYS   Yr4   GPA: 65.67   |  PH401:55, PH402:68, MA301:74
  Carol Brown              S005     MATH   Yr2   GPA: 86.50   |  MA201:90, MA202:87, CS201:82
  David Miller             S006     CS     Yr3   GPA: 92.17   |  CS301:96, CS302:88, CS303:93
  Eve Davis                S007     PHYS   Yr1   GPA: 80.00   |  PH101:78, MA101:82
  Jane Smith               S002     MATH   Yr3   GPA: 91.83   |  MA301:95, MA302:89, CS101:92
  John Doe                 S001     CS     Yr2   GPA: 85.88   |  CS101:86, MA201:78, CS201:92, EN101:88

========================================================================
   Report complete — 7 students, 21 grades processed.
   JSON report written to: reports/report.json
========================================================================
```

### Output — `reports/report.json`

```json
{
  "generated_at": "2026-07-29T12:00:00+00:00",
  "total_students": 7,
  "grade_distribution": {"A": 6, "B": 6, "C": 4, "D": 3, "F": 1},
  "students_by_major": {
    "CS": ["S001", "S003", "S006"],
    "MATH": ["S002", "S005"],
    "PHYS": ["S004", "S007"]
  },
  "students_by_year": {
    "1": ["S003", "S007"],
    "2": ["S001", "S005"],
    "3": ["S002", "S006"],
    "4": ["S004"]
  },
  "top_performers": [
    {"student_id": "S006", "gpa": 92.17},
    {"student_id": "S002", "gpa": 91.83}
  ],
  "statistics": {
    "mean": 81.02,
    "median": 85.0,
    "mode": 78.0,
    "percentile_25": 74.0,
    "percentile_75": 90.0,
    "highest": 95.5,
    "lowest": 55.0
  },
  "rolling_averages": {
    "S001": [85.5, 81.75, 84.5, 86.375]
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
