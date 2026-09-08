# Generated manually, matching Django's own generator style, for the
# preview-metadata fields backfilled asynchronously by the url-preview
# service (see apps.shortener.tasks.fetch_url_preview_task).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shortener", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="url",
            name="description",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="url",
            name="favicon_url",
            field=models.URLField(blank=True, default="", max_length=2048),
        ),
    ]
