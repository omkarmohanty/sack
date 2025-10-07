"""WSGI config for sack_tool project."""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sack_tool.settings')

application = get_wsgi_application()
