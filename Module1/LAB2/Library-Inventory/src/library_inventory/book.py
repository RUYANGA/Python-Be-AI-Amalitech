from abc import ABC, abstractmethod

_FIELDS = ("id", "title", "author_id", "publication_year", "available", "borrower_id")


class LibraryResource(ABC):
    """Abstract base class for all library resources."""

    def __init__(self, id, title):
        self._id = id
        self._title = title

    @property
    def id(self):
        """Unique identifier for the resource."""
        return self._id

    @property
    def title(self):
        """Title of the resource."""
        return self._title

    @title.setter
    def title(self, value):
        self._title = value

    def __eq__(self, other):
        return isinstance(other, LibraryResource) and self._id == other._id

    def __hash__(self):
        return hash(self._id)

    @abstractmethod
    def to_dict(self):
        """Serialize resource to a dictionary."""

    @abstractmethod
    def __repr__(self):
        """Developer-friendly string representation."""


class Book(LibraryResource):
    """Represents a print book in the library."""

    def __init__(
        self, id, title, author_id, publication_year, available=True, borrower_id=None
    ):
        super().__init__(id, title)
        self._author_id = author_id
        self._publication_year = publication_year
        self._available = available
        self._borrower_id = borrower_id

    @property
    def author_id(self):
        """ID of the book's author."""
        return self._author_id

    @author_id.setter
    def author_id(self, value):
        self._author_id = value

    @property
    def publication_year(self):
        """Year the book was published."""
        return self._publication_year

    @publication_year.setter
    def publication_year(self, value):
        self._publication_year = value

    @property
    def available(self):
        """Whether the book is currently available."""
        return self._available

    @available.setter
    def available(self, value):
        self._available = value

    @property
    def borrower_id(self):
        """ID of the borrower who currently has the book, or None."""
        return self._borrower_id

    @borrower_id.setter
    def borrower_id(self, value):
        self._borrower_id = value

    def to_dict(self):
        return {field: getattr(self, field) for field in _FIELDS}

    @staticmethod
    def from_dict(data):
        """Create a Book instance from a dictionary."""
        return Book(**{field: data.get(field) for field in _FIELDS})

    def __repr__(self):
        return f"Book({self._id}, '{self._title}', avail={self._available})"

    def __eq__(self, other):
        return isinstance(other, Book) and self._id == other._id


class EBook(Book):
    """Represents a digital ebook in the library."""

    def __init__(
        self,
        id,
        title,
        author_id,
        publication_year,
        file_format,
        file_size,
        available=True,
        borrower_id=None,
    ):
        super().__init__(id, title, author_id, publication_year, available, borrower_id)
        self._file_format = file_format
        self._file_size = file_size

    @property
    def file_format(self):
        """File format of the ebook (e.g. PDF, EPUB)."""
        return self._file_format

    @file_format.setter
    def file_format(self, value):
        self._file_format = value

    @property
    def file_size(self):
        """File size of the ebook in MB."""
        return self._file_size

    @file_size.setter
    def file_size(self, value):
        self._file_size = value

    def to_dict(self):
        result = super().to_dict()
        result["file_format"] = self._file_format
        result["file_size"] = self._file_size
        return result

    @staticmethod
    def from_dict(data):
        """Create an EBook instance from a dictionary."""
        return EBook(
            data["id"],
            data["title"],
            data["author_id"],
            data["publication_year"],
            data["file_format"],
            data["file_size"],
            data.get("available", True),
            data.get("borrower_id"),
        )

    def __repr__(self):
        return f"EBook({self._id}, '{self._title}', {self._file_format})"


class AudioBook(Book):
    """Represents an audiobook in the library."""

    def __init__(
        self,
        id,
        title,
        author_id,
        publication_year,
        duration,
        narrator,
        available=True,
        borrower_id=None,
    ):
        super().__init__(id, title, author_id, publication_year, available, borrower_id)
        self._duration = duration
        self._narrator = narrator

    @property
    def duration(self):
        """Duration of the audiobook in minutes."""
        return self._duration

    @duration.setter
    def duration(self, value):
        self._duration = value

    @property
    def narrator(self):
        """Name of the audiobook narrator."""
        return self._narrator

    @narrator.setter
    def narrator(self, value):
        self._narrator = value

    def to_dict(self):
        result = super().to_dict()
        result["duration"] = self._duration
        result["narrator"] = self._narrator
        return result

    @staticmethod
    def from_dict(data):
        """Create an AudioBook instance from a dictionary."""
        return AudioBook(
            data["id"],
            data["title"],
            data["author_id"],
            data["publication_year"],
            data["duration"],
            data["narrator"],
            data.get("available", True),
            data.get("borrower_id"),
        )

    def __repr__(self):
        return f"AudioBook({self._id}, '{self._title}', {self._narrator})"
