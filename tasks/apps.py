# tasks/apps.py
"""
إعدادات تطبيق المهام (Tasks)
تم التحديث: تفعيل Signals
"""

from django.apps import AppConfig

class TasksConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tasks'
    verbose_name = 'إدارة المهام'
    
    def ready(self):
        """تفعيل Signals"""
        import tasks.signals  # ✅