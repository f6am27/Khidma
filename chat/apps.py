# chat/apps.py
from django.apps import AppConfig


class ChatConfig(AppConfig):
    """
    إعدادات تطبيق المحادثات
    Chat app configuration
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chat'
    verbose_name = 'Chat System'
    verbose_name_plural = 'Chat Systems'