"""
DeviceCare — comprehensive test suite
Covers: models, view auth, view responses, API shape, filtering, exports
Run: python manage.py test devices -v 2
"""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Department, Device, Maintenance, TechnicianNote, PMTemplate, MaintenanceTask

User = get_user_model()


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def make_department(**kwargs):
    defaults = dict(name='ICU', floor=1, phone='0000')
    defaults.update(kwargs)
    return Department.objects.create(**defaults)


def make_device(department=None, **kwargs):
    today = timezone.now().date()
    defaults = dict(
        name='Test Monitor',
        device_id='MON-TEST-001',
        serial_number='SER-TEST-001',
        device_type='monitor',
        manufacturer='Acme',
        model='A1',
        purchase_date=today - timedelta(days=365),
        warranty_expiry=today + timedelta(days=365),
        price='10000.00',
        status='active',
        department=department or make_department(),
        location='Room 1',
    )
    defaults.update(kwargs)
    return Device.objects.create(**defaults)


def make_maintenance(device, **kwargs):
    defaults = dict(
        maintenance_type='corrective',
        technician='Tech A',
        assigned_technician='Tech B',
        description='Routine fix',
        status='in_progress',
    )
    defaults.update(kwargs)
    return Maintenance.objects.create(device=device, **defaults)


# ─────────────────────────────────────────────────────────────
# 1. Model tests — Maintenance work-order state machine
# ─────────────────────────────────────────────────────────────

class MaintenanceWorkOrderTests(TestCase):
    def setUp(self):
        self.department = make_department()
        self.device = make_device(
            department=self.department,
            device_id='MON-100',
            serial_number='SER-100',
            purchase_date=timezone.now().date() - timedelta(days=3650),
            warranty_expiry=timezone.now().date() - timedelta(days=1),
            price='1000.00',
            status='maintenance',
        )

    def test_completed_flag_tracks_status(self):
        m = make_maintenance(self.device, status='in_progress')
        self.assertFalse(m.completed)
        m.status = 'completed'
        m.save()
        self.assertTrue(m.completed)

    def test_status_cannot_move_backwards(self):
        m = make_maintenance(self.device, status='in_progress')
        m.status = 'assigned'
        with self.assertRaises(ValidationError):
            m.save()

    def test_sla_breach_indicator_open(self):
        m = make_maintenance(
            self.device,
            status='assigned',
            sla_deadline=timezone.now() - timedelta(hours=2),
        )
        self.assertTrue(m.is_sla_breached)

    def test_sla_breach_clears_on_verify(self):
        m = make_maintenance(
            self.device,
            status='assigned',
            sla_deadline=timezone.now() - timedelta(hours=2),
        )
        m.status = 'verified'
        m.save()
        self.assertFalse(m.is_sla_breached)

    def test_device_becomes_inactive_when_work_order_opened(self):
        self.device.status = 'active'
        self.device.save(update_fields=['status'])
        make_maintenance(self.device, status='new')
        self.device.refresh_from_db()
        self.assertEqual(self.device.status, 'inactive')

    def test_device_becomes_active_when_all_work_orders_closed(self):
        m = make_maintenance(self.device, status='in_progress')
        m.status = 'verified'
        m.save()
        self.device.refresh_from_db()
        self.assertEqual(self.device.status, 'active')

    def test_tco_and_replacement_score(self):
        make_maintenance(self.device, status='completed', cost='700.00')
        self.assertEqual(self.device.total_maintenance_cost, Decimal('700'))
        self.assertEqual(self.device.total_cost_of_ownership, Decimal('1700.00'))
        self.assertGreaterEqual(self.device.replacement_recommendation_score, 70)
        self.assertEqual(self.device.replacement_priority_label, 'High')

    def test_technician_note_sync_fields(self):
        m = make_maintenance(self.device, status='in_progress')
        note = TechnicianNote.objects.create(
            maintenance=m,
            body='Offline note',
            is_offline_created=True,
            synced_at=timezone.now(),
        )
        self.assertTrue(note.is_offline_created)

    def test_delete_maintenance_syncs_device(self):
        """Deleting the only open WO should restore device to active."""
        self.device.status = 'active'
        self.device.save(update_fields=['status'])
        m = make_maintenance(self.device, status='new')
        self.device.refresh_from_db()
        self.assertEqual(self.device.status, 'inactive')
        m.delete()
        self.device.refresh_from_db()
        self.assertEqual(self.device.status, 'active')


# ─────────────────────────────────────────────────────────────
# 2. Model tests — Device properties
# ─────────────────────────────────────────────────────────────

