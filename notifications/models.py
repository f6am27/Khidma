# notifications/models.py
from django.db import models
from django.utils import timezone
from users.models import User


class Notification(models.Model):
    """
    Unified notification system for clients and workers
    نظام إشعارات موحد للعملاء والعمال
    """
    
    # أنواع الإشعارات للعملاء
    CLIENT_NOTIFICATION_TYPES = [
        ('task_published', 'Tâche publiée'),
        ('worker_applied', 'Prestataire candidat'),
        ('task_completed', 'Tâche terminée'),
        ('payment_received', 'Paiement reçu'),
        ('message_received', 'Message reçu'),
        ('service_reminder', 'Rappel de service'),
        ('service_cancelled', 'Service annulé'),
    ]
    
    # أنواع الإشعارات للعمال  
    WORKER_NOTIFICATION_TYPES = [
        ('new_task_available', 'Nouvelle tâche disponible'),
        ('application_accepted', 'Candidature acceptée'),
        ('application_rejected', 'Candidature rejetée'),
        ('payment_sent', 'Paiement envoyé'),
        ('message_received', 'Message reçu'),
    ]
    
    ALL_NOTIFICATION_TYPES = CLIENT_NOTIFICATION_TYPES + WORKER_NOTIFICATION_TYPES
    
    # حقول أساسية - مباشرة مع User
    recipient = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='notifications',
        help_text="المستلم للإشعار"
    )
    
    notification_type = models.CharField(
        max_length=30, 
        choices=ALL_NOTIFICATION_TYPES,
        help_text="نوع الإشعار"
    )
    
    # نصوص مباشرة (بدون نظام ترجمة معقد)
    title = models.CharField(
        max_length=200,
        help_text="عنوان الإشعار"
    )
    
    message = models.TextField(
        help_text="محتوى الإشعار"
    )
    
    # حالة الإشعار
    is_read = models.BooleanField(default=False, help_text="هل تم قراءة الإشعار")
    read_at = models.DateTimeField(null=True, blank=True, help_text="وقت القراءة")
    
    # إشعارات مرتبطة بكائنات أخرى
    related_task = models.ForeignKey(
        'tasks.ServiceRequest',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="المهمة المرتبطة بالإشعار"
    )
    
    related_application = models.ForeignKey(
        'tasks.TaskApplication',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="طلب العمل المرتبط بالإشعار"
    )
    
    # تواريخ
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['notification_type']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Notification pour {self.recipient.username}: {self.notification_type}"
    
    @property
    def recipient_role(self):
        """الحصول على دور المستلم"""
        return self.recipient.role
    
    def mark_as_read(self):
        """تحديد الإشعار كمقروء"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
    
    @classmethod
    def create_for_client(cls, client, notification_type, title, message, **kwargs):
        """
        إنشاء إشعار للعميل
        Create notification for client
        """
        return cls.objects.create(
            recipient=client,
            notification_type=notification_type,
            title=title,
            message=message,
            **kwargs
        )
    
    @classmethod
    def create_for_worker(cls, worker, notification_type, title, message, **kwargs):
        """
        إنشاء إشعار للعامل
        Create notification for worker
        """
        return cls.objects.create(
            recipient=worker,
            notification_type=notification_type,
            title=title,
            message=message,
            **kwargs
        )


class NotificationSettings(models.Model):
    """
    إعدادات الإشعارات لكل مستخدم - مبسط
    Notification settings for each user - simplified
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='notification_settings',
        help_text="المستخدم"
    )
    
    # إعدادات مبسطة - تشغيل/إيقاف فقط
    notifications_enabled = models.BooleanField(
        default=True,
        help_text="تفعيل الإشعارات بشكل عام"
    )
    
    # تواريخ
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Paramètres de notification"
        verbose_name_plural = "Paramètres de notifications"
    
    def __str__(self):
        return f"Paramètres pour {self.user.username}"
    
    def should_send_notification(self):
        """
        التحقق من إمكانية إرسال الإشعار
        Check if notification should be sent
        """
        return self.notifications_enabled