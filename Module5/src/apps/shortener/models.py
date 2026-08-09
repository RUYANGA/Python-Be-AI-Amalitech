"""Data model for shortened URLs.

Module 5 fields only: ``original_url``, ``short_code``, ``owner``.
Later modules will add ``custom_alias``, ``expires_at``, ``click_count``,
``title``, ``description``, ``favicon`` and the ``Click`` + ``Tag``
relationships.
"""

from django.conf import settings
from django.db import models


class URL(models.Model):
    original_url = models.URLField(max_length=2048)
    short_code = models.CharField(max_length=10, unique=True, db_index=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="urls",
        null=True,
        blank=True,
        help_text="Optional owner. Anonymous creation is allowed in Module 5.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "urls"
        ordering = ["-created_at"]
        verbose_name = "URL"
        verbose_name_plural = "URLs"

    def __str__(self) -> str:
        return f"{self.short_code} → {self.original_url}"
