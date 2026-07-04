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
tests/
pyproject.toml
```

## Requirements

- Python >= 3.12
- [Poetry](https://python-poetry.org/) (dependency manager)

## Setup

```bash
git clone <repo-url>
cd Module1/LAB1/Employee-Payroll-Tracker
poetry install
```

## Usage

Run the payroll demonstration with sample employees:

```bash
poetry run python -m src.employee_payroll_tracker.main
```

## Employee types

| Type              | Pay calculation            | Constructor parameters                                   |
|-------------------|----------------------------|----------------------------------------------------------|
| `FullTimeEmployee` | `base_salary + bonus`      | `emp_id`, `name`, `base_salary`, `bonus=0.0`            |
| `ContractEmployee` | `hourly_rate × hours_worked` | `emp_id`, `name`, `hourly_rate`, `hours_worked`          |
| `Intern`           | `stipend` (fixed)          | `emp_id`, `name`, `stipend`                              |

## Testing

```bash
poetry run pytest
```
