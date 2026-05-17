import json

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

from .realtime import DEVICES_BROADCAST_GROUP, get_device_stats_payload


class DeviceStatusConsumer(AsyncWebsocketConsumer):
    GROUP_NAME = DEVICES_BROADCAST_GROUP

    async def connect(self):
        if not self.scope['user'].is_authenticated:
            await self.close()
            return
        await self.channel_layer.group_add(self.GROUP_NAME, self.channel_name)
        await self.accept()
        stats = await self.get_stats()
        await self.send(text_data=json.dumps({'type': 'stats_update', **stats}))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.GROUP_NAME, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        if data.get('type') == 'request_stats':
            stats = await self.get_stats()
            await self.send(text_data=json.dumps({'type': 'stats_update', **stats}))

    async def stats_update(self, event):
        await self.send(text_data=json.dumps(event))

    async def device_changed(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def get_stats(self):
        return get_device_stats_payload()
