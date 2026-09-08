"""Django models for the preview app.

Deliberately empty: this service is stateless beyond Redis (the result
cache and circuit-breaker state — see ``apps.preview.api.cache`` and
``apps.preview.api.services.circuit_breaker``). It's still provisioned
with its own Postgres database, for parity with ``auth``/``shortener``/
``analytics`` (the shared ``Dockerfile`` unconditionally runs
``manage.py migrate`` on start, which needs a real database to migrate
``django.contrib.contenttypes`` into even with no domain tables of its
own) — see the "Known simplifications" section of this service's README.
"""

from django.db import models  # noqa: F401
