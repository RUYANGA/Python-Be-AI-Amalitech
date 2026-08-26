"""Custom user model.

Module 5 keeps this deliberately minimal — a thin subclass of
``AbstractUser`` so that later modules (Module 6: ``email`` unique,
``is_premium``, ``tier``; Module 7: RBAC) can extend it without a
disruptive migration to ``AUTH_USER_MODEL``.
"""

from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    class Meta:
        db_table = "users"
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self) -> str:
        return self.username
