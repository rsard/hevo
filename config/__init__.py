"""Exposes the Celery app so it's loaded whenever Django starts."""

from config.celery import app as celery_app

__all__ = ['celery_app']
