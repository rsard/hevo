"""Celery application setup; autodiscovers tasks from installed apps."""

import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

app = Celery('hevo')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
