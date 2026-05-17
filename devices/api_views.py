from datetime import date, timedelta
from django.db.models import Q, Count
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.urls import reverse
from rest_framework.views import APIView
from .models import Device, Department, Maintenance, TechnicianNote, PMTemplate, MaintenanceTask
from .realtime import get_dashboard_stats_response, get_device_stats_payload
from .serializers import (
    DeviceListSerializer, DeviceDetailSerializer,
    DepartmentSerializer, MaintenanceSerializer,
    PMTemplateSerializer, MaintenanceTaskSerializer,
    TechnicianNoteSerializer, DashboardStatsSerializer,
)


class DeviceViewSet(viewsets.ModelViewSet):
    queryset = Device.objects.select_related('department').order_by('-created_at')
    filterset_fields = ['status', 'device_type', 'department']
    search_fields = ['name', 'device_id', 'serial_number', 'manufacturer']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return DeviceDetailSerializer
        return DeviceListSerializer

    @action(detail=False, methods=['get'])
    def overdue(self, request):
        today = timezone.now().date()
        qs = self.get_queryset().filter(
            next_maintenance__isnull=False,
            next_maintenance__lt=today
        )
        serializer = DeviceListSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def due_soon(self, request):
        today = timezone.now().date()
        soon = today + timedelta(days=7)
        qs = self.get_queryset().filter(
            next_maintenance__gte=today,
            next_maintenance__lte=soon
        )
        serializer = DeviceListSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def maintenance_history(self, request, pk=None):
        device = self.get_object()
        maintenances = device.maintenances.order_by('-date')
        serializer = MaintenanceSerializer(maintenances, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def generate_qr(self, request, pk=None):
        device = self.get_object()
        try:
            device.generate_qr_code()
            device.save()
            return Response({'status': 'QR code generated', 'device_id': device.device_id})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.annotate(device_count=Count('device')).order_by('name')
    serializer_class = DepartmentSerializer

    @action(detail=True, methods=['get'])
    def devices(self, request, pk=None):
        department = self.get_object()
        devices = Device.objects.filter(department=department).order_by('-created_at')
        serializer = DeviceListSerializer(devices, many=True, context={'request': request})
        return Response(serializer.data)


class MaintenanceViewSet(viewsets.ModelViewSet):
    queryset = Maintenance.objects.select_related('device').order_by('-date')
    serializer_class = MaintenanceSerializer
    filterset_fields = ['status', 'maintenance_type', 'device', 'completed']

    @action(detail=False, methods=['get'])
    def open_work_orders(self, request):
        qs = self.get_queryset().exclude(status__in=['completed', 'verified'])
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class TechnicianNoteViewSet(viewsets.ModelViewSet):
    queryset = TechnicianNote.objects.select_related('maintenance__device').order_by('-created_at')
    serializer_class = TechnicianNoteSerializer
    filterset_fields = ['maintenance', 'is_offline_created']
    search_fields = ['body', 'maintenance__device__name', 'maintenance__device__device_id']


class PMTemplateViewSet(viewsets.ModelViewSet):
    queryset = PMTemplate.objects.filter(is_active=True).order_by('device_type', 'name')
    serializer_class = PMTemplateSerializer
    filterset_fields = ['device_type', 'is_active']


class MaintenanceTaskViewSet(viewsets.ModelViewSet):
    queryset = MaintenanceTask.objects.select_related('device', 'template').order_by('due_date')
    serializer_class = MaintenanceTaskSerializer
    filterset_fields = ['status', 'urgency', 'device']

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        task = self.get_object()
        task.status = 'completed'
        task.completed_at = timezone.now()
        task.save(update_fields=['status', 'completed_at', 'updated_at'])
        return Response(self.get_serializer(task).data)


class ControlCenterStatsAPIView(APIView):
    def get(self, request):
        return Response(get_dashboard_stats_response())


class DeviceLookupAPIView(APIView):
    def get(self, request):
        device_id = (request.query_params.get('device_id') or '').strip()
        if not device_id:
            return Response({'ok': False, 'error': 'device_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        device = Device.objects.filter(device_id__iexact=device_id).first()
        if not device:
            return Response({'ok': False, 'error': 'Device not found'}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            'ok': True,
            'pk': device.pk,
            'url': reverse('device_detail', kwargs={'pk': device.pk}),
        })


class DashboardStatsAPIView(APIView):
    def get(self, request):
        stats = get_device_stats_payload()
        data = {
            'total_devices': stats['total_devices'],
            'active_devices': stats['active_devices'],
            'maintenance_devices': stats['maintenance_devices'],
            'inactive_devices': stats['inactive_devices'],
            'critical_alerts': stats['critical_alerts'],
            'system_health': stats['system_health'],
            'overdue_count': Device.objects.filter(
                next_maintenance__isnull=False,
                next_maintenance__lt=date.today(),
            ).count(),
        }
        return Response(DashboardStatsSerializer(data).data)
