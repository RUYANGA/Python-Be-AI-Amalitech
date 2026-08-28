"""Django models for URL shortening, tagging, and click analytics.

These are the single source of truth for the ``urls``, ``tags``,
``clicks`` and the ``urls_tags`` join table.  All data access goes
through Django's built-in ORM (the repository layer in
``apps.shortener.api.repositories``).
"""

from django.conf import settings
from django.db import models
from django.db.models import Count, F, Q
from django.utils import timezone


class URLManager(models.Manager):
    def active_urls(self):
        """Return only active, non-expired URLs."""
        now = timezone.now()
        active = Q(expires_at__isnull=True) | Q(expires_at__gt=now)
        return self.filter(is_active=True).filter(active)

    def expired_urls(self):
        """Return URLs past their ``expires_at``."""
        return self.filter(expires_at__isnull=False, expires_at__lte=timezone.now())

    def popular_urls(self):
        """Return URLs ordered by ``click_count`` descending."""
        return self.order_by("-click_count")

    def with_tags(self):
        """Prefetch the tag relation to avoid N+1 queries."""
        return self.prefetch_related("tags")


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
    click_count = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
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

    objects = URLManager()

    class Meta:
        db_table = "urls"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["owner", "-created_at"]),
            models.Index(fields=["-click_count"]),
            models.Index(fields=["is_active", "expires_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.short_code} -> {self.original_url[:50]}"


class ClickManager(models.Manager):
    def record(self, url, ip_address=None, user_agent="", referer="", country=""):
        """Create a click row and atomically bump the URL counter."""
        click = self.create(
            url=url,
            ip_address=ip_address,
            user_agent=user_agent,
            referer=referer,
            country=country,
        )
        URL.objects.filter(pk=url.pk).update(
            click_count=F("click_count") + 1,
            last_accessed_at=timezone.now(),
        )
        return click

    def country_breakdown(self, url, limit=10):
        """Aggregate clicks by country code, excluding empty values."""
        return list(
            self.filter(url=url)
            .exclude(country="")
            .values("country")
            .annotate(clicks=Count("id"))
            .order_by("-clicks")[:limit]
        )

    def referrer_breakdown(self, url, limit=10):
        """Aggregate clicks by referer, excluding empty values."""
        return list(
            self.filter(url=url)
            .exclude(referer="")
            .values("referer")
            .annotate(clicks=Count("id"))
            .order_by("-clicks")[:limit]
        )

    def total_for(self, url):
        """Total number of clicks for ``url``."""
        return self.filter(url=url).count()

    def last_clicked_at(self, url):
        """Most recent click timestamp for ``url``, if any."""
        return self.filter(url=url).values_list("clicked_at", flat=True).first()


class Click(models.Model):
    url = models.ForeignKey(URL, on_delete=models.CASCADE, related_name="clicks")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")
    country = models.CharField(max_length=2, blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    referer = models.URLField(max_length=2048, blank=True, default="")
    clicked_at = models.DateTimeField(auto_now_add=True, db_index=True)

    objects = ClickManager()

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
