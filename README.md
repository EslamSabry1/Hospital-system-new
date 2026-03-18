# DeviceCare — Intelligent Hospital Equipment Management

> **Graduation Project · Biomedical Engineering · Class of 2026**
> Higher Technological Institute — Biomedical Engineering Department

[![CI](https://github.com/EslamSabry1/Hospital-system-new/actions/workflows/ci.yml/badge.svg)](https://github.com/EslamSabry1/Hospital-system-new/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://python.org)
[![Django 6](https://img.shields.io/badge/django-6.0-green.svg)](https://djangoproject.com)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

---

## Overview

DeviceCare is a full-stack web platform that gives hospitals **complete visibility and control** over their biomedical equipment lifecycle — from procurement through retirement. It replaces paper-based maintenance logs and spreadsheet chaos with a live, role-aware operations cockpit.

**Key capabilities**

| Feature | Detail |
|---|---|
| Equipment inventory | Track 7 device types with full metadata, QR-code generation, and status lifecycle |
| Work-order management | Forward-only status machine (New → Assigned → In Progress → Waiting Parts → Completed → Verified) with SLA breach alerts |
| Predictive maintenance | ML-backed failure prediction scoring; PM schedule calendar with overdue/urgent urgency tiers |
| Analytics | TCO, replacement-priority scoring, department KPIs, Excel export |
| Technician workbench | QR-scan → device lookup → start/stop work timer → offline note sync |
| Procurement dashboard | Budget tracking, warranty expiry alerts, replacement recommendations |
| Multi-language | English + Arabic (RTL) via Django i18n |

---

## Quick Start (Docker — recommended)

```bash
# 1. Clone
git clone https://github.com/EslamSabry1/Hospital-system-new.git
cd Hospital-system-new

# 2. Configure environment
cp .env.example .env
# Edit .env — set SECRET_KEY, DB_PASSWORD, LOCAL_IP at minimum

# 3. Launch (PostgreSQL + Gunicorn)
docker compose up --build

# 4. Create a superuser (in a second terminal)
docker compose exec web python manage.py createsuperuser

# 5. (Optional) Seed sample data
docker compose exec web python manage.py reset_db --yes
```

Open **http://localhost:8000** — log in with the superuser you just created.

---

## Local Development (virtualenv)

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Minimal .env for dev
echo "SECRET_KEY=dev-only-key\nDEBUG=True" > .env

python manage.py migrate
python manage.py createsuperuser
python manage.py reset_db --yes   # optional: seed 5 depts + 5 devices
python manage.py runserver
```

---

## Running Tests

```bash
python manage.py test devices -v 2
```

The suite covers **44 tests** across 7 test classes:

| Class | What it tests |
|---|---|
| `MaintenanceWorkOrderTests` | Status machine, SLA breach, device auto-sync on WO open/close/delete |
| `DeviceModelTests` | Properties: age, TCO, replacement score, status color |
| `DepartmentModelTests` | String representation |
| `AuthenticationRedirectTests` | All 10 protected URLs redirect anonymous users to login |
| `AuthenticatedViewTests` | CRUD views return correct status codes; POST creates/deletes objects; Excel export MIME type |
| `APITests` | Stats API JSON shape, device lookup 200/400/404, auth enforcement |
| `PMTemplateTests` | PM task urgency/status refresh logic |

---

## Architecture

```
hospital_system/          # Django project
├── settings.py           # All config via environment variables (python-decouple)
└── urls.py

devices/                  # Main application
├── models.py             # Device, Department, Maintenance, TechnicianNote, PMTemplate, MaintenanceTask
├── views.py              # ~30 function-based views + 3 JSON API endpoints
├── forms.py              # ModelForms with Bootstrap widget attrs
├── urls.py               # URL routing
├── admin.py              # Customised admin with inline Maintenance
├── scheduling.py         # PM calendar sync logic
├── utils/
│   └── prediction.py     # compute_failure_prediction()
├── management/
│   └── commands/
│       └── reset_db.py   # Dev seed command (blocked when DEBUG=False)
└── tests.py              # 44-test suite

templates/
├── base.html             # Navbar, dark/light toggle, message toasts
├── control_center.html   # Main operations cockpit
├── devices/              # CRUD templates
└── auth/login.html

static/css/style.css      # Global design tokens + component styles
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | *(insecure dev key)* | **Required in production** |
| `DEBUG` | `True` | Set `False` in production |
| `ALLOWED_HOSTS` | `127.0.0.1,localhost` | Comma-separated host list |
| `DB_ENGINE` | `sqlite3` | Use `postgresql` for production |
| `DB_NAME` | `hospital_db` | PostgreSQL database name |
| `DB_USER` | `hospital_user` | PostgreSQL user |
| `DB_PASSWORD` | *(empty)* | **Required for PostgreSQL** |
| `DB_HOST` | `db` | PostgreSQL host |
| `LOCAL_IP` | `127.0.0.1` | Used in QR code URLs |
| `BASE_URL` | `http://{LOCAL_IP}:8000` | Base URL for QR links |

---

## Production Checklist

- [ ] `DEBUG=False` in `.env`
- [ ] `SECRET_KEY` is a long random string (50+ chars)
- [ ] `DB_ENGINE=django.db.backends.postgresql` + DB credentials set
- [ ] `ALLOWED_HOSTS` contains only your domain(s)
- [ ] Run `python manage.py collectstatic --noinput`
- [ ] Serve static/media via Nginx (not Django)
- [ ] HTTPS enabled — `SECURE_SSL_REDIRECT`, `HSTS`, and `SECURE_COOKIES` auto-enable when `DEBUG=False`
- [ ] Healthcheck passes: `curl http://your-host/healthz/`

---

## Team

| Name | Role |
|---|---|
| Yousef Mohamed Ahmed | Team Lead & Full-Stack Developer |
| Eslam Mohamed Sabry | Frontend Developer & UI Specialist |
| Hamsa Samir | AI Integration & Data Analytics |

**Supervisor:** Eng. Lamia Nabil Mahdy — Biomedical Engineering Department, HTI

---

## Tech Stack

Django 6 · PostgreSQL · Bootstrap 5 · Chart.js · Docker · Gunicorn · python-decouple · openpyxl · qrcode · Pillow

