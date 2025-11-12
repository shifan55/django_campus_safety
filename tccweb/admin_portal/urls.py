from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('reports/', views.admin_reports, name='admin_reports'),
    path('case-assignment/', views.admin_case_assignment, name='admin_case_assignment'),
    path('analytics/', views.admin_analytics, name='admin_analytics'),
    path('awareness/', views.admin_awareness, name='admin_awareness'),
    path('resource/<int:pk>/delete/', views.delete_resource, name='delete_resource'),
    path('users/', views.admin_user_management, name='admin_user_management'),
    path('profile/', views.admin_profile, name='admin_profile'),
    path('security-logs/', views.admin_security_logs, name='admin_security_logs'),
    path('data-exports/', views.admin_data_exports, name='admin_data_exports'),
    path('impersonate/', views.admin_impersonate_user, name='admin_impersonate_user'),
    path('impersonate/stop/', views.admin_stop_impersonation, name='admin_stop_impersonation'),
]