# devices/models.py
from datetime import timedelta

from django.db import models
import qrcode
from io import BytesIO
from django.core.files import File
from django.utils import timezone
from django.urls import reverse
from django.conf import settings

class Department(models.Model):
    name = models.CharField(max_length=200, verbose_name='Department Name')
    floor = models.IntegerField(verbose_name='Floor')
    phone = models.CharField(max_length=15, blank=True, verbose_name='Phone Number')
    
    class Meta:
        verbose_name = 'Department'
        verbose_name_plural = 'Departments'
    
    def __str__(self):
        return f"{self.name} - Floor {self.floor}"

class Device(models.Model):
    DEVICE_STATUS = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('maintenance', 'Under Maintenance'),
        ('retired', 'Retired'),
    ]
    
    DEVICE_TYPE = [
        ('monitor', 'Monitor'),
        ('infusion_pump', 'Infusion Pump'),
        ('ventilator', 'Ventilator'),
        ('defibrillator', 'Defibrillator'),
        ('ultrasound', 'Ultrasound'),
        ('xray', 'X-Ray'),
        ('other', 'Other'),
    ]
    
    name = models.CharField(max_length=200, verbose_name='Device Name')
    device_id = models.CharField(max_length=50, unique=True, verbose_name='Device ID')
    serial_number = models.CharField(max_length=100, unique=True, verbose_name='Serial Number')
    device_type = models.CharField(max_length=50, choices=DEVICE_TYPE, verbose_name='Device Type')
    manufacturer = models.CharField(max_length=200, verbose_name='Manufacturer')
    model = models.CharField(max_length=200, verbose_name='Model')
    purchase_date = models.DateField(verbose_name='Purchase Date')
    warranty_expiry = models.DateField(verbose_name='Warranty Expiry')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Price')
    status = models.CharField(max_length=20, choices=DEVICE_STATUS, default='active', verbose_name='Status')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Department')
    location = models.CharField(max_length=200, verbose_name='Location')
    last_maintenance = models.DateField(null=True, blank=True, verbose_name='Last Maintenance')
    next_maintenance = models.DateField(null=True, blank=True, verbose_name='Next Maintenance')
    notes = models.TextField(blank=True, verbose_name='Notes')
    qr_code = models.ImageField(blank=True, upload_to='qrcodes/', verbose_name='QR Code')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    
    class Meta:
        verbose_name = 'Device'
        verbose_name_plural = 'Devices'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.device_id})"
    
    def get_absolute_url(self):
        return reverse('device_detail', kwargs={'pk': self.pk})
    
    def get_status_color(self):
        colors = {
            'active': 'success',
            'inactive': 'secondary',
            'maintenance': 'warning',
            'retired': 'danger'
        }
        return colors.get(self.status, 'secondary')
    
    def generate_qr_code(self):
        device_url = settings.BASE_URL + self.get_absolute_url()
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(device_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        filename = f'qr_{self.device_id}_{self.id}.png'
        self.qr_code.save(filename, File(buffer), save=False)
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if not self.qr_code:
            self.generate_qr_code()
            super().save(update_fields=['qr_code'])

class Maintenance(models.Model):
    MAINTENANCE_TYPE = [
        ('preventive', 'Preventive Maintenance'),
        ('corrective', 'Corrective Maintenance'),
        ('emergency', 'Emergency Maintenance'),
        ('calibration', 'Calibration'),
    ]
    
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='maintenances', verbose_name='Device')
    maintenance_type = models.CharField(max_length=20, choices=MAINTENANCE_TYPE, verbose_name='Maintenance Type')
    date = models.DateField(default=timezone.now, verbose_name='Maintenance Date')
    technician = models.CharField(max_length=200, verbose_name='Technician')
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Cost')
    description = models.TextField(verbose_name='Work Description')
    notes = models.TextField(blank=True, verbose_name='Notes')
    completed = models.BooleanField(default=True, verbose_name='Completed')
    next_maintenance_date = models.DateField(blank=True, null=True, verbose_name='Next Maintenance Date')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Maintenance'
        verbose_name_plural = 'Maintenance Records'
        ordering = ['-date']
    
    def __str__(self):
        return f"Maintenance {self.device.name} - {self.date}"


class PMTemplate(models.Model):
    """Recurring preventive-maintenance template matched by device attributes."""

    MAINTENANCE_TYPE = Maintenance.MAINTENANCE_TYPE

    name = models.CharField(max_length=200)
    maintenance_type = models.CharField(max_length=20, choices=MAINTENANCE_TYPE, default='preventive')
    device_type = models.CharField(max_length=50, choices=Device.DEVICE_TYPE)
    manufacturer = models.CharField(max_length=200, blank=True)
    model = models.CharField(max_length=200, blank=True)
    interval_days = models.PositiveIntegerField(default=90)
    reminder_days_before = models.PositiveIntegerField(default=7)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['device_type', 'manufacturer', 'model', 'name']

    def __str__(self):
        target = f"{self.get_device_type_display()}"
        if self.manufacturer:
            target += f" / {self.manufacturer}"
        if self.model:
            target += f" / {self.model}"
        return f"{self.name} ({target})"


class MaintenanceTask(models.Model):
    """Auto-generated PM task from template/device pair."""

    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('due', 'Due Now'),
        ('overdue', 'Overdue'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    URGENCY_CHOICES = [
        ('normal', 'Normal'),
        ('soon', 'Due Soon'),
        ('urgent', 'Urgent'),
        ('overdue', 'Overdue'),
    ]

    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='maintenance_tasks')
    template = models.ForeignKey(PMTemplate, on_delete=models.CASCADE, related_name='maintenance_tasks')
    due_date = models.DateField()
    reminder_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    urgency = models.CharField(max_length=20, choices=URGENCY_CHOICES, default='normal')
    source_maintenance = models.ForeignKey(Maintenance, on_delete=models.SET_NULL, null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['due_date', 'urgency']
        unique_together = ('device', 'template', 'due_date')

    def __str__(self):
        return f"{self.device.device_id} / {self.template.name} / {self.due_date}"

    def refresh_status(self, reference_date=None):
        if self.status in {'completed', 'cancelled'}:
            return

        reference_date = reference_date or timezone.now().date()
        days = (self.due_date - reference_date).days

        if days < 0:
            self.status = 'overdue'
            self.urgency = 'overdue'
        elif days <= 3:
            self.status = 'due'
            self.urgency = 'urgent'
        elif days <= 7:
            self.status = 'scheduled'
            self.urgency = 'soon'
        else:
            self.status = 'scheduled'
            self.urgency = 'normal'

    @property
    def next_due_date(self):
        return self.due_date + timedelta(days=self.template.interval_days)
