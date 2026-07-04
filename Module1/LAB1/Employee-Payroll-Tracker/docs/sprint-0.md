# Sprint 0 — Project Setup & Environment

**Duration:** Initial phase
**Goal:** Establish the project structure, toolchain, and development environment.

## Objectives

- Initialize a Poetry-managed Python project with Python >= 3.12
- Configure the `src` layout for package distribution
- Set up tooling for code quality (Pyright, Pylance)
- Add `.gitignore` to exclude build artifacts and cache directories
- Create initial placeholders for source code and tests

## Deliverables

| Artifact              | Description                                |
|-----------------------|--------------------------------------------|
| `pyproject.toml`      | Poetry project metadata and build config   |
| `src/` directory      | Source layout with `employee_payroll_tracker` package |
| `tests/` directory    | Test suite placeholder                     |
| `.gitignore`          | Ignore rules for Python, cache, and logs   |
| `pyrightconfig.json`  | Static analysis configuration              |

## Key decisions

- **Poetry** for dependency management and packaging
- **`src` layout** to keep source code separate from project root and avoid import ambiguity
- **Rotating file handler** for logging (5 MB per file, 3 backups) alongside console output

## Commits

- `803b627` — Initial payroll processing setup
- `84e5564` — Fix circular imports, add logger module, add pyrightconfig and .gitignore
