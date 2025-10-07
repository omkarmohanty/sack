"""Celery configuration for SACK Tool background tasks"""
import os
from celery import Celery

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sack_tool.settings')

app = Celery('sack_tool')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

# Periodic tasks for resource cleanup
from celery.schedules import crontab

app.conf.beat_schedule = {
    'cleanup-expired-sessions': {
        'task': 'resource_manager.tasks.cleanup_expired_sessions',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },
    'update-queue-estimates': {
        'task': 'resource_manager.tasks.update_queue_estimates',
        'schedule': crontab(minute='*/2'),  # Every 2 minutes
    },
}
