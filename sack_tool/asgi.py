"""ASGI config for sack_tool project."""
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sack_tool.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    # Add WebSocket routing here if needed in the future
})
