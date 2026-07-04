# Employee Payroll Tracker

A Python-based CLI application for calculating employee salaries, applying tax deductions, and generating formatted payslips. Supports three employee types: **Full-Time**, **Contract**, and **Intern**.

## Features

- **Employee hierarchy** — Abstract base `Employee` class with role-specific subclasses
- **Salary calculation** — Type-specific logic (salary + bonus, hourly × hours, fixed stipend)
- **Tax deduction** — Flat 20% tax rate applied to gross pay
- **Payslip generation** — Formatted output with gross, tax, and net pay
- **Structured logging** — Console (INFO+) and rotating file (DEBUG+) handlers
- **Input validation** — Positive/non-negative checks on salary, bonus, hours, etc.

## Project structure

```
src/
  employee_payroll_tracker/
    __init__.py        Package initializer and re-exports
    employe.py         Employee ABC and subclass definitions
    logger.py          Centralised logging configuration
    main.py            CLI entry point
    payroll.py         Payroll processing logic
    util.py            Validation and formatting utilities
logs/
    app.log            Rotating log file (DEBUG+)
docs/
    sprint-0.md
    sprint-1.md
    sprint-2.md
pyproject.toml
pyrightconfig.json
README.md
```

## Requirements

- **Python** >= 3.12
- **Poetry** >= 2.0 (dependency manager)

## Setup

### 1. Clone the repository

```bash
git clone <repo-url>
cd <repo-directory>
```

### 2. Navigate to the project directory

```bash
cd Module1/LAB1/Employee-Payroll-Tracker
```

### 3. Install dependencies

```bash
poetry install
```

This creates a virtual environment and installs all required packages.

## Usage

### Run the payroll demonstration

The application ships with sample employees covering all three types:

```bash
poetry run python -m src.employee_payroll_tracker.main
```

### Activate the virtual environment (alternative)

```bash
poetry shell
python -m src.employee_payroll_tracker.main
```

### View logs

Logs are written to `logs/app.log` with rotating file handlers (max 5 MB, 3 backups):

```bash
tail -f logs/app.log
```

## Example output

### Console payslips

```
Employee ID: 101 — Alice Johnson
======================================================
         PAYSLIP — FULL-TIME
======================================================
  Employee  :  Alice Johnson
  ID        :  101
  Type      :  Full-Time
------------------------------------------------------
  Gross Pay :  $  5500.00
  Tax (20%) :  $  1100.00
------------------------------------------------------
  Net Pay   :  $  4400.00
======================================================

Employee ID: 102 — Bob Smith
======================================================
         PAYSLIP — FULL-TIME
======================================================
  Employee  :  Bob Smith
  ID        :  102
  Type      :  Full-Time
------------------------------------------------------
  Gross Pay :  $  4500.00
  Tax (20%) :  $   900.00
------------------------------------------------------
  Net Pay   :  $  3600.00
======================================================

Employee ID: 201 — Carol Davis
======================================================
         PAYSLIP — CONTRACT
======================================================
  Employee  :  Carol Davis
  ID        :  201
  Type      :  Contract
------------------------------------------------------
  Gross Pay :  $  5400.00
  Tax (20%) :  $  1080.00
------------------------------------------------------
  Net Pay   :  $  4320.00
======================================================

Employee ID: 202 — David Lee
======================================================
         PAYSLIP — CONTRACT
======================================================
  Employee  :  David Lee
  ID        :  202
  Type      :  Contract
------------------------------------------------------
  Gross Pay :  $  4400.00
  Tax (20%) :  $   880.00
------------------------------------------------------
  Net Pay   :  $  3520.00
======================================================

Employee ID: 301 — Eve Martin
======================================================
         PAYSLIP — INTERN
======================================================
  Employee  :  Eve Martin
  ID        :  301
  Type      :  Intern
------------------------------------------------------
  Gross Pay :  $  1200.00
  Tax (20%) :  $   240.00
------------------------------------------------------
  Net Pay   :  $   960.00
======================================================

Employee ID: 302 — Frank Wilson
======================================================
         PAYSLIP — INTERN
======================================================
  Employee  :  Frank Wilson
  ID        :  302
  Type      :  Intern
------------------------------------------------------
  Gross Pay :  $  1000.00
  Tax (20%) :  $   200.00
------------------------------------------------------
  Net Pay   :  $   800.00
======================================================

Processed 6 employee(s) successfully.
```

### Console log output

```
2026-07-04 16:20:51 | __main__ | INFO     | ========================================
2026-07-04 16:20:51 | __main__ | INFO     | Payroll Tracker started
2026-07-04 16:20:51 | __main__ | INFO     | ========================================
2026-07-04 16:20:51 | src.employee_payroll_tracker.employe | INFO     | Created Full-Time employee: Alice Johnson (ID: 101)
2026-07-04 16:20:51 | src.employee_payroll_tracker.employe | INFO     | Created Full-Time employee: Bob Smith (ID: 102)
2026-07-04 16:20:51 | src.employee_payroll_tracker.employe | INFO     | Created Contract employee: Carol Davis (ID: 201)
2026-07-04 16:20:51 | src.employee_payroll_tracker.employe | INFO     | Created Contract employee: David Lee (ID: 202)
2026-07-04 16:20:51 | src.employee_payroll_tracker.employe | INFO     | Created Intern employee: Eve Martin (ID: 301)
2026-07-04 16:20:51 | src.employee_payroll_tracker.employe | INFO     | Created Intern employee: Frank Wilson (ID: 302)
2026-07-04 16:20:51 | __main__ | INFO     | Loaded 6 employee(s) for processing
2026-07-04 16:20:51 | src.employee_payroll_tracker.payroll | INFO     | Applied tax: gross=5500.00, tax=1100.00 (20%), net=4400.00
2026-07-04 16:20:51 | src.employee_payroll_tracker.payroll | INFO     | Generated payslip for Alice Johnson (ID: 101)
2026-07-04 16:20:51 | src.employee_payroll_tracker.payroll | INFO     | Applied tax: gross=4500.00, tax=900.00 (20%), net=3600.00
2026-07-04 16:20:51 | src.employee_payroll_tracker.payroll | INFO     | Generated payslip for Bob Smith (ID: 102)
2026-07-04 16:20:51 | src.employee_payroll_tracker.payroll | INFO     | Applied tax: gross=5400.00, tax=1080.00 (20%), net=4320.00
2026-07-04 16:20:51 | src.employee_payroll_tracker.payroll | INFO     | Generated payslip for Carol Davis (ID: 201)
...
2026-07-04 16:20:51 | src.employee_payroll_tracker.payroll | INFO     | Payroll complete — 6 employee(s) processed
2026-07-04 16:20:51 | __main__ | INFO     | Processed 6 employee(s) successfully.
2026-07-04 16:20:51 | __main__ | INFO     | Payroll Tracker finished
```

## Employee types

| Type              | Pay calculation            | Constructor parameters                                   |
|-------------------|----------------------------|----------------------------------------------------------|
| `FullTimeEmployee` | `base_salary + bonus`      | `emp_id`, `name`, `base_salary`, `bonus=0.0`            |
| `ContractEmployee` | `hourly_rate × hours_worked` | `emp_id`, `name`, `hourly_rate`, `hours_worked`          |
| `Intern`           | `stipend` (fixed)          | `emp_id`, `name`, `stipend`                              |
