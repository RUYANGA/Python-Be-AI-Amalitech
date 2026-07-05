import json
import os
from datetime import date
from .book import Book, EBook, AudioBook
from .author import Author
from .borrower import Borrower

LIBRARY_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "library.json"
)


def _load():
    """Load data from the JSON library file."""
    if not os.path.exists(LIBRARY_FILE):
        return {"books": [], "authors": [], "borrowers": [], "borrowing_history": []}
    with open(LIBRARY_FILE) as file:
        return json.load(file)


def _save(data):
    """Save data to the JSON library file."""
    os.makedirs(os.path.dirname(LIBRARY_FILE), exist_ok=True)
    with open(LIBRARY_FILE, "w") as file:
        json.dump(data, file, indent=4)


def _from_dict(item):
    """Convert a dictionary to the appropriate Book subclass instance."""
    book_type = item.get("type", "book")
    if book_type == "ebook":
        return EBook.from_dict(item)
    if book_type == "audiobook":
        return AudioBook.from_dict(item)
    return Book.from_dict(item)


def _next_id(prefix, items):
    """Generate the next sequential ID for a given prefix."""
    nums = [
        int(item[len(prefix) :])
        for item in items
        if item.startswith(prefix) and item[len(prefix) :].isdigit()
    ]
    return f"{prefix}{max(nums) + 1:03d}" if nums else f"{prefix}001"


def get_all_books():
    """Return a list of all books in the library."""
    return [_from_dict(entry) for entry in _load()["books"]]


def get_all_authors():
    """Return a list of all registered authors."""
    return [Author.from_dict(entry) for entry in _load()["authors"]]


def get_all_borrowers():
    """Return a list of all registered borrowers."""
    return [Borrower.from_dict(entry) for entry in _load()["borrowers"]]


def add_book(title, author_id, publication_year, book_type="book", **kwargs):
    """Add a new book to the library and return it."""
    books = get_all_books()
    new_id = _next_id("B", [book.id for book in books])
    if book_type == "ebook":
        new_book = EBook(
            new_id,
            title,
            author_id,
            publication_year,
            kwargs["file_format"],
            kwargs["file_size"],
        )
    elif book_type == "audiobook":
        new_book = AudioBook(
            new_id,
            title,
            author_id,
            publication_year,
            kwargs["duration"],
            kwargs["narrator"],
        )
    else:
        new_book = Book(new_id, title, author_id, publication_year)
    data = _load()
    data["books"].append(new_book.to_dict())
    _save(data)
    return new_book


def add_author(name, biography=""):
    """Register a new author and return them."""
    authors = get_all_authors()
    new_id = _next_id("A", [author.id for author in authors])
    new_author = Author(new_id, name, biography)
    data = _load()
    data["authors"].append(new_author.to_dict())
    _save(data)
    return new_author


def add_borrower(name, email):
    """Register a new borrower and return them."""
    borrowers = get_all_borrowers()
    new_id = _next_id("BR", [borrower.id for borrower in borrowers])
    new_borrower = Borrower(new_id, name, email)
    data = _load()
    data["borrowers"].append(new_borrower.to_dict())
    _save(data)
    return new_borrower


def search_books(title=None, author_id=None, available=None):
    """Search books by title, author, or availability using list comprehensions."""
    results = get_all_books()
    if title:
        results = [book for book in results if title.lower() in book.title.lower()]
    if author_id:
        results = [book for book in results if book.author_id == author_id]
    if available is not None:
        results = [book for book in results if book.available == available]
    return results


def borrow_book(book_id, borrower_id):
    """Borrow a book to a borrower. Returns (success, message)."""
    data = _load()
    target_book = next(
        (entry for entry in data["books"] if entry["id"] == book_id), None
    )
    target_borrower = next(
        (entry for entry in data["borrowers"] if entry["id"] == borrower_id), None
    )
    if not target_book:
        return False, "Book not found."
    if not target_borrower:
        return False, "Borrower not found."
    if not target_book.get("available", True):
        return False, "Book is already borrowed."
    target_book["available"] = False
    target_book["borrower_id"] = borrower_id
    data["borrowing_history"].append(
        {
            "book_id": book_id,
            "borrower_id": borrower_id,
            "borrow_date": str(date.today()),
            "return_date": None,
        }
    )
    _save(data)
    return True, f"Book '{target_book['title']}' borrowed successfully."


