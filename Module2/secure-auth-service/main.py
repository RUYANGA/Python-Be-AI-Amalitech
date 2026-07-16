"""CLI entry point for the Secure Auth Service."""

import sys

from app.exceptions import (
    InvalidCredentialsError,
    InvalidPasswordError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.repositories.in_memory_repository import InMemoryRepository
from app.security.bcrypt_hasher import BcryptPasswordHasher
from app.services.user_service import UserService


def main() -> None:
    """Run the interactive auth CLI."""
    repo = InMemoryRepository()
    hasher = BcryptPasswordHasher()
    service = UserService(repository=repo, hasher=hasher)

    while True:
        print("\n=== Secure Auth Service ===")
        print("1. Register")
        print("2. Login")
        print("3. Exit")

        choice = input("\nSelect option: ").strip()

        if choice == "1":
            register(service)
        elif choice == "2":
            login(service)
        elif choice == "3":
            print("Goodbye!")
            sys.exit(0)
        else:
            print("Invalid option. Try again.")


def register(service: UserService) -> None:
    """Handle user registration."""
    print("\n--- Register ---")
    username = input("Username: ").strip()
    password = input("Password: ").strip()

    try:
        service.register(username, password)
        print(f"User '{username}' registered successfully!")
    except UserAlreadyExistsError:
        print(f"Error: User '{username}' already exists.")
    except InvalidPasswordError as e:
        print(f"Error: {e}")


def login(service: UserService) -> None:
    """Handle user login."""
    print("\n--- Login ---")
    username = input("Username: ").strip()
    password = input("Password: ").strip()

    try:
        user = service.login(username, password)
        print(f"Welcome, {user.username}!")
    except UserNotFoundError:
        print("Error: User not found.")
    except InvalidCredentialsError:
        print("Error: Invalid password.")


if __name__ == "__main__":
    main()
