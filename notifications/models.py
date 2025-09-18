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
        return f"Notification pour {self.recipient.phone}: {self.notification_type}"
    
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
        return f"Paramètres pour {self.user.phone}"
    
    def should_send_notification(self):
        """
        التحقق من إمكانية إرسال الإشعار
        Check if notification should be sent
        """
        return self.notifications_enabled


# ===============================================
# Firebase Push Notifications Models - إضافة جديدة
# ===============================================

class DeviceToken(models.Model):
    """
    حفظ رموز الأجهزة للإشعارات المتقدمة
    Device tokens for Firebase push notifications
    """
    
    PLATFORM_CHOICES = [
        ('android', 'Android'),
        ('ios', 'iOS'),
        ('web', 'Web'),
    ]
    
    # المستخدم المالك للجهاز
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='device_tokens',
        help_text="مالك الجهاز"
    )
    
    # رمز الجهاز من Firebase
    token = models.TextField(
        unique=True,
        help_text="Firebase FCM Token"
    )
    
    # معلومات الجهاز
    platform = models.CharField(
        max_length=10,
        choices=PLATFORM_CHOICES,
        default='android',
        help_text="نوع الجهاز"
    )
    
    device_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="اسم الجهاز (اختياري)"
    )
    
    app_version = models.CharField(
        max_length=20,
        blank=True,
        help_text="إصدار التطبيق"
    )
    
    # حالة الجهاز
    is_active = models.BooleanField(
        default=True,
        help_text="الجهاز نشط ويستقبل إشعارات"
    )
    
    last_used = models.DateTimeField(
        auto_now=True,
        help_text="آخر استخدام للجهاز"
    )
    
    # إعدادات الإشعارات للجهاز
    notifications_enabled = models.BooleanField(
        default=True,
        help_text="تفعيل الإشعارات على هذا الجهاز"
    )
    
    # إحصائيات
    total_notifications_sent = models.PositiveIntegerField(
        default=0,
        help_text="عدد الإشعارات المرسلة لهذا الجهاز"
    )
    
    last_notification_sent = models.DateTimeField(
        null=True, blank=True,
        help_text="آخر إشعار تم إرساله"
    )
    
    # تواريخ
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Device Token"
        verbose_name_plural = "Device Tokens"
        ordering = ['-last_used']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['platform']),
            models.Index(fields=['last_used']),
        ]
    
    def __str__(self):
        return f"{self.user.phone} - {self.platform} ({self.device_name or 'Unknown'})"
    
    @property
    def is_fresh(self):
        """تحديد ما إذا كان الرمز حديث (آخر 30 يوم)"""
        if not self.last_used:
            return False
        return (timezone.now() - self.last_used).days <= 30
    
    def update_last_used(self):
        """تحديث آخر استخدام"""
        self.last_used = timezone.now()
        self.save(update_fields=['last_used'])
    
    def increment_notification_count(self):
        """زيادة عداد الإشعارات المرسلة"""
        self.total_notifications_sent += 1
        self.last_notification_sent = timezone.now()
        self.save(update_fields=['total_notifications_sent', 'last_notification_sent'])
    
    def deactivate(self):
        """إلغاء تفعيل الجهاز (عند فشل الإرسال المتكرر)"""
        self.is_active = False
        self.save(update_fields=['is_active'])
    
    @classmethod
    def get_user_active_tokens(cls, user):
        """الحصول على جميع رموز الأجهزة النشطة للمستخدم"""
        return cls.objects.filter(
            user=user,
            is_active=True,
            notifications_enabled=True
        ).values_list('token', flat=True)
    
    @classmethod
    def cleanup_old_tokens(cls, days=60):
        """تنظيف الرموز القديمة غير المستخدمة"""
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        old_tokens = cls.objects.filter(last_used__lt=cutoff_date)
        count = old_tokens.count()
        old_tokens.delete()
        return count


class NotificationLog(models.Model):
    """
    سجل الإشعارات المرسلة عبر Firebase
    Log of notifications sent via Firebase
    """
    
    STATUS_CHOICES = [
        ('pending', 'معلق'),
        ('sent', 'مرسل'),
        ('delivered', 'تم التسليم'),
        ('failed', 'فشل'),
        ('invalid_token', 'رمز غير صالح'),
    ]
    
    # الإشعار الأصلي
    notification = models.ForeignKey(
        'Notification',
        on_delete=models.CASCADE,
        related_name='firebase_logs',
        help_text="الإشعار الأصلي"
    )
    
    # الجهاز المستهدف
    device_token = models.ForeignKey(
        DeviceToken,
        on_delete=models.CASCADE,
        help_text="الجهاز المستهدف"
    )
    
    # حالة الإرسال
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="حالة الإرسال"
    )
    
    # معرف Firebase للإشعار
    firebase_message_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="معرف الرسالة في Firebase"
    )
    
    # تفاصيل الإرسال
    sent_at = models.DateTimeField(
        null=True, blank=True,
        help_text="وقت الإرسال"
    )
    
    delivered_at = models.DateTimeField(
        null=True, blank=True,
        help_text="وقت التسليم"
    )
    
    # معلومات الخطأ
    error_message = models.TextField(
        blank=True,
        help_text="رسالة الخطأ إن وجدت"
    )
    
    retry_count = models.PositiveIntegerField(
        default=0,
        help_text="عدد محاولات الإعادة"
    )
    
    # تواريخ
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Notification Log"
        verbose_name_plural = "Notification Logs"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['sent_at']),
        ]
    
    def __str__(self):
        return f"Log {self.notification.id} -> {self.device_token.platform} ({self.status})"
    
    def mark_as_sent(self, firebase_message_id=None):
        """تحديد الإشعار كمرسل"""
        self.status = 'sent'
        self.sent_at = timezone.now()
        if firebase_message_id:
            self.firebase_message_id = firebase_message_id
        self.save(update_fields=['status', 'sent_at', 'firebase_message_id'])
    
    def mark_as_delivered(self):
        """تحديد الإشعار كمُسلّم"""
        self.status = 'delivered'
        self.delivered_at = timezone.now()
        self.save(update_fields=['status', 'delivered_at'])
    
    def mark_as_failed(self, error_message):
        """تحديد الإشعار كفاشل"""
        self.status = 'failed'
        self.error_message = error_message
        self.retry_count += 1
        self.save(update_fields=['status', 'error_message', 'retry_count'])