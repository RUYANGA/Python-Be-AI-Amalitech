# Sprint 2 — Contract Employee, Intern & Payroll Processing

**Duration:** Development phase 2
**Goal:** Add remaining employee types, implement payroll computation, and wire up the CLI entry point.

## Objectives

- Implement `ContractEmployee` with `hourly_rate` and `hours_worked` (capped at 744/month)
- Implement `Intern` with a fixed `stipend`
- Build the payroll pipeline: `calculate_salary` → `apply_tax` → `generate_payslip`
- Apply a flat 20% tax rate on gross salary
- Create a `main.py` entry point with sample employees and formatted output

## Deliverables

| Module         | Key classes / functions                          |
|----------------|--------------------------------------------------|
| `employe.py`   | `ContractEmployee`, `Intern`                     |
| `payroll.py`   | `calculate_salary`, `apply_tax`, `generate_payslip`, `process_payroll` |
| `main.py`      | `main()` — entry point with demo data            |

## Key decisions

- **`isinstance` dispatch** in `calculate_salary` for type-specific pay logic (extensible without modifying employee classes)
- **Flat 20% tax** applied via `apply_tax()` — rate configurable via parameter but defaults to `TAX_RATE` constant
- **Payslip format** uses a 54-char wide bordered layout with gross, tax (20%), and net pay
- **Class design pattern**: `ContractEmployee` stores `hourly_rate` as the base `salary` field and `hours_worked` separately; `Intern` stores `stipend` as the base `salary`

## Commits

- `1c69d04` / `47d2a38` — Add ContractEmployee, Intern, and FullTimeEmployee classes
- `803b627` — Add payroll processing pipeline and main entry point
- `84e5564` — Fix `hourly_salary` → `hourly_rate` naming, fix circular imports, add logger
