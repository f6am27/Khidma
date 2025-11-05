# admin_api/urls.py
from django.urls import path
from . import views
from rest_framework_simplejwt.views import TokenRefreshView
from .upload_views import (  # ✅ أضف هذا السطر
    upload_admin_profile_image,
    delete_admin_profile_image,
    get_admin_profile_image
)
app_name = 'admin_api'

urlpatterns = [
    # Authentication
    path('login/', views.AdminLoginView.as_view(), name='admin-login'),
    path('logout/', views.admin_logout, name='admin-logout'), 
    path('heartbeat/', views.admin_heartbeat, name='admin-heartbeat'), 
    path('status/', views.admin_status, name='admin-status'),  
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),   
    
    # Dashboard
    path('dashboard/stats/', views.dashboard_stats, name='dashboard-stats'),
    
    # Users Management
    path('users/', views.AdminUserListView.as_view(), name='users-list'),
    path('users/<int:id>/', views.AdminUserDetailView.as_view(), name='user-detail'),
    path('users/<int:user_id>/suspend/', views.suspend_user, name='suspend-user'),
    path('users/<int:user_id>/unsuspend/', views.unsuspend_user, name='unsuspend-user'),
    path('users/<int:user_id>/delete/', views.delete_user, name='delete-user'),
    
    # Reports Management
    path('reports/', views.AdminReportListView.as_view(), name='reports-list'),
    path('reports/<int:report_id>/handle/', views.handle_report, name='handle-report'),
    
    # Categories Management
    path('categories/', views.AdminCategoryListView.as_view(), name='categories-list'),
    path('categories/<int:id>/', views.AdminCategoryDetailView.as_view(), name='category-detail'),
    
    # Areas Management
    path('areas/', views.AdminAreaListView.as_view(), name='areas-list'),
    path('areas/<int:id>/', views.AdminAreaDetailView.as_view(), name='area-detail'),
    
    # Financial Reports
    path('financial/summary/', views.financial_summary, name='financial-summary'),

    # Admin Profile Management
    path('profile/', views.admin_profile, name='admin-profile'),
    path('change-password/', views.admin_change_password, name='admin-change-password'),  
    path('upload-profile-image/', upload_admin_profile_image, name='upload-admin-profile-image'),
    path('delete-profile-image/', delete_admin_profile_image, name='delete-admin-profile-image'),
    path('profile-image/', get_admin_profile_image, name='get-admin-profile-image'),

    # ✅ Password Reset
    path('password-reset-request/', views.admin_password_reset_request, name='password-reset-request'),
    path('password-reset-confirm/', views.admin_password_reset_confirm, name='password-reset-confirm'),

    # ✅ Notifications
    path('notifications/', views.admin_notifications, name='admin-notifications'),
    path('notifications/unread-count/', views.admin_notifications_unread_count, name='admin-notifications-unread-count'),
    path('notifications/<int:notification_id>/read/', views.admin_mark_notification_read, name='admin-mark-notification-read'),
    path('notifications/mark-all-read/', views.admin_mark_all_read, name='admin-mark-all-read'),

]