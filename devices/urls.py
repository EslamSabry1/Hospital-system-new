from importlib.util import find_spec

from django.contrib.auth.decorators import login_required
from django.urls import path
from . import views


def optional_app_available(app):
    try:
        return find_spec(app) is not None
    except ModuleNotFoundError:
        return False


api_views = None
if optional_app_available('rest_framework'):
    from . import api_views

urlpatterns = [
    path('htmx/cockpit/needs-action/', views.htmx_cockpit_needs_action, name='htmx_cockpit_needs_action'),
    path('htmx/cockpit/todays-work/', views.htmx_cockpit_todays_work, name='htmx_cockpit_todays_work'),
    path('htmx/cockpit/trends/', views.htmx_cockpit_trends, name='htmx_cockpit_trends'),
    path('htmx/stats-strip/', views.htmx_stats_strip, name='htmx_stats_strip'),
    path('htmx/todays-maintenance/', views.htmx_todays_maintenance, name='htmx_todays_maintenance'),
    path('htmx/critical-zone/', views.htmx_critical_zone, name='htmx_critical_zone'),
    path('healthz/', views.healthz, name='healthz'),
    path('service-worker.js', views.service_worker, name='service_worker'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.control_center, name='control_center'),
    path('control-center/', views.control_center, name='control_center_dash'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('team-profile/', views.team_profile, name='team_profile'),
    path('devices/', views.device_list, name='device_list'),
    path('devices/add/', views.device_add, name='device_add'),
    path('devices/<int:pk>/', views.device_detail, name='device_detail'),
    path('devices/<int:pk>/edit/', views.device_edit, name='device_edit'),
    path('devices/<int:pk>/delete/', views.device_delete, name='device_delete'),
    path('devices/<int:pk>/generate-qr/', views.generate_device_qr, name='generate_device_qr'),
    path('departments/', views.departments_list, name='departments_list'),
    path('departments/add/', views.department_add, name='department_add'),
    path('departments/<int:pk>/edit/', views.department_edit, name='department_edit'),
    path('departments/<int:pk>/delete/', views.department_delete, name='department_delete'),
    path('procurement/', views.procurement_dashboard, name='procurement_dashboard'),
    path('technician/', views.technician_workbench, name='technician_workbench'),
    path('technician/scan/', views.technician_device_from_qr, name='technician_device_from_qr'),
    path('technician/device/<int:pk>/', views.technician_device, name='technician_device'),
    path('technician/device/<int:pk>/start-work-order/', views.technician_start_work_order, name='technician_start_work_order'),
    path('technician/work-order/<int:maintenance_id>/stop/', views.technician_stop_work_order, name='technician_stop_work_order'),
    path('technician/work-order/<int:maintenance_id>/sync-notes/', views.technician_sync_notes, name='technician_sync_notes'),
    path('reports/', views.reports_view, name='reports'),
    path('devices/export/excel/', views.devices_export_excel, name='devices_export_excel'),
    path('control-center/api/stats/', views.control_center_stats_api, name='control_center_stats_api'),
    path('devices/api/lookup/', views.device_lookup_api, name='device_lookup_api'),
    path('maintenance/api/calendar/', views.maintenance_calendar_api, name='maintenance_calendar_api'),
    path('devices/<int:pk>/qr.png', views.device_qr, name='device_qr'),
]

if api_views is not None:
    from django.urls import include
    from rest_framework.routers import DefaultRouter
    router = DefaultRouter()
    router.register(r'devices', api_views.DeviceViewSet, basename='api-device')
    router.register(r'departments', api_views.DepartmentViewSet, basename='api-department')
    router.register(r'maintenance', api_views.MaintenanceViewSet, basename='api-maintenance')
    router.register(r'technician-notes', api_views.TechnicianNoteViewSet, basename='api-technician-note')
    router.register(r'pm-templates', api_views.PMTemplateViewSet, basename='api-pmtemplate')
    router.register(r'tasks', api_views.MaintenanceTaskViewSet, basename='api-task')

    urlpatterns = [
        path('control-center/api/stats/', login_required(api_views.ControlCenterStatsAPIView.as_view()), name='control_center_stats_api'),
        path('devices/api/lookup/', login_required(api_views.DeviceLookupAPIView.as_view()), name='device_lookup_api'),
        path('api/v1/', include(router.urls)),
        path('api/v1/stats/', api_views.DashboardStatsAPIView.as_view(), name='api-stats'),
    ] + urlpatterns
