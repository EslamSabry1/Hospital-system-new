from rest_framework import serializers
from .models import Device, Department, Maintenance, TechnicianNote, PMTemplate, MaintenanceTask


class DepartmentSerializer(serializers.ModelSerializer):
    device_count = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = ['id', 'name', 'floor', 'phone', 'device_count']

    def get_device_count(self, obj):
        return obj.device_set.count()


class DeviceListSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    device_type_display = serializers.CharField(source='get_device_type_display', read_only=True)
    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = Device
        fields = [
            'id', 'name', 'device_id', 'serial_number',
            'device_type', 'device_type_display',
            'manufacturer', 'model', 'status', 'status_display',
            'department', 'department_name', 'location',
            'last_maintenance', 'next_maintenance',
            'is_overdue', 'created_at',
        ]

    def get_is_overdue(self, obj):
        from django.utils import timezone
        if obj.next_maintenance:
            return obj.next_maintenance < timezone.now().date()
        return False


class DeviceDetailSerializer(DeviceListSerializer):
    total_cost_of_ownership = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    replacement_recommendation_score = serializers.IntegerField(read_only=True)
    replacement_priority_label = serializers.CharField(read_only=True)
    age_in_years = serializers.FloatField(read_only=True)

    class Meta(DeviceListSerializer.Meta):
        fields = DeviceListSerializer.Meta.fields + [
            'purchase_date', 'warranty_expiry', 'price',
            'notes', 'total_cost_of_ownership',
            'replacement_recommendation_score', 'replacement_priority_label',
            'age_in_years', 'updated_at',
        ]


class MaintenanceSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source='device.name', read_only=True)
    maintenance_type_display = serializers.CharField(
        source='get_maintenance_type_display', read_only=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_sla_breached = serializers.BooleanField(read_only=True)

    class Meta:
        model = Maintenance
        fields = [
            'id', 'device', 'device_name',
            'maintenance_type', 'maintenance_type_display',
            'date', 'technician', 'assigned_technician',
            'cost', 'description', 'notes',
            'status', 'status_display',
            'sla_deadline', 'is_sla_breached',
            'completed', 'next_maintenance_date',
            'started_at', 'stopped_at',
            'technician_signature', 'created_at',
        ]
        read_only_fields = ['created_at', 'is_sla_breached']


class TechnicianNoteSerializer(serializers.ModelSerializer):
    maintenance_device_name = serializers.CharField(source='maintenance.device.name', read_only=True)

    class Meta:
        model = TechnicianNote
        fields = [
            'id', 'maintenance', 'maintenance_device_name', 'body',
            'is_offline_created', 'synced_at', 'created_at',
        ]
        read_only_fields = ['created_at']


class PMTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PMTemplate
        fields = '__all__'


class MaintenanceTaskSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source='device.name', read_only=True)
    template_name = serializers.CharField(source='template.name', read_only=True)

    class Meta:
        model = MaintenanceTask
        fields = [
            'id', 'device', 'device_name', 'template', 'template_name',
            'due_date', 'reminder_date', 'status', 'urgency',
            'completed_at', 'notes', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class DashboardStatsSerializer(serializers.Serializer):
    total_devices = serializers.IntegerField()
    active_devices = serializers.IntegerField()
    maintenance_devices = serializers.IntegerField()
    inactive_devices = serializers.IntegerField()
    critical_alerts = serializers.IntegerField()
    system_health = serializers.FloatField()
    overdue_count = serializers.IntegerField()