class DeviceModelTests(TestCase):
    def setUp(self):
        self.device = make_device()

    def test_str_representation(self):
        self.assertIn(self.device.device_id, str(self.device))

    def test_get_status_color_active(self):
        self.assertEqual(self.device.get_status_color(), 'success')

    def test_get_status_color_retired(self):
        self.device.status = 'retired'
        self.assertEqual(self.device.get_status_color(), 'danger')

    def test_age_in_years(self):
        self.assertAlmostEqual(self.device.age_in_years, 1.0, delta=0.1)

    def test_replacement_score_low_for_new_device(self):
        """Brand-new, in-warranty, no maintenance → low replacement score."""
        score = self.device.replacement_recommendation_score
        self.assertLess(score, 40)
        self.assertEqual(self.device.replacement_priority_label, 'Low')

    def test_total_maintenance_cost_zero_with_no_records(self):
        self.assertEqual(self.device.total_maintenance_cost, Decimal('0'))

    def test_total_cost_of_ownership_equals_price_when_no_maintenance(self):
        self.assertEqual(self.device.total_cost_of_ownership, Decimal('10000.00'))


# ─────────────────────────────────────────────────────────────
# 3. Model tests — Department
# ─────────────────────────────────────────────────────────────

class DepartmentModelTests(TestCase):
    def test_str_includes_name_and_floor(self):
        dept = Department.objects.create(name='Radiology', floor=2)
        self.assertIn('Radiology', str(dept))
        self.assertIn('2', str(dept))


# ─────────────────────────────────────────────────────────────
# 4. View tests — Authentication (all protected views redirect)
# ─────────────────────────────────────────────────────────────

class AuthenticationRedirectTests(TestCase):
    """Anonymous requests to protected views must redirect to login."""

    PROTECTED_URLS = [
        '/',
        '/devices/',
        '/devices/add/',
        '/departments/',
        '/departments/add/',
        '/reports/',
        '/procurement/',
        '/technician/',
        '/control-center/api/stats/',
        '/devices/api/lookup/',
    ]

    def test_anonymous_redirected_to_login(self):
        client = Client()
        for url in self.PROTECTED_URLS:
            with self.subTest(url=url):
                response = client.get(url)
                self.assertIn(
                    response.status_code, [302, 301],
                    msg=f'{url} should redirect anonymous users'
                )
                self.assertIn('/login', response['Location'])


# ─────────────────────────────────────────────────────────────
# 5. View tests — Authenticated CRUD
# ─────────────────────────────────────────────────────────────

class AuthenticatedViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        self.department = make_department(name='ICU', phone='1234')
        self.device = make_device(
            department=self.department,
            device_id='MON-VIEW-001',
            serial_number='SER-VIEW-001',
        )

    def test_device_list_returns_200(self):
        r = self.client.get(reverse('device_list'))
        self.assertEqual(r.status_code, 200)

    def test_device_list_contains_device_name(self):
        r = self.client.get(reverse('device_list'))
        self.assertContains(r, self.device.name)

    def test_device_list_status_filter(self):
        make_device(
            device_id='RET-001', serial_number='SER-RET-001',
            status='retired', department=self.department,
        )
        r = self.client.get(reverse('device_list') + '?status=retired')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'RET-001')
        self.assertNotContains(r, 'MON-VIEW-001')

    def test_device_list_search(self):
        r = self.client.get(reverse('device_list') + '?search=MON-VIEW-001')
        self.assertContains(r, 'MON-VIEW-001')

    def test_device_detail_returns_200(self):
        r = self.client.get(reverse('device_detail', args=[self.device.pk]))
        self.assertEqual(r.status_code, 200)

    def test_device_detail_404_for_nonexistent(self):
        r = self.client.get(reverse('device_detail', args=[999999]))
        self.assertEqual(r.status_code, 404)

    def test_device_add_get_returns_200(self):
        r = self.client.get(reverse('device_add'))
        self.assertEqual(r.status_code, 200)

    def test_device_add_post_creates_device(self):
        today = timezone.now().date()
        payload = {
            'name': 'New Ventilator',
            'device_id': 'VEN-NEW-001',
            'serial_number': 'SN-VEN-NEW-001',
            'device_type': 'ventilator',
            'manufacturer': 'Medtronic',
            'model': 'PB980',
            'purchase_date': str(today - timedelta(days=30)),
            'warranty_expiry': str(today + timedelta(days=700)),
            'price': '45000.00',
            'status': 'active',
            'department': self.department.pk,
            'location': 'ICU Bay A',
        }
        r = self.client.post(reverse('device_add'), payload)
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Device.objects.filter(device_id='VEN-NEW-001').exists())

    def test_device_edit_get_returns_200(self):
        r = self.client.get(reverse('device_edit', args=[self.device.pk]))
        self.assertEqual(r.status_code, 200)

    def test_device_delete_post_removes_device(self):
        pk = self.device.pk
        r = self.client.post(reverse('device_delete', args=[pk]))
        self.assertEqual(r.status_code, 302)
        self.assertFalse(Device.objects.filter(pk=pk).exists())

    def test_departments_list_returns_200(self):
        r = self.client.get(reverse('departments_list'))
        self.assertEqual(r.status_code, 200)

    def test_department_add_post_creates_department(self):
        r = self.client.post(reverse('department_add'), {
            'name': 'Cardiology', 'floor': '4', 'phone': '9999'
        })
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Department.objects.filter(name='Cardiology').exists())

    def test_reports_view_returns_200(self):
        r = self.client.get(reverse('reports'))
        self.assertEqual(r.status_code, 200)

    def test_healthz_returns_200_unauthenticated(self):
        """Health probe must be reachable — returns 200 (ok) or 503 (DB degraded)."""
        from django.test import override_settings
        with override_settings(ALLOWED_HOSTS=['*']):
            r = Client().get('/healthz/')
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data['status'], 'ok')

    def test_control_center_returns_200(self):
        r = self.client.get(reverse('control_center'))
        self.assertEqual(r.status_code, 200)

    def test_excel_export_returns_xlsx(self):
        r = self.client.get(reverse('devices_export_excel'))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )


# ─────────────────────────────────────────────────────────────
# 6. API tests — JSON shape & authentication
# ─────────────────────────────────────────────────────────────

class APITests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='apiuser', password='pass123')
        self.client.login(username='apiuser', password='pass123')
        dept = make_department(name='ER', phone='111')
        self.device = make_device(
            department=dept,
            device_id='API-001',
            serial_number='SER-API-001',
        )

    def test_stats_api_returns_correct_shape(self):
        r = self.client.get(reverse('control_center_stats_api'))
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn('counts', data)
        self.assertIn('system_health', data)
        self.assertIn('recent_maintenance', data)
        self.assertIn('total_devices', data['counts'])
        self.assertIn('active_devices', data['counts'])

    def test_stats_api_counts_reflect_db(self):
        r = self.client.get(reverse('control_center_stats_api'))
        data = r.json()
        self.assertEqual(data['counts']['total_devices'], Device.objects.count())

    def test_device_lookup_api_found(self):
        r = self.client.get(
            reverse('device_lookup_api') + f'?device_id={self.device.device_id}'
        )
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['pk'], self.device.pk)

    def test_device_lookup_api_not_found(self):
        r = self.client.get(reverse('device_lookup_api') + '?device_id=DOES-NOT-EXIST')
        self.assertEqual(r.status_code, 404)
        self.assertFalse(r.json()['ok'])

    def test_device_lookup_api_missing_param(self):
        r = self.client.get(reverse('device_lookup_api'))
        self.assertEqual(r.status_code, 400)

    def test_stats_api_requires_auth(self):
        r = Client().get(reverse('control_center_stats_api'))
        self.assertEqual(r.status_code, 302)


# ─────────────────────────────────────────────────────────────
# 7. PMTemplate & MaintenanceTask scheduling
# ─────────────────────────────────────────────────────────────

class PMTemplateTests(TestCase):
    def setUp(self):
        self.device = make_device()
        self.template = PMTemplate.objects.create(
            name='90-day PM',
            device_type='monitor',
            interval_days=90,
            reminder_days_before=7,
        )

    def test_template_str(self):
        self.assertIn('90-day PM', str(self.template))

    def test_task_refresh_status_overdue(self):
        task = MaintenanceTask(
            device=self.device,
            template=self.template,
            due_date=timezone.now().date() - timedelta(days=5),
            reminder_date=timezone.now().date() - timedelta(days=12),
        )
        task.refresh_status()
        self.assertEqual(task.status, 'overdue')
        self.assertEqual(task.urgency, 'overdue')

    def test_task_refresh_status_due_today(self):
        task = MaintenanceTask(
            device=self.device,
            template=self.template,
            due_date=timezone.now().date(),
            reminder_date=timezone.now().date() - timedelta(days=7),
        )
        task.refresh_status()
        self.assertEqual(task.status, 'due')
        self.assertEqual(task.urgency, 'urgent')

    def test_task_refresh_status_scheduled(self):
        task = MaintenanceTask(
            device=self.device,
            template=self.template,
            due_date=timezone.now().date() + timedelta(days=30),
            reminder_date=timezone.now().date() + timedelta(days=23),
        )
        task.refresh_status()
        self.assertEqual(task.status, 'scheduled')
        self.assertEqual(task.urgency, 'normal')
