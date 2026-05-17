import os
from importlib.util import find_spec

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_system.settings')

if find_spec('channels') is not None:
    import django
    from django.core.asgi import get_asgi_application

    django.setup()

    from channels.routing import ProtocolTypeRouter, URLRouter
    from channels.auth import AuthMiddlewareStack
    from channels.security.websocket import AllowedHostsOriginValidator
    from django.urls import path
    from devices.consumers import DeviceStatusConsumer

    application = ProtocolTypeRouter({
        'http': get_asgi_application(),
        'websocket': AllowedHostsOriginValidator(
            AuthMiddlewareStack(
                URLRouter([
                    path('ws/device-status/', DeviceStatusConsumer.as_asgi()),
                ])
            )
        ),
    })
else:
    from django.core.asgi import get_asgi_application

    application = get_asgi_application()
