"""Django application configuration for the preview app."""

from django.apps import AppConfig


class PreviewConfig(AppConfig):
    """Configuration for the preview app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.preview"
    verbose_name = "URL Preview"
