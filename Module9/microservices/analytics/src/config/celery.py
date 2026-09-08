"""Celery application for the analytics service.

Backs the write-behind click-ingestion path: ``ClickIngestView`` enqueues
``apps.analytics.tasks.track_click_task`` instead of writing the
``Click`` row (and doing the geo lookup) in-process, so a burst of
traffic on the hot redirect path never blocks on — or is throttled by —
database writes.
"""

from __future__ import annotations

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("analytics")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
