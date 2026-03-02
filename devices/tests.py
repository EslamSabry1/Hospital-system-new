from datetime import date, timedelta

from django.test import TestCase

from .models import Department, Device, PMTemplate, MaintenanceTask
from .scheduling import schedule_device_tasks, refresh_all_task_statuses


class SchedulingEngineTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(name='ICU', floor=1)
        self.device = Device.objects.create(
            name='Patient Monitor',
            device_id='MON-900',
            serial_number='SER-900',
            device_type='monitor',
            manufacturer='Philips',
            model='MX450',
            purchase_date=date.today() - timedelta(days=500),
            warranty_expiry=date.today() + timedelta(days=500),
            price=1000,
            status='active',
            department=self.department,
            location='ICU',
            next_maintenance=date.today() + timedelta(days=5),
        )

    def test_template_matching_and_task_generation(self):
        PMTemplate.objects.create(
            name='Generic Monitor PM',
            device_type='monitor',
            interval_days=30,
            reminder_days_before=5,
        )
        PMTemplate.objects.create(
            name='Philips MX450 PM',
            device_type='monitor',
            manufacturer='Philips',
            model='MX450',
            interval_days=30,
            reminder_days_before=10,
        )

        created = schedule_device_tasks(self.device, horizon_days=65, reference_date=date.today())
        self.assertEqual(len(created), 3)
        self.assertTrue(MaintenanceTask.objects.filter(template__name='Philips MX450 PM').exists())

    def test_urgency_refresh(self):
        template = PMTemplate.objects.create(
            name='Ventilator PM',
            device_type='monitor',
            interval_days=90,
            reminder_days_before=7,
        )
        task = MaintenanceTask.objects.create(
            device=self.device,
            template=template,
            due_date=date.today() - timedelta(days=1),
            reminder_date=date.today() - timedelta(days=8),
        )

        refresh_all_task_statuses(reference_date=date.today())
        task.refresh_from_db()
        self.assertEqual(task.status, 'overdue')
        self.assertEqual(task.urgency, 'overdue')