def return_book(book_id):
    """Return a borrowed book. Returns (success, message)."""
    data = _load()
    target_book = next(
        (entry for entry in data["books"] if entry["id"] == book_id), None
    )
    if not target_book:
        return False, "Book not found."
    if target_book.get("available", True):
        return False, "Book was not borrowed."
    target_book["available"] = True
    target_book["borrower_id"] = None
    unmatched = [
        r
        for r in data["borrowing_history"]
        if r["book_id"] == book_id and r["return_date"] is None
    ]
    if unmatched:
        unmatched[-1]["return_date"] = str(date.today())
    _save(data)
    return True, f"Book '{target_book['title']}' returned successfully."


def get_available_books():
    """Return a list of all currently available books."""
    return search_books(available=True)


def get_borrowed_books():
    """Return a list of all currently borrowed books."""
    return search_books(available=False)


def get_books_by_author(author_id):
    """Return all books written by a specific author."""
    return [book for book in get_all_books() if book.author_id == author_id]


def _author_name(author_id):
    """Return the author's name given their ID."""
    return next(
        (author.name for author in get_all_authors() if author.id == author_id),
        author_id,
    )


def _borrower_name(borrower_id):
    """Return the borrower's name given their ID."""
    return next(
        (
            borrower.name
            for borrower in get_all_borrowers()
            if borrower.id == borrower_id
        ),
        borrower_id,
    )


def report_available_books():
    """Generate a formatted report of all available books."""
    books = get_available_books()
    if not books:
        return "No available books."
    lines = [
        f"  {book.id}: {book.title} by {_author_name(book.author_id)}" for book in books
    ]
    return "Available Books:\n" + "\n".join(lines)


def report_borrowed_books():
    """Generate a formatted report of all borrowed books."""
    books = get_borrowed_books()
    if not books:
        return "No borrowed books."
    lines = [
        f"  {book.id}: {book.title} by {_author_name(book.author_id)} -> {_borrower_name(book.borrower_id)}"
        for book in books
    ]
    return "Borrowed Books:\n" + "\n".join(lines)


def report_books_by_author(author_id):
    """Generate a formatted report of books by a specific author."""
    books = get_books_by_author(author_id)
    name = _author_name(author_id)
    if not books:
        return f"No books found for author '{name}'."
    lines = [
        f"  {book.id}: {book.title} ({'Available' if book.available else 'Borrowed'})"
        for book in books
    ]
    return f"Books by {name}:\n" + "\n".join(lines)


def report_all_books():
    """Generate a formatted report of every book in the library."""
    books = get_all_books()
    if not books:
        return "No books in the library."
    lines = [
        f"  {book.id}: {book.title} by {_author_name(book.author_id)} ({'Avail' if book.available else 'Brwd'})"
        for book in books
    ]
    return "All Books:\n" + "\n".join(lines)


def report_all_authors():
    """Generate a formatted report of all registered authors."""
    authors = get_all_authors()
    if not authors:
        return "No authors registered."
    lines = [
        f"  {author.id}: {author.name} ({len(get_books_by_author(author.id))} book(s))"
        for author in authors
    ]
    return "All Authors:\n" + "\n".join(lines)


def report_all_borrowers():
    """Generate a formatted report of all registered borrowers."""
    borrowers = get_all_borrowers()
    if not borrowers:
        return "No borrowers registered."
    lines = [
        f"  {borrower.id}: {borrower.name} ({borrower.email})" for borrower in borrowers
    ]
    return "All Borrowers:\n" + "\n".join(lines)
