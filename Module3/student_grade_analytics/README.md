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
│   └── run_demo.py                   # End-to-end demo runner
├── src/
│   └── student_analytics/
│       ├── __init__.py               # Public API exports
│       ├── cli.py                    # argparse-based entry point
│       ├── analytics/                # Business logic layer
│       │   ├── __init__.py
│       │   ├── aggregators.py        # Counter / defaultdict / OrderedDict
│       │   ├── analyzer.py           # Orchestrator (composition root)
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
│   ├── test_cli.py
│   ├── test_exceptions.py
│   ├── test_logger.py
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
| **S**ingle Responsibility | Each module does one thing: `readers` reads, `writers` writes, `statistics` computes, `aggregators` aggregates, `analyzer` orchestrates. |
| **O**pen/Closed | New readers or writers just implement the protocols in `models/protocols.py`; `analytics/analyzer.py` never has to change. |
| **L**iskov Substitution | `StudentReader` and `ReportWriter` protocols guarantee any conforming class is interchangeable. |
| **I**nterface Segregation | Two narrow protocols instead of a fat "IOService" — readers know nothing about writing and vice versa. |
| **D**ependency Inversion | `StudentGradeAnalyzer` depends only on the protocols, not on concrete classes; the CLI is the composition root. |

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

### As a CLI

```bash
student-analytics \
    --input data/sample_students.csv \
    --output reports/report.json \
    --top 5 \
    --window 3 \
    --verbose
```

Or run the demo script:

```bash
python scripts/run_demo.py
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

### Run everything through the demo script

```bash
python scripts/run_demo.py
```
