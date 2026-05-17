from datetime import date, timedelta

from importlib.util import find_spec

from asgiref.sync import async_to_sync
from django.db.models import Q
from django.utils import timezone

DEVICES_BROADCAST_GROUP = 'devices_broadcast'


def get_device_stats_payload():
    from .models import Device

    today = date.today()
    total = Device.objects.count()
    active = Device.objects.filter(status='active').count()
    maintenance = Device.objects.filter(status='maintenance').count()
    inactive = Device.objects.filter(status='inactive').count()
    critical = Device.objects.filter(next_maintenance__isnull=False).filter(
        Q(next_maintenance__lt=today) |
        Q(next_maintenance__lte=today + timedelta(days=3))
    ).count()
    health = round((active / total) * 100, 1) if total else 0
    return {
        'total_devices': total,
        'active_devices': active,
        'maintenance_devices': maintenance,
        'inactive_devices': inactive,
        'critical_alerts': critical,
        'system_health': health,
        'timestamp': timezone.now().isoformat(),
    }


def get_dashboard_stats_response():
    from .models import Maintenance

    stats = get_device_stats_payload()
    recent_qs = Maintenance.objects.select_related('device').order_by('-date')[:5]
    recent_list = []
    for maintenance in recent_qs:
        recent_list.append({
            'device_name': maintenance.device.name if maintenance.device else '',
            'device_id': maintenance.device.device_id if maintenance.device else '',
            'technician': maintenance.technician or 'Technician',
            'maintenance_type': maintenance.get_maintenance_type_display(),
            'cost': float(maintenance.cost or 0),
            'date': maintenance.date.strftime('%b %d, %Y') if maintenance.date else '',
        })
    return {
        'counts': {
            'total_devices': stats['total_devices'],
            'active_devices': stats['active_devices'],
            'maintenance_devices': stats['maintenance_devices'],
            'inactive_devices': stats['inactive_devices'],
            'critical_alerts': stats['critical_alerts'],
        },
        'system_health': stats['system_health'],
        'recent_maintenance': recent_list,
        'server_time': timezone.now().strftime('%H:%M:%S'),
    }


def broadcast_device_status_change(maintenance):
    if find_spec('channels') is None:
        return

    from channels.layers import get_channel_layer

    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    async_to_sync(channel_layer.group_send)(
        DEVICES_BROADCAST_GROUP,
        {
            'type': 'device_changed',
            'device_id': maintenance.device.device_id,
            'device_name': maintenance.device.name,
            'new_status': maintenance.device.status,
            'maintenance_status': maintenance.status,
        }
    )
    async_to_sync(channel_layer.group_send)(
        DEVICES_BROADCAST_GROUP,
        {'type': 'stats_update', **get_device_stats_payload()}
    )
