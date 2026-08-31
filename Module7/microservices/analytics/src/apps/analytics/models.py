"""Django models for click analytics.

Keyed by ``short_code`` (a plain string), not a foreign key to the
shortener service's ``URL`` row — that row lives in another service's
database entirely. ``short_code`` is exactly what the shortener service
publishes on the ``clicks`` Kafka topic (see
``apps.analytics.management.commands.consume_clicks``), so no
cross-service lookup is needed just to record a click.
"""

from django.db import models


class Click(models.Model):
    short_code = models.CharField(max_length=10, db_index=True)
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
            models.Index(fields=["short_code", "-clicked_at"]),
            models.Index(fields=["country", "-clicked_at"]),
        ]

    def __str__(self) -> str:
        return f"Click on {self.short_code} at {self.clicked_at}"
