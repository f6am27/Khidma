# chat/models.py
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from users.models import User


class Conversation(models.Model):
    """
    محادثة بين عميل وعامل
    Conversation between client and worker
    """
    # المشاركون في المحادثة - مباشرة مع User
    client = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='client_conversations',
        limit_choices_to={'role': 'client'},
        help_text="العميل في المحادثة"
    )
    
    worker = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='worker_conversations',
        limit_choices_to={'role': 'worker'},
        help_text="العامل في المحادثة"
    )
    
    # حالة المحادثة
    is_active = models.BooleanField(
        default=True,
        help_text="هل المحادثة نشطة"
    )

    deleted_by_client = models.BooleanField(default=False)
    deleted_by_worker = models.BooleanField(default=False)

    # ✅ أضف هذين السطرين الجديدين:
    deleted_at_by_client = models.DateTimeField(null=True, blank=True)
    deleted_at_by_worker = models.DateTimeField(null=True, blank=True)
    
    # إحصائيات المحادثة
    total_messages = models.PositiveIntegerField(
        default=0,
        help_text="إجمالي عدد الرسائل"
    )
    
    # آخر نشاط
    last_message_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="وقت آخر رسالة"
    )
    
    # تواريخ
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Conversation"
        verbose_name_plural = "Conversations"
        ordering = ['-last_message_at', '-created_at']
        unique_together = ['client', 'worker']
        indexes = [
            models.Index(fields=['client', 'is_active']),
            models.Index(fields=['worker', 'is_active']),
            models.Index(fields=['last_message_at']),
        ]
    
    def __str__(self):
        client_name = self.client.get_full_name() or self.client.username
        worker_name = self.worker.get_full_name() or self.worker.username
        return f"Conversation: {client_name} ↔ {worker_name}"
    
    def clean(self):
        """التحقق من صحة البيانات"""
        if self.client_id and self.worker_id:
            if self.client.role != 'client':
                raise ValidationError("المستخدم الأول يجب أن يكون عميل")
            if self.worker.role != 'worker':
                raise ValidationError("المستخدم الثاني يجب أن يكون عامل")
            if self.client_id == self.worker_id:
                raise ValidationError("لا يمكن أن تكون المحادثة مع نفس المستخدم")
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    @property
    def last_message(self):
        """آخر رسالة في المحادثة"""
        return self.messages.order_by('-created_at').first()
    
    def get_unread_count(self, user):
        """عدد الرسائل غير المقروءة للمستخدم"""
        return self.messages.filter(
            is_read=False
        ).exclude(sender=user).count()
    
    def mark_messages_as_read(self, user):
        """تحديد رسائل المحادثة كمقروءة للمستخدم"""
        unread_messages = self.messages.filter(
            is_read=False
        ).exclude(sender=user)
        
        updated_count = unread_messages.update(
            is_read=True,
            read_at=timezone.now()
        )
        
        return updated_count
    
    def update_last_message_time(self):
        """تحديث وقت آخر رسالة"""
        self.last_message_at = timezone.now()
        self.save(update_fields=['last_message_at'])


class Message(models.Model):
    """
    رسالة في المحادثة
    Message in conversation
    """
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
        help_text="المحادثة التي تنتمي إليها الرسالة"
    )
    
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_messages',
        help_text="مرسل الرسالة"
    )
    
    # محتوى الرسالة
    content = models.TextField(
        max_length=1000,
        help_text="نص الرسالة"
    )
    
    # حالة القراءة
    is_read = models.BooleanField(
        default=False,
        help_text="هل تم قراءة الرسالة"
    )
    
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="وقت قراءة الرسالة"
    )
    
    # تواريخ
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Message"
        verbose_name_plural = "Messages"
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['sender', 'created_at']),
            models.Index(fields=['is_read']),
        ]
    
    def __str__(self):
        sender_name = self.sender.get_full_name() or self.sender.username
        return f"Message from {sender_name}: {self.content[:50]}..."
    
    def clean(self):
        """التحقق من صحة البيانات"""
        if self.conversation_id and self.sender_id:
            if (self.sender != self.conversation.client and 
                self.sender != self.conversation.worker):
                raise ValidationError("المرسل يجب أن يكون مشارك في المحادثة")
    
    def save(self, *args, **kwargs):
        self.clean()
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            # تحديث إحصائيات المحادثة
            self.conversation.total_messages += 1
            self.conversation.update_last_message_time()
    
    @property
    def receiver(self):
        """المستلم للرسالة"""
        if self.sender == self.conversation.client:
            return self.conversation.worker
        return self.conversation.client


