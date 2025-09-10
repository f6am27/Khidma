from django.contrib import admin
from django.urls import path,include


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
