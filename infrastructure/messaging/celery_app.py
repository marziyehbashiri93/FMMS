"""Celery application factory for FMMS background tasks.

The Celery app is loaded from Django settings and autodiscovers task modules
under ``infrastructure.messaging.tasks``.
"""

from __future__ import annotations

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("fmms")
app.config_from_object("django.conf:settings", namespace="CELERY")
# Explicit imports keep task registration deterministic for workers and tests.
app.conf.imports = (
    "infrastructure.messaging.tasks.sap_retry_tasks",
    "infrastructure.messaging.tasks.sap_sync_tasks",
    "infrastructure.messaging.tasks.maintenance_tasks",
)
