"""Seed default tags.

Creates the default tag set that ships with the application.
Uses ``get_or_create`` semantics so the migration is idempotent.

Generated manually — Django does not produce data migrations from
``makemigrations``.
"""

from django.db import migrations

DEFAULT_TAGS = [
    "marketing",
    "social",
    "campaign",
    "product",
    "blog",
    "newsletter",
    "partner",
    "internal",
]


def seed_tags(apps, _schema_editor):
    Tag = apps.get_model("shortener", "Tag")
    for name in DEFAULT_TAGS:
        Tag.objects.get_or_create(name=name)


def unseed_tags(apps, _schema_editor):
    Tag = apps.get_model("shortener", "Tag")
    Tag.objects.filter(name__in=DEFAULT_TAGS).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("shortener", "0005_alter_click_options_alter_tag_options_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_tags, unseed_tags),
    ]
