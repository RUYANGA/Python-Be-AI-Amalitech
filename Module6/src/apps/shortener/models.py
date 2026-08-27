"""Django model stubs — ``managed = False`` so Django leaves these
tables alone.  All data access goes through SQLAlchemy models in
``database.shortener.models``.
"""

from django.conf import settings
from django.db import models


class URLManager(models.Manager):
    def active_urls(self):
        """Return only active, non-expired URLs."""
        from django.utils import timezone

        now = timezone.now()
        return self.filter(is_active=True).filter(
            models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=now)
        )

    def expired_urls(self):
        """Return URLs past their ``expires_at``."""
        from django.utils import timezone

        return self.filter(expires_at__isnull=False, expires_at__lte=timezone.now())

    def popular_urls(self):
        """Return URLs ordered by ``click_count`` descending."""
        return self.order_by("-click_count")


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
    )
    click_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    last_accessed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = URLManager()

    class Meta:
        db_table = "urls"
        managed = False

    def __str__(self) -> str:
        return f"{self.short_code} -> {self.original_url[:50]}"


class Click(models.Model):
    url = models.ForeignKey(URL, on_delete=models.CASCADE, related_name="clicks")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    country = models.CharField(max_length=2, blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    referer = models.URLField(max_length=2048, blank=True, default="")
    clicked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "clicks"
        managed = False

    def __str__(self) -> str:
        return f"Click on {self.url_id} at {self.clicked_at}"


class Tag(models.Model):
    name = models.CharField(max_length=64, unique=True, db_index=True)

    class Meta:
        db_table = "tags"
        managed = False

    def __str__(self) -> str:
        return self.name
