from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='counselor_dashboard'),
    path('analytics/', views.analytics_dashboard, name='counselor_analytics'),
    path('cases/<int:report_id>/', views.case_detail, name='counselor_case_detail'),
    path('cases/<int:report_id>/claim/', views.claim_case, name='counselor_claim_case'),
    path('messages/', views.messages_view, name='counselor_messages'),
]