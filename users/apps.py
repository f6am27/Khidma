# users/apps.py
from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'
    verbose_name = 'Users Management'
    
    def ready(self):
        """تشغيل إعدادات إضافية عند تحميل التطبيق"""
        pass