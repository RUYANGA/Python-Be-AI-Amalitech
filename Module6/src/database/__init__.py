"""SQLAlchemy declarative models — the primary data-access layer.

Models are split per Django app, mirroring the ``apps/*/models.py``
structure::

    database/
    ├── connection.py            # engine + session factory
    ├── shortener/models.py      # URLModel, ClickModel, TagModel
    └── users/models.py          # UserModel (read-only)

Django models in ``apps/*/models.py`` are thin stubs retained only for
DRF serializers and the Django admin.
"""

from database.connection import Base
from database.shortener.models import ClickModel, TagModel, URLModel, URLTagModel
from database.users.models import UserModel

__all__ = [
    "Base",
    "ClickModel",
    "TagModel",
    "URLModel",
    "URLTagModel",
    "UserModel",
]
