import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from datetime import date, timedelta
from django.db.models import Q


class DeviceStatusConsumer(AsyncWebsocketConsumer):
    GROUP_NAME = 'device_status'

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
        from .models import Device
        today = date.today()
        total = Device.objects.count()
        active = Device.objects.filter(status='active').count()
        maintenance = Device.objects.filter(status='maintenance').count()
        critical = Device.objects.filter(
            next_maintenance__isnull=False
        ).filter(
            Q(next_maintenance__lt=today) |
            Q(next_maintenance__lte=today + timedelta(days=3))
        ).count()
        health = round((active / total) * 100, 1) if total else 0
        return {
            'total_devices': total,
            'active_devices': active,
            'maintenance_devices': maintenance,
            'critical_alerts': critical,
            'system_health': health,
            'timestamp': timezone.now().isoformat(),
        }
