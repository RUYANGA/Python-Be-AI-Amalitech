class Borrower:
    """Represents a library patron who can borrow books."""

    def __init__(self, id_, name, email):
        self._id = id_
        self._name = name
        self._email = email

    @property
    def id(self):
        """Unique identifier for the borrower."""
        return self._id

    @property
    def name(self):
        """Full name of the borrower."""
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def email(self):
        """Email address of the borrower."""
        return self._email

    @email.setter
    def email(self, value):
        self._email = value

    def to_dict(self):
        """Serialize borrower to a dictionary."""
        return {"id": self._id, "name": self._name, "email": self._email}

    @staticmethod
    def from_dict(data):
        """Create a Borrower instance from a dictionary."""
        return Borrower(data["id"], data["name"], data["email"])

    def __repr__(self):
        return f"Borrower({self._id}, '{self._name}')"

    def __eq__(self, other):
        return isinstance(other, Borrower) and self._id == other._id
