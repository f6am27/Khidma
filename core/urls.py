from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
import os
from rest_framework_simplejwt.views import TokenRefreshView  # ✅ أضف هذا


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    path('api/users/', include('users.urls')),
    path('api/services/', include('services.urls')),      # فئات الخدمات
    path('api/workers/', include('workers.urls')),        # العمال
    path('api/tasks/', include('tasks.urls')),           # المهام
    path('api/clients/', include('clients.urls')),
    path('api/chat/', include('chat.urls')),             # المحادثات
    path('api/notifications/', include('notifications.urls')), # الإشعارات
    path('api/payments/', include('payments.urls')),
    path('api/admin/', include('admin_api.urls')), 
    path('api/complaints/', include('complaints.urls')),


]

# إضافة مسارات الملفات في Development فقط
if settings.DEBUG:
    # تمكين الوصول للملفات المرفوعة عبر MEDIA_URL
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # إنشاء مجلدات الصور تلقائيًا
    image_dirs = [
        'worker_avatars',
        'client_avatars'
    ]
    for dir_name in image_dirs:
        dir_path = os.path.join(settings.MEDIA_ROOT, dir_name)
        os.makedirs(dir_path, exist_ok=True)
