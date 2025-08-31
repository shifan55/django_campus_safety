from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register, name='register'),
    path('report-anonymous/', views.report_anonymous, name='report_anonymous'),
    path('submit-report/', views.submit_report, name='submit_report'),
    path('report-success/<int:report_id>/', views.report_success, name='report_success'),
    path('awareness/', views.awareness, name='awareness'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
]