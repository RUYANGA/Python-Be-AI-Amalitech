"""Custom user model.

Extends ``AbstractUser`` with premium-tier fields so that later modules
(Module 7: RBAC) can extend it without a disruptive migration to
``AUTH_USER_MODEL``.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    TIER_CHOICES = [
        ("free", "Free"),
        ("basic", "Basic"),
        ("pro", "Pro"),
        ("enterprise", "Enterprise"),
    ]

    is_premium = models.BooleanField(default=False)
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, default="free")

    class Meta:
        db_table = "users"
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self) -> str:
        return self.username
