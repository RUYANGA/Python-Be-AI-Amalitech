"""Custom user model.

This is the *only* copy of the user identity in the whole system — the
shortener and analytics services never query it directly; they read
``user_id``/``is_premium``/``tier`` off the JWT claims this service embeds
at login time (see ``JWTTokenService.generate_tokens``).
"""

from django.contrib.auth.models import AbstractUser
from django.db import models

PREMIUM_TIERS = {"pro", "enterprise"}


class User(AbstractUser):
    TIER_CHOICES = [
        ("free", "Free"),
        ("basic", "Basic"),
        ("pro", "Pro"),
        ("enterprise", "Enterprise"),
    ]

    is_premium = models.BooleanField(default=False)
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, default="free")
    email = models.EmailField(unique=True)

    class Meta:
        db_table = "users"
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self) -> str:
        return self.username

    @property
    def is_premium_tier(self) -> bool:
        """True if this user has premium access.

        Either the ``is_premium`` flag is set directly, or their ``tier``
        is one of the premium tiers (``pro``, ``enterprise``).
        """
        return self.is_premium or self.tier in PREMIUM_TIERS
