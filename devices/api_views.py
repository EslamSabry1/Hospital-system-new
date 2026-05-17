from datetime import date, timedelta
from django.db.models import Q, Count
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Device, Department, Maintenance, PMTemplate, MaintenanceTask
from .serializers import (
    DeviceListSerializer, DeviceDetailSerializer,
    DepartmentSerializer, MaintenanceSerializer,
    PMTemplateSerializer, MaintenanceTaskSerializer,
    DashboardStatsSerializer,
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


class DashboardStatsAPIView(APIView):
    def get(self, request):
        today = date.today()
        total = Device.objects.count()
        active = Device.objects.filter(status='active').count()
        maintenance = Device.objects.filter(status='maintenance').count()
        inactive = Device.objects.filter(status='inactive').count()
        overdue_qs = Device.objects.filter(
            next_maintenance__isnull=False,
            next_maintenance__lt=today
        )
        critical = Device.objects.filter(
            next_maintenance__isnull=False
        ).filter(
            Q(next_maintenance__lt=today) |
            Q(next_maintenance__lte=today + timedelta(days=3))
        ).count()
        health = round((active / total) * 100, 1) if total else 0
        data = {
            'total_devices': total,
            'active_devices': active,
            'maintenance_devices': maintenance,
            'inactive_devices': inactive,
            'critical_alerts': critical,
            'system_health': health,
            'overdue_count': overdue_qs.count(),
        }
        return Response(DashboardStatsSerializer(data).data)
