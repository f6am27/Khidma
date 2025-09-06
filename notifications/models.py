# notifications/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from accounts.models import Profile
from workers.models import WorkerProfile


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
        ('task_completed', 'Tâche confirmée terminée'),
        ('payment_sent', 'Paiement envoyé'),
        ('message_received', 'Message reçu'),
    ]
    
    ALL_NOTIFICATION_TYPES = CLIENT_NOTIFICATION_TYPES + WORKER_NOTIFICATION_TYPES
    
    # حقول أساسية
    recipient = models.ForeignKey(
        Profile, 
        on_delete=models.CASCADE, 
        related_name='notifications',
        help_text="المستلم للإشعار"
    )
    
    notification_type = models.CharField(
        max_length=30, 
        choices=ALL_NOTIFICATION_TYPES,
        help_text="نوع الإشعار"
    )
    
    # مفاتيح الترجمة بدلاً من النصوص المباشرة
    title_key = models.CharField(
        max_length=100,
        help_text="مفتاح ترجمة العنوان"
    )
    message_key = models.CharField(
        max_length=100,
        help_text="مفتاح ترجمة الرسالة"
    )
    
    # بيانات ديناميكية للرسائل (أسماء، أرقام، تواريخ)
    context_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="البيانات المستخدمة في الترجمة"
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
    
    related_worker = models.ForeignKey(
        WorkerProfile,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="العامل المرتبط بالإشعار"
    )
    
    related_application = models.ForeignKey(
        'tasks.TaskApplication',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="طلب العمل المرتبط بالإشعار"
    )
    
    # أولوية الإشعار
    PRIORITY_CHOICES = [
        ('low', 'Basse'),
        ('medium', 'Moyenne'),
        ('high', 'Haute'),
        ('urgent', 'Urgente'),
    ]
    
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='medium',
        help_text="أولوية الإشعار"
    )
    
    # انتهاء صلاحية الإشعار
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="تاريخ انتهاء صلاحية الإشعار"
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
        return f"Notification pour {self.recipient.user.username}: {self.notification_type}"
    
    @property
    def is_expired(self):
        """التحقق من انتهاء صلاحية الإشعار"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
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
    
    def get_localized_content(self, language='fr'):
        """
        الحصول على المحتوى المترجم
        Get localized content based on language
        """
        from .utils import get_translated_notification
        return get_translated_notification(
            self.title_key,
            self.message_key,
            self.context_data,
            language
        )
    
    @classmethod
    def create_for_client(cls, client, notification_type, context_data=None, **kwargs):
        """
        إنشاء إشعار للعميل
        Create notification for client
        """
        if context_data is None:
            context_data = {}
            
        return cls.objects.create(
            recipient=client,
            notification_type=notification_type,
            title_key=f'notifications.{notification_type}.title',
            message_key=f'notifications.{notification_type}.message',
            context_data=context_data,
            **kwargs
        )
    
    @classmethod
    def create_for_worker(cls, worker_profile, notification_type, context_data=None, **kwargs):
        """
        إنشاء إشعار للعامل
        Create notification for worker
        """
        if context_data is None:
            context_data = {}
            
        return cls.objects.create(
            recipient=worker_profile.profile,
            notification_type=notification_type,
            title_key=f'notifications.{notification_type}.title',
            message_key=f'notifications.{notification_type}.message',
            context_data=context_data,
            **kwargs
        )


class NotificationSettings(models.Model):
    """
    إعدادات الإشعارات لكل مستخدم
    Notification settings for each user
    """
    user = models.OneToOneField(
        Profile,
        on_delete=models.CASCADE,
        related_name='notification_settings',
        help_text="المستخدم"
    )
    
    # إعدادات عامة
    notifications_enabled = models.BooleanField(
        default=True,
        help_text="تفعيل الإشعارات بشكل عام"
    )
    
    # إعدادات حسب النوع (للمستقبل)
    task_notifications = models.BooleanField(
        default=True,
        help_text="إشعارات المهام"
    )
    
    message_notifications = models.BooleanField(
        default=True,
        help_text="إشعارات الرسائل"
    )
    
    payment_notifications = models.BooleanField(
        default=True,
        help_text="إشعارات المدفوعات"
    )
    
    # إعدادات التوقيت
    quiet_hours_start = models.TimeField(
        null=True,
        blank=True,
        help_text="بداية ساعات الهدوء"
    )
    
    quiet_hours_end = models.TimeField(
        null=True,
        blank=True,
        help_text="نهاية ساعات الهدوء"
    )
    
    # تواريخ
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Paramètres de notification"
        verbose_name_plural = "Paramètres de notifications"
    
    def __str__(self):
        return f"Paramètres pour {self.user.user.username}"
    
    def should_send_notification(self, notification_type=None):
        """
        التحقق من إمكانية إرسال الإشعار
        Check if notification should be sent
        """
        if not self.notifications_enabled:
            return False
        
        # التحقق من ساعات الهدوء
        if self.quiet_hours_start and self.quiet_hours_end:
            current_time = timezone.now().time()
            if self.quiet_hours_start <= current_time <= self.quiet_hours_end:
                return False
        
        # التحقق من نوع الإشعار (للمستقبل)
        if notification_type:
            if 'task' in notification_type and not self.task_notifications:
                return False
            if 'message' in notification_type and not self.message_notifications:
                return False
            if 'payment' in notification_type and not self.payment_notifications:
                return False
        
        return True


class NotificationTemplate(models.Model):
    """
    قوالب الإشعارات للترجمة
    Notification templates for translation
    """
    notification_type = models.CharField(
        max_length=30,
        unique=True,
        help_text="نوع الإشعار"
    )
    
    # القوالب بالفرنسية (افتراضي)
    title_fr = models.CharField(max_length=200, help_text="العنوان بالفرنسية")
    message_fr = models.TextField(help_text="الرسالة بالفرنسية")
    
    # القوالب بالعربية (للمستقبل)
    title_ar = models.CharField(max_length=200, blank=True, help_text="العنوان بالعربية")
    message_ar = models.TextField(blank=True, help_text="الرسالة بالعربية")
    
    # القوالب بالإنجليزية (للمستقبل)
    title_en = models.CharField(max_length=200, blank=True, help_text="العنوان بالإنجليزية")
    message_en = models.TextField(blank=True, help_text="الرسالة بالإنجليزية")
    
    # متغيرات القالب
    template_variables = models.JSONField(
        default=list,
        help_text="قائمة بالمتغيرات المطلوبة في القالب"
    )
    
    is_active = models.BooleanField(default=True, help_text="نشط")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Modèle de notification"
        verbose_name_plural = "Modèles de notifications"
    
    def __str__(self):
        return f"Template: {self.notification_type}"
    
    def get_template(self, language='fr'):
        """الحصول على القالب بلغة معينة"""
        title_field = f'title_{language}'
        message_field = f'message_{language}'
        
        title = getattr(self, title_field, '') or self.title_fr
        message = getattr(self, message_field, '') or self.message_fr
        
        return {
            'title': title,
            'message': message,
            'variables': self.template_variables
        }