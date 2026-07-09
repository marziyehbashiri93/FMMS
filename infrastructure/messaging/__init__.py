"""FMMS messaging package — Celery application and background tasks."""

from infrastructure.messaging.celery_app import app as celery_app

__all__ = ["celery_app"]
