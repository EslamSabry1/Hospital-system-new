"""
Management command: python manage.py reset_db

Seeds the database with sample data for development / demo purposes.
BLOCKED in production (DEBUG=False) to prevent accidental data loss.
"""
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


class Command(BaseCommand):
    help = 'Reset and seed the database with sample data (dev/demo only)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--yes',
            action='store_true',
            help='Skip confirmation prompt',
        )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError(
                'reset_db is disabled in production (DEBUG=False). '
                'This command would destroy all data.'
            )

        if not options['yes']:
            confirm = input(
                'This will DELETE all devices, departments, and maintenance records. '
                'Type "yes" to continue: '
            )
            if confirm.strip().lower() != 'yes':
                self.stdout.write(self.style.WARNING('Aborted.'))
                return

        from devices.models import Department, Device, Maintenance

        self.stdout.write('🔄 Deleting existing data...')
        Maintenance.objects.all().delete()
        Device.objects.all().delete()
        Department.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('✅ All data deleted'))

        self.stdout.write('🔄 Seeding sample data...')

        departments = [
            Department.objects.create(name='ICU', floor=3, phone='1234'),
            Department.objects.create(name='Emergency', floor=1, phone='5678'),
            Department.objects.create(name='Radiology', floor=2, phone='9012'),
            Department.objects.create(name='Laboratory', floor=2, phone='3456'),
            Department.objects.create(name='Outpatient Clinics', floor=1, phone='7890'),
        ]
        self.stdout.write(f'  ✅ {len(departments)} departments created')

        today = timezone.now().date()
        devices_data = [
            dict(name='Advanced Patient Monitor', device_id='MON-001', serial_number='SN-1001',
                 device_type='monitor', manufacturer='Philips', model='IntelliVue MX450',
                 status='active', price=25000, department=departments[0], location='Bed 1 - ICU',
                 purchase_date=today - timedelta(days=730), warranty_expiry=today + timedelta(days=365)),
            dict(name='Smart Infusion Pump', device_id='INF-001', serial_number='SN-2001',
                 device_type='infusion_pump', manufacturer='BD', model='Alaris GP',
                 status='active', price=8000, department=departments[1], location='Bay 3 - Emergency',
                 purchase_date=today - timedelta(days=400), warranty_expiry=today + timedelta(days=600)),
            dict(name='Portable Ventilator', device_id='VEN-001', serial_number='SN-3001',
                 device_type='ventilator', manufacturer='Medtronic', model='Puritan Bennett 980',
                 status='maintenance', price=45000, department=departments[0], location='ICU Suite A',
                 purchase_date=today - timedelta(days=1200), warranty_expiry=today - timedelta(days=100)),
            dict(name='Ultrasound Scanner', device_id='ULT-001', serial_number='SN-4001',
                 device_type='ultrasound', manufacturer='GE Healthcare', model='LOGIQ E10',
                 status='active', price=60000, department=departments[2], location='Radiology Room 1',
                 purchase_date=today - timedelta(days=500), warranty_expiry=today + timedelta(days=800)),
            dict(name='Defibrillator', device_id='DEF-001', serial_number='SN-5001',
                 device_type='defibrillator', manufacturer='Zoll', model='R Series',
                 status='active', price=15000, department=departments[1], location='Emergency Bay 1',
                 purchase_date=today - timedelta(days=900), warranty_expiry=today + timedelta(days=200)),
        ]

        created_devices = []
        for d in devices_data:
            device = Device(**d)
            device.save()
            created_devices.append(device)

        self.stdout.write(f'  ✅ {len(created_devices)} devices created')
        self.stdout.write(self.style.SUCCESS('\n🎉 Database reset complete!'))
