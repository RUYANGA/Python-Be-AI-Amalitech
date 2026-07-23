# Secure Auth Service

A production-quality authentication service built with **Test-Driven Development**, **SOLID principles**, and **Clean Architecture**.

## Architecture

```
                UserService
                     |
     +---------------+---------------+
     |                               |
UserRepository                 PasswordHasher
     |                               |
InMemoryRepository          BcryptPasswordHasher
```

`UserService` depends only on **interfaces** (protocols), not concrete implementations. This is the **Dependency Inversion Principle** in action.

## SOLID Principles

| Principle | How it's applied |
|-----------|-----------------|
| **S**ingle Responsibility | Each class has one job: `UserService` handles business logic, `BcryptPasswordHasher` hashes passwords, `InMemoryRepository` stores users |
| **O**pen/Closed | New hashers (e.g., Argon2) or repositories can be added without modifying `UserService` |
| **L**iskov Substitution | Any implementation of `UserRepository` or `PasswordHasher` protocol works interchangeably |
| **I**nterface Segregation | Protocols define only the methods needed: `save()`/`find()` for repository, `hash()`/`verify()` for hasher |
| **D**ependency Inversion | `UserService` depends on `UserRepository` and `PasswordHasher` protocols, not concrete classes |

## Project Structure

```
secure-auth-service/
├── app/
│   ├── __init__.py
│   ├── models.py              # User dataclass
│   ├── exceptions.py          # Custom exception hierarchy
│   ├── logger.py              # Centralized logging
│   ├── interfaces/
│   │   ├── password_hasher.py # PasswordHasher protocol
│   │   └── user_repository.py # UserRepository protocol
│   ├── repositories/
│   │   └── in_memory_repository.py
│   ├── security/
│   │   └── bcrypt_hasher.py
│   └── services/
│       └── user_service.py    # Core business logic
├── tests/
│   ├── test_registration.py
│   ├── test_login.py
│   ├── test_password_policy.py
│   ├── test_service_exceptions.py
│   ├── test_hasher.py
│   ├── test_repository.py
│   └── test_logger.py
├── .github/workflows/ci.yml
├── .pre-commit-config.yaml
├── pyproject.toml
└── requirements.txt
```

## Installation

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e ".[dev]"
```

## Run the App

```bash
python main.py
```

## Usage

```python
from app.repositories.in_memory_repository import InMemoryRepository
from app.security.bcrypt_hasher import BcryptPasswordHasher
from app.services.user_service import UserService

repo = InMemoryRepository()
hasher = BcryptPasswordHasher()
service = UserService(repository=repo, hasher=hasher)

# Register
service.register("alice", "SecureP@ss1")

# Login
user = service.login("alice", "SecureP@ss1")
print(user.username)
```

## Password Policy

| Rule | Example Fail | Example Pass |
|------|-------------|-------------|
| Minimum 8 characters | `Ab1!` | `Password1!` |
| Uppercase letter | `password1!` | `Password1!` |
| Lowercase letter | `PASSWORD1!` | `Password1!` |
| Digit | `Password!` | `Password1!` |
| Special character | `Password1` | `Password1!` |

## Running Tests

```bash
pytest tests/ -v
```

## Coverage

```bash
pytest tests/ --cov=app --cov-branch --cov-report=term-missing
```

Expected output: **100% branch coverage** across all modules.

## Code Quality Tools

| Tool | Command | Purpose |
|------|---------|---------|
| **Black** | `black app/ tests/` | Code formatting |
| **Ruff** | `ruff check app/ tests/` | Linting (unused imports, style, complexity) |
| **Mypy** | `mypy app/` | Static type checking |
| **Pytest** | `pytest tests/` | Testing |
| **Coverage** | `coverage report` | Coverage reporting |

## Pre-commit Hooks

```bash
pre-commit install
```

Hooks run automatically on every commit: Black -> Ruff -> Mypy -> Pytest.

## CI/CD

GitHub Actions pipeline runs on every push:
1. Checkout code
2. Install dependencies
3. Black formatting check
4. Ruff linting
5. Mypy type checking
6. Pytest with 100% coverage enforcement

## TDD Process

Every feature follows **Red -> Green -> Refactor**:

1. **RED**: Write a failing test
2. **GREEN**: Write minimal code to pass
3. **REFACTOR**: Improve code while tests stay green

## Git Strategy

```
main
 └── develop
      ├── feature/registration
      ├── feature/login
      └── feature/password-policy
```

## Custom Exceptions

```
AuthError (base)
├── UserAlreadyExistsError
├── InvalidPasswordError
├── UserNotFoundError
└── InvalidCredentialsError
```

## Security

- Passwords are **never** stored in plaintext
- Uses `bcrypt` with configurable work factor (default: 12 rounds)
- Hashes include per-password salt
- Verification is timing-safe via `bcrypt.checkpw()`

## License

MIT
