from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='counselor_dashboard'),
    path('cases/<int:report_id>/', views.case_detail, name='counselor_case_detail'),
    path('messages/', views.messages_view, name='counselor_messages'),
]