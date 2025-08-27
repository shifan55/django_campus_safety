
from django.contrib import admin
from django.urls import path, include
from tccweb.core import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register, name='register'),
    path('report-anonymous/', views.report_anonymous, name='report_anonymous'),
    path('submit-report/', views.submit_report, name='submit_report'),
    path('report-success/<int:report_id>/', views.report_success, name='report_success'),
    path('awareness/', views.awareness, name='awareness'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path("accounts/", include("allauth.urls")),
    path("profile/", views.profile_view, name="profile"),
    path('admin/reports/', views.admin_reports, name='admin_reports'),
    path('admin/case-assignment/', views.admin_case_assignment, name='admin_case_assignment'),
    path('admin/analytics/', views.admin_analytics, name='admin_analytics'),
    path('admin/awareness/', views.admin_awareness, name='admin_awareness'),
    path('admin/users/', views.admin_user_management, name='admin_user_management'),
]
