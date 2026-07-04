class Author:
    """Represents a book author."""

    def __init__(self, id, name, biography=""):
        self._id = id
        self._name = name
        self._biography = biography

    @property
    def id(self):
        """Unique identifier for the author."""
        return self._id

    @property
    def name(self):
        """Full name of the author."""
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def biography(self):
        """Short biography of the author."""
        return self._biography

    @biography.setter
    def biography(self, value):
        self._biography = value

    def to_dict(self):
        """Serialize author to a dictionary."""
        return {"id": self._id, "name": self._name, "biography": self._biography}

    @staticmethod
    def from_dict(data):
        """Create an Author instance from a dictionary."""
        return Author(data["id"], data["name"], data.get("biography", ""))

    def __repr__(self):
        return f"Author({self._id}, '{self._name}')"

    def __eq__(self, other):
        return isinstance(other, Author) and self._id == other._id
