# Sprint 1 — Employee Core & Full-Time Employee

**Duration:** Development phase 1
**Goal:** Implement the abstract `Employee` base class and the `FullTimeEmployee` subclass with property validation.

## Objectives

- Define an abstract `Employee` base class with `emp_id`, `name`, and validated `salary`
- Enforce a contract via the abstract `employee_type()` method
- Implement `FullTimeEmployee` with a `bonus` property (non-negative validation)
- Provide reusable validation utilities (`validate_positive_number`, `validate_non_negative_number`)
- Add structured logging across all modules

## Deliverables

| Module         | Key classes / functions                      |
|----------------|----------------------------------------------|
| `employe.py`   | `Employee` (ABC), `FullTimeEmployee`         |
| `util.py`      | `validate_positive_number`, `validate_non_negative_number`, `format_currency` |
| `logger.py`    | `get_logger`                                 |
| `__init__.py`  | Re-exports for public API                    |

## Key decisions

- **Properties with setters** for salary, bonus — validation runs on assignment, not just construction
- **ABC** pattern ensures every employee type implements `employee_type()`
- **Centralised logger** with module-level caching (`_loggers` dict) to avoid duplicate handlers
- **Utility functions** raise `ValueError` — callers (setters) log a warning before re-raising

## Commits

- `52a4688` — Implement Employee abstract class and properties
- `a80b14e` — Add FullTimeEmployee inheriting from Employee
