# reset_db.py
"""Compatibility wrapper for the Django reset_db management command.

Prefer running: python manage.py reset_db --yes
This script remains so existing workflows that call `python reset_db.py` still
reset the same database with the same seed data used by the app.
"""
import os

import django
from django.core.management import call_command

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_system.settings')
django.setup()


def reset_database():
    call_command('reset_db', yes=True)


if __name__ == '__main__':
    confirm = input("Are you sure you want to reset the database? (yes/no): ")
    if confirm.lower() in ['yes', 'y']:
        reset_database()
    else:
        print("❌ Operation cancelled")
