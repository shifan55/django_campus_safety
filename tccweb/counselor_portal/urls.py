from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='counselor_dashboard'),
    path('my-cases/', views.my_cases, name='counselor_my_cases'),
    path('analytics/', views.analytics_dashboard, name='counselor_analytics'),
    path('invitations/', views.invitations, name='counselor_invitations'),
    path('cases/<int:report_id>/', views.case_detail, name='counselor_case_detail'),
    path(
        'collaborations/<int:report_id>/',
        views.collaboration_case_detail,
        name='collaboration_case_detail'
    ),
    path('cases/<int:report_id>/claim/', views.claim_case, name='counselor_claim_case'),
    path('messages/', views.messages_view, name='counselor_messages'),
    path('profile/', views.profile, name='counselor_profile'),
]