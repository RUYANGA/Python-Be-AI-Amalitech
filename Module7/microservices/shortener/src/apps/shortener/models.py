"""Django models for URL shortening and tagging.

This service owns ``urls``, ``tags`` and the ``urls_tags`` join table.
Click events live in the *analytics* service's own database now, not
here — ``owner_id`` is a bare integer, not a foreign key, because the
owning ``User`` row lives in the *auth* service's database: there is no
single database left to enforce that relationship for us, so it is
enforced at the application layer (the JWT's ``user_id`` claim) instead.
"""

from django.db import models


class URL(models.Model):
    original_url = models.URLField(max_length=2048)
    short_code = models.CharField(max_length=10, unique=True, db_index=True)
    title = models.CharField(max_length=255, blank=True, default="")
    owner_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)
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
            models.Index(fields=["owner_id"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["original_url"]),
        ]

    def __str__(self) -> str:
        return f"{self.short_code} -> {self.original_url[:50]}"


class Tag(models.Model):
    name = models.CharField(max_length=64, unique=True, db_index=True)

    class Meta:
        db_table = "tags"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
