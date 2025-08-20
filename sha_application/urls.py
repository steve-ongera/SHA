# admin_urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('login/', views.admin_login, name='admin_login'),
    path('logout/', views.admin_logout, name='admin_logout'),
    
    # Dashboard
    path('', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    
    # Members Management
    path('members/', views.members_list, name='members_list'),
    path('members/<int:member_id>/', views.member_detail, name='member_detail'),
    path('members/<int:member_id>/approve/', views.approve_member, name='approve_member'),
    
    # Hospitals Management
    path('hospitals/', views.hospitals_list, name='hospitals_list'),
    path('hospitals/<int:hospital_id>/', views.hospital_detail, name='hospital_detail'),
    
    # Claims Management
    path('claims/', views.claims_list, name='claims_list'),
    path('claims/<int:claim_id>/', views.claim_detail, name='claim_detail'),
    
    # Reports and Analytics
    path('reports/', views.reports_dashboard, name='reports_dashboard'),
    path('reports/financial/', views.financial_reports, name='financial_reports'),
    
    # System Management
    path('system/settings/', views.system_settings, name='system_settings'),
    path('system/audit-logs/', views.audit_logs, name='audit_logs'),
    
    # API Endpoints
    path('api/dashboard-stats/', views.dashboard_stats_api, name='dashboard_stats_api'),
]