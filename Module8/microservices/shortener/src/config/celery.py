"""Celery application for the shortener service.

Runs the nightly ``archive_expired_urls`` job (see ``apps.shortener.tasks``
and ``CELERY_BEAT_SCHEDULE`` in settings). Click delivery itself stays a
fire-and-forget REST call to analytics (``ClickEventPublisher``) — the
write-behind persistence of a click lives in the analytics service's own
Celery app, not here, since that's the service that owns the ``clicks``
table.
"""

from __future__ import annotations

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("shortener")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
