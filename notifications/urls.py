# notifications/urls.py
from django.urls import path
from . import views
from . import device_views  # إضافة جديدة

app_name = 'notifications'

urlpatterns = [
    # ===== APIs الإشعارات الأساسية (موجودة مسبقاً) =====
    
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
    
    # ===== Firebase Push Notifications APIs (جديدة) =====
    
    # تسجيل وإدارة الأجهزة
    path('register-device/', device_views.register_device_token, name='register_device'),
    path('devices/', device_views.list_user_devices, name='list_devices'),
    path('device/<int:device_id>/', device_views.unregister_device_token, name='unregister_device'),
    path('device/<int:device_id>/settings/', device_views.update_device_settings, name='update_device_settings'),
    
    # اختبار الإشعارات
    path('test/', device_views.test_notification, name='test_notification'),
]