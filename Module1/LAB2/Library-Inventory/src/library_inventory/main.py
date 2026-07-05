import sys
from .utils import (
    add_book,
    add_author,
    add_borrower,
    search_books,
    borrow_book,
    return_book,
    get_all_authors,
    get_all_borrowers,
    _author_name,
    report_available_books,
    report_borrowed_books,
    report_books_by_author,
    report_all_books,
    report_all_authors,
    report_all_borrowers,
)


MENU_OPTIONS = [
    "Add Book",
    "Add Author",
    "Add Borrower",
    "Search Books",
    "Borrow Book",
    "Return Book",
    "Show Available Books",
    "Show Borrowed Books",
    "Show Books by Author",
    "Show All Books",
    "Show All Authors",
    "Show All Borrowers",
    "Exit",
]


def _menu():
    """Display the main menu with all available options."""
    print("\n" + "=" * 50)
    print("          LIBRARY INVENTORY SYSTEM")
    print("=" * 50)
    print("\n".join(f"  {i:2}.  {label}" for i, label in enumerate(MENU_OPTIONS, 1)))
    print("=" * 50)


def _prompt(message):
    """Prompt the user for input and return the trimmed response."""
    return input(message).strip()


def _show_authors():
    """List all authors and return the list, or None if empty."""
    authors = get_all_authors()
    if not authors:
        print("No authors registered. Please add an author first.")
        return None
    print("\n".join(f"  {a.id}: {a.name}" for a in authors))
    return authors


def _show_borrowers():
    """List all borrowers and return the list, or None if empty."""
    borrowers = get_all_borrowers()
    if not borrowers:
        print("No borrowers registered. Please add a borrower first.")
        return None
    print("\n".join(f"  {b.id}: {b.name}" for b in borrowers))
    return borrowers


def main():
    """Main application loop - displays menu and handles user choices."""
    while True:
        _menu()
        choice = _prompt("Enter your choice: ")
        print()

        if choice == "1":
            title = _prompt("Title: ")
            if not title:
                print("Title cannot be empty.")
                continue
            if not _show_authors():
                continue
            author_id = _prompt("Author ID: ")
            try:
                year = int(_prompt("Publication Year: "))
            except ValueError:
                print("Invalid year.")
                continue
            type_choice = _prompt(
                "Book type: (1) Print  (2) EBook  (3) AudioBook\nChoice: "
            )
            if type_choice == "2":
                new_book = add_book(
                    title,
                    author_id,
                    year,
                    book_type="ebook",
                    file_format=_prompt("File format: "),
                    file_size=float(_prompt("File size (MB): ")),
                )
            elif type_choice == "3":
                new_book = add_book(
                    title,
                    author_id,
                    year,
                    book_type="audiobook",
                    duration=float(_prompt("Duration (min): ")),
                    narrator=_prompt("Narrator: "),
                )
            else:
                new_book = add_book(title, author_id, year)
            print(f"Added: {new_book}")

        elif choice == "2":
            name = _prompt("Author name: ")
            if not name:
                print("Name cannot be empty.")
                continue
            print(f"Added: {add_author(name, _prompt('Biography (optional): '))}")

        elif choice == "3":
            name = _prompt("Borrower name: ")
            if not name:
                print("Name cannot be empty.")
                continue
            print(f"Added: {add_borrower(name, _prompt('Email: '))}")

        elif choice == "4":
            results = search_books(title=_prompt("Search by title: ") or None)
            if not results:
                print("No books found.")
            else:
                print(
                    "\n".join(
                        f"  {b.id}: {b.title} by {_author_name(b.author_id)} "
                        f"({'Avail' if b.available else 'Brwd'})"
                        for b in results
                    )
                )

        elif choice == "5":
            if not _show_borrowers():
                continue
            success, message = borrow_book(
                _prompt("Book ID: "), _prompt("Borrower ID: ")
            )
            print(message)

        elif choice == "6":
            success, message = return_book(_prompt("Book ID: "))
            print(message)

        elif choice == "7":
            print(report_available_books())
        elif choice == "8":
            print(report_borrowed_books())
        elif choice == "9":
            for author in get_all_authors():
                print(report_books_by_author(author.id))
                print()
        elif choice == "10":
            print(report_all_books())
        elif choice == "11":
            print(report_all_authors())
        elif choice == "12":
            print(report_all_borrowers())
        elif choice == "13":
            print("Goodbye!")
            sys.exit(0)
        else:
            print("Invalid choice. Enter 1-13.")


if __name__ == "__main__":
    main()
