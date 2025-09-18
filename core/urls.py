from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
import os

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/users/', include('users.urls')),
    path('api/services/', include('services.urls')),      # فئات الخدمات
    path('api/workers/', include('workers.urls')),        # العمال
    path('api/tasks/', include('tasks.urls')),           # المهام
    path('api/clients/', include('clients.urls')),
    path('api/chat/', include('chat.urls')),             # المحادثات
    path('api/notifications/', include('notifications.urls')), # الإشعارات
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
