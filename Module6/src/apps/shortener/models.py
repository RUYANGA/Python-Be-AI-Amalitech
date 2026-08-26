"""Django model stubs — ``managed = False`` so Django leaves these
tables alone.  All data access goes through SQLAlchemy models in
``database.shortener.models``.
"""

from django.db import models


class URL(models.Model):
    original_url = models.URLField(max_length=2048)
    short_code = models.CharField(max_length=10, unique=True, db_index=True)
    title = models.CharField(max_length=255, blank=True, default="")
    click_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "urls"
        managed = False

    def __str__(self) -> str:
        return f"{self.short_code} -> {self.original_url[:50]}"


class Click(models.Model):
    url = models.ForeignKey(URL, on_delete=models.CASCADE, related_name="clicks")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    country = models.CharField(max_length=2, blank=True, default="")
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
