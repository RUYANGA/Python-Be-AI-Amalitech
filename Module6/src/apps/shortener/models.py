"""Django models for URL shortening, tagging, and click analytics.

These are the single source of truth for the ``urls``, ``tags``,
``clicks`` and the ``urls_tags`` join table.  All data access goes
through Django's built-in ORM (the repository layer in
``apps.shortener.api.repositories``).
"""

from django.conf import settings
from django.db import models


class URL(models.Model):
    original_url = models.URLField(max_length=2048)
    short_code = models.CharField(max_length=10, unique=True, db_index=True)
    title = models.CharField(max_length=255, blank=True, default="")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="urls",
        db_index=False,
    )
    click_count = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    last_accessed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    tags = models.ManyToManyField(
        "Tag",
        blank=True,
        related_name="urls",
        db_table="urls_tags",
    )

    class Meta:
        db_table = "urls"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["owner"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["original_url"]),
        ]

    def __str__(self) -> str:
        return f"{self.short_code} -> {self.original_url[:50]}"


class Click(models.Model):
    url = models.ForeignKey(URL, on_delete=models.CASCADE, related_name="clicks")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")
    country = models.CharField(max_length=2, blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    referer = models.URLField(max_length=2048, blank=True, default="")
    clicked_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "clicks"
        ordering = ["-clicked_at"]
        indexes = [
            models.Index(fields=["url", "-clicked_at"]),
            models.Index(fields=["country", "-clicked_at"]),
        ]

    def __str__(self) -> str:
        return f"Click on {self.url_id} at {self.clicked_at}"


class Tag(models.Model):
    name = models.CharField(max_length=64, unique=True, db_index=True)

    class Meta:
        db_table = "tags"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
