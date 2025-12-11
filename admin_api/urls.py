# admin_api/urls.py
from django.urls import path
from . import views
from rest_framework_simplejwt.views import TokenRefreshView
from complaints import views as complaint_views
from .upload_views import ( 
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
    path('users/<int:id>/', views.AdminUserDetailView.as_view(), name='user-detail'),
    
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
    path('notification-settings/', views.AdminNotificationSettingsView.as_view(), name='notification-settings'),
  
   # ✅ Analytics & Statistics
    path('analytics/top-rated/', views.top_rated_users, name='analytics-top-rated'),
    path('analytics/most-reported/', views.most_reported_users, name='analytics-most-reported'),
    path('analytics/subscriptions/', views.subscription_analytics, name='analytics-subscriptions'),
    path('analytics/activity/', views.platform_activity, name='analytics-activity'),
    path('analytics/top-categories/', views.top_service_categories, name='analytics-top-categories'),
    path('analytics/most-active/', views.most_active_users, name='analytics-most-active'),
    path('analytics/cancellations/', views.cancellation_analytics, name='analytics-cancellations'),
    path('analytics/user-growth/', views.user_growth_chart, name='user_growth_chart'),
    path('tasks/', views.get_all_tasks, name='get_all_tasks'),
    path('tasks/stats/', views.get_tasks_stats, name='get_tasks_stats'),
    path('categories/', views.get_all_categories, name='get_all_categories'),
    path('users/at-limit/', views.users_at_limit, name='users_at_limit'),
    path('analytics/daily-tasks/', views.daily_tasks_chart),

   # ✅ Complaints Management 
    path('complaints/', complaint_views.AdminComplaintListView.as_view(), name='admin-complaints-list'),
    path('complaints/stats/', complaint_views.admin_complaints_stats, name='admin-complaints-stats'),
    path('complaints/bulk-update/', complaint_views.admin_bulk_update_status, name='admin-complaints-bulk-update'),
    path('complaints/<int:id>/', complaint_views.AdminComplaintDetailView.as_view(), name='admin-complaint-detail'),
    path('complaints/<int:complaint_id>/delete/', complaint_views.admin_delete_complaint, name='admin-complaint-delete'),
]