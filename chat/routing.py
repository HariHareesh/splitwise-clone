from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/(?P<room_type>group|expense)/(?P<room_id>\d+)/$', consumers.ChatConsumer.as_asgi()),
]