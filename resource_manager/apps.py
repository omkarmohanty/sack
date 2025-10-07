"""App Configuration for Resource Manager"""
from django.apps import AppConfig

class ResourceManagerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'resource_manager'
    verbose_name = 'Resource Manager'

    def ready(self):
        # Import signal handlers
        try:
            from . import signals
        except ImportError:
            pass
