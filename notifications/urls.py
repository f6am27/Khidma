# notifications/urls.py
from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # قائمة الإشعارات
    path('', views.NotificationListView.as_view(), name='list'),
    
    # إجراءات مجمعة (قبل المسارات الفردية)
    path('mark-all-read/', views.mark_all_notifications_as_read, name='mark_all_read'),
    path('bulk-actions/', views.bulk_notification_action, name='bulk_actions'),
    path('clear-all/', views.clear_all_notifications, name='clear_all'),
    
    # إحصائيات وإعدادات
    path('stats/', views.NotificationStatsView.as_view(), name='stats'),
    path('settings/', views.NotificationSettingsView.as_view(), name='settings'),
    path('types/', views.notification_types, name='types'),
    
    # إدارة (للإدارة) - مبسط
    path('admin/create/', views.create_notification, name='admin_create'),
    
    # إجراءات الإشعارات الفردية (في النهاية)
    path('<int:notification_id>/mark-read/', views.mark_notification_as_read, name='mark_read'),
    path('<int:notification_id>/mark-unread/', views.mark_notification_as_unread, name='mark_unread'),
    path('<int:notification_id>/delete/', views.delete_notification, name='delete'),
    
    # تفاصيل إشعار محدد (الأخير)
    path('<int:pk>/', views.NotificationDetailView.as_view(), name='detail'),
]