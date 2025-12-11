# complaints/models.py
from django.db import models
from django.utils import timezone
from users.models import User


class Complaint(models.Model):
    """
    نموذج الشكاوى والاستشكالات
    يدعم النص والصوت
    """
    
    # نوع الشكوى
    TYPE_CHOICES = [
        ('text', 'نصية'),
        ('audio', 'صوتية'),
        ('both', 'نص + صوت'),
    ]
    
    # فئة المشكلة
    CATEGORY_CHOICES = [
        ('technical', 'مشكلة تقنية'),
        ('payment', 'مشكلة في الدفع'),
        ('suggestion', 'اقتراح تحسين'),
        ('account', 'مشكلة في الحساب'),
        ('worker_behavior', 'سلوك عامل'),
        ('client_behavior', 'سلوك عميل'),
        ('other', 'أخرى'),
    ]
    
    # حالة الشكوى
    STATUS_CHOICES = [
        ('new', 'جديد'),
        ('under_review', 'قيد المراجعة'),
        ('resolved', 'محلول'),
        ('closed', 'مغلق'),
    ]
    
    # أولوية الشكوى
    PRIORITY_CHOICES = [
        ('normal', 'عادي'),
        ('important', 'مهم'),
        ('urgent', 'عاجل'),
    ]
    
    # معلومات المستخدم
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='complaints',
        help_text="المستخدم الذي قدم الشكوى"
    )
    
    # بيانات الشكوى
    type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES,
        default='text',
        verbose_name="نوع الشكوى"
    )
    
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='other',
        verbose_name="فئة المشكلة"
    )
    
    # المحتوى
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="الوصف النصي",
        help_text="وصف المشكلة (اختياري إذا كان هناك تسجيل صوتي)"
    )
    
    audio_file = models.FileField(
        upload_to='complaints/audio/%Y/%m/',
        blank=True,
        null=True,
        verbose_name="التسجيل الصوتي",
        help_text="ملف صوتي (MP3, AAC) - max 10MB"
    )
    
    audio_duration = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name="مدة التسجيل",
        help_text="مدة التسجيل بالثواني"
    )
    
    # الحالة والأولوية
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='new',
        verbose_name="الحالة"
    )
    
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='normal',
        verbose_name="الأولوية"
    )
    
    # معالجة الشكوى
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_complaints',
        limit_choices_to={'role': 'admin'},
        verbose_name="تم الحل بواسطة"
    )
    
    admin_notes = models.TextField(
        blank=True,
        verbose_name="ملاحظات الأدمن",
        help_text="ملاحظات خاصة للأدمن"
    )
    
    # تواريخ
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاريخ الإنشاء"
    )
    
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="تاريخ الحل"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="آخر تحديث"
    )
    
    class Meta:
        verbose_name = "Complaint"
        verbose_name_plural = "Complaints"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['category', '-created_at']),
        ]
    
    def __str__(self):
        return f"Complaint #{self.id} - {self.get_category_display()} by {self.user.get_full_name()}"
    
    def save(self, *args, **kwargs):
        # تحديد نوع الشكوى تلقائياً
        if self.description and self.audio_file:
            self.type = 'both'
        elif self.audio_file:
            self.type = 'audio'
        elif self.description:
            self.type = 'text'
        
        # تحديد تاريخ الحل عند تغيير الحالة
        if self.status in ['resolved', 'closed'] and not self.resolved_at:
            self.resolved_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    @property
    def is_resolved(self):
        """هل تم حل الشكوى؟"""
        return self.status in ['resolved', 'closed']
    
    @property
    def response_time(self):
        """مدة الاستجابة (إذا تم الحل)"""
        if self.resolved_at:
            delta = self.resolved_at - self.created_at
            return delta
        return None
    
    @property
    def user_role(self):
        """دور المستخدم (عميل أو عامل)"""
        return self.user.role