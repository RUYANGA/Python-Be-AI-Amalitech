# Library Inventory System

A Python-based CLI application for managing a library's book inventory, patrons, and borrowing workflow. Supports three resource types: **Print Books**, **EBooks**, and **AudioBooks**.

## Features

- **Resource hierarchy** — Abstract `LibraryResource` base class with `Book`, `EBook`, and `AudioBook` subclasses
- **Author & Borrower management** — Register and list authors and borrowers
- **CRUD operations** — Add books, authors, and borrowers via CLI menu
- **Borrowing workflow** — Borrow and return books with automatic history tracking
- **Search & filtering** — Search books by title, author, or availability using list comprehensions
- **Reporting** — Formatted reports for available books, borrowed books, books by author, and full inventory
- **JSON persistence** — All data saved to a `library.json` file

## Project structure

```
src/
  library_inventory/
    __init__.py       Package initializer
    book.py           LibraryResource ABC, Book, EBook, AudioBook
    author.py         Author model
    borrower.py       Borrower model
    utils.py          Service layer: CRUD, search, reports, persistence
    main.py           CLI entry point with interactive menu
    data/
      library.json    Persistent JSON data store
tests/
pyproject.toml
README.md
```

## Requirements

- **Python** >= 3.12
- **Poetry** >= 2.0

## Setup

### 1. Clone and navigate

```bash
git clone <repo-url>
cd Module1/LAB2/Library-Inventory
```

### 2. Install dependencies

```bash
poetry install
```

## Usage

### Run the interactive CLI

```bash
poetry run python -m src.library_inventory.main
```

### Menu options

| #  | Option                | Description                          |
|----|-----------------------|--------------------------------------|
| 1  | Add Book              | Add a print, ebook, or audiobook     |
| 2  | Add Author            | Register a new author                |
| 3  | Add Borrower          | Register a new borrower              |
| 4  | Search Books          | Search books by title                |
| 5  | Borrow Book           | Borrow a book to a borrower          |
| 6  | Return Book           | Return a borrowed book               |
| 7  | Show Available Books  | List all currently available books   |
| 8  | Show Borrowed Books   | List all currently borrowed books    |
| 9  | Show Books by Author  | List books grouped by author         |
| 10 | Show All Books        | List every book in the library       |
| 11 | Show All Authors      | List all registered authors          |
| 12 | Show All Borrowers    | List all registered borrowers        |
| 13 | Exit                  | Quit the application                 |

## Example session

```
==================================================
          LIBRARY INVENTORY SYSTEM
==================================================
   1.  Add Book
   2.  Add Author
   3.  Add Borrower
   4.  Search Books
   5.  Borrow Book
   6.  Return Book
   7.  Show Available Books
   8.  Show Borrowed Books
   9.  Show Books by Author
  10.  Show All Books
  11.  Show All Authors
  12.  Show All Borrowers
  13.  Exit
==================================================
Enter your choice: 2
Author name: George Orwell
Biography (optional): Author of 1984
Added: Author(A001, 'George Orwell')

Enter your choice: 1
Title: 1984
  A001: George Orwell
Author ID: A001
Publication Year: 1949
Book type: (1) Print  (2) EBook  (3) AudioBook
Choice: 1
Added: Book(B001, '1984', avail=True)

Enter your choice: 3
Borrower name: Alice
Email: alice@email.com
Added: Borrower(BR001, 'Alice')

Enter your choice: 5
  BR001: Alice
Book ID: B001
Borrower ID: BR001
Book '1984' borrowed successfully.

Enter your choice: 7
Available Books:
  B002: Harry Potter by George Orwell

Enter your choice: 8
Borrowed Books:
  B001: 1984 by George Orwell -> Alice

Enter your choice: 10
All Books:
  B001: 1984 by George Orwell (Brwd)
  B002: Harry Potter by George Orwell (Avail)

Enter your choice: 11
All Authors:
  A001: George Orwell (2 book(s))
  A002: J.K. Rowling (1 book(s))

Enter your choice: 13
Goodbye!
```

## Resource types

| Type         | Extra parameters                        |
|--------------|-----------------------------------------|
| `Book`       | `author_id`, `publication_year`         |
| `EBook`      | `file_format`, `file_size`              |
| `AudioBook`  | `duration`, `narrator`                  |
