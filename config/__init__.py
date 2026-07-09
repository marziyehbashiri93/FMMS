"""FMMS Django project package.

Loads the Celery app on Django startup so ``@shared_task`` bindings resolve.
"""

from __future__ import annotations

from infrastructure.messaging.celery_app import app as celery_app

__all__ = ["celery_app"]