class BlockedUser(models.Model):
    """
    المستخدمون المحظورون
    Blocked users
    """
    blocker = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='blocked_users',
        help_text="المستخدم الذي قام بالحظر"
    )
    
    blocked = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='blocked_by_users',
        help_text="المستخدم المحظور"
    )
    
    reason = models.CharField(
        max_length=100,
        blank=True,
        help_text="سبب الحظر"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Blocked User"
        verbose_name_plural = "Blocked Users"
        unique_together = ['blocker', 'blocked']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['blocker']),
            models.Index(fields=['blocked']),
        ]
    
    def __str__(self):
        blocker_name = self.blocker.get_full_name() or self.blocker.username
        blocked_name = self.blocked.get_full_name() or self.blocked.username
        return f"{blocker_name} blocked {blocked_name}"
    
    def clean(self):
        """التحقق من صحة البيانات"""
        if self.blocker_id == self.blocked_id:
            raise ValidationError("لا يمكن حظر نفسك")
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class Report(models.Model):
    """
    تبليغات المستخدمين
    User reports
    """
    REPORT_REASONS = [
        ('inappropriate_content', 'Contenu inapproprié'),
        ('harassment', 'Harcèlement'),
        ('scam_fraud', 'Arnaque/Fraude'),
        ('spam', 'Spam'),
        ('fake_profile', 'Profil faux'),
        ('other', 'Autre'),
    ]
    
    REPORT_STATUS = [
        ('pending', 'En attente'),
        ('under_review', 'En cours d\'examen'),
        ('resolved', 'Résolu'),
        ('dismissed', 'Rejeté'),
    ]
    
    # المبلِّغ والمُبلَّغ عنه
    reporter = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='filed_reports',
        help_text="الشخص الذي قدم التبليغ"
    )
    
    reported_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='received_reports',
        help_text="الشخص المُبلَّغ عنه"
    )
    
    # المحادثة المرتبطة (اختيارية)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reports',
        help_text="المحادثة المرتبطة بالتبليغ"
    )
    
    # تفاصيل التبليغ
    reason = models.CharField(
        max_length=30,
        choices=REPORT_REASONS,
        help_text="سبب التبليغ"
    )
    
    description = models.TextField(
        max_length=500,
        blank=True,
        help_text="وصف تفصيلي للمشكلة"
    )
    
    # حالة التبليغ
    status = models.CharField(
        max_length=20,
        choices=REPORT_STATUS,
        default='pending',
        help_text="حالة التبليغ"
    )
    
    # معالجة التبليغ
    admin_notes = models.TextField(
        blank=True,
        help_text="ملاحظات الإدارة"
    )
    
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="وقت حل التبليغ"
    )
    
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_reports',
        limit_choices_to={'role': 'admin'},
        help_text="الإداري الذي عالج التبليغ"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Report"
        verbose_name_plural = "Reports"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['reporter']),
            models.Index(fields=['reported_user']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        reporter_name = self.reporter.get_full_name() or self.reporter.username
        reported_name = self.reported_user.get_full_name() or self.reported_user.username
        return f"Report: {reporter_name} → {reported_name} ({self.get_reason_display()})"
    
    def clean(self):
        """التحقق من صحة البيانات"""
        if self.reporter_id == self.reported_user_id:
            raise ValidationError("لا يمكن تبليغ نفسك")
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)