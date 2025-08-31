from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('reports/', views.admin_reports, name='admin_reports'),
    path('case-assignment/', views.admin_case_assignment, name='admin_case_assignment'),
    path('analytics/', views.admin_analytics, name='admin_analytics'),
    path('awareness/', views.admin_awareness, name='admin_awareness'),
    path('users/', views.admin_user_management, name='admin_user_management'),
    ]