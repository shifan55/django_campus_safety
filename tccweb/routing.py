"""ASGI routing configuration for websocket consumers."""

from django.urls import re_path

from tccweb.core import consumers as core_consumers

websocket_urlpatterns = [
    re_path(r"^ws/notifications/$", core_consumers.NotificationConsumer.as_asgi()),
]
