# payments/models.py
"""
نماذج نظام الدفع والاشتراكات
تم التحديث: إضافة نظام تتبع IDs المهام
"""

from django.db import models
from django.conf import settings


class UserTaskCounter(models.Model):
    """
    عداد المهام المجانية لكل مستخدم (عميل أو عامل)
    
    النظام:
    - 5 مهام مجانية لكل مستخدم
    - بعد استنفاد الحد: اشتراك شهري مطلوب
    - تتبع IDs المهام لمنع الحساب المزدوج
    """
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='task_counter'
    )
    
    accepted_tasks_count = models.IntegerField(
        default=0,
        help_text="عدد المهام المقبولة (للعميل أو العامل)"
    )
    
    # ✅ جديد: قائمة IDs المهام المحسوبة
    counted_task_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="قائمة IDs المهام التي تم حسابها (لمنع الحساب المزدوج)"
    )
    
    last_payment_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="تاريخ آخر دفع للاشتراك"
    )
    
    last_reset_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="تاريخ آخر إعادة تعيين للعداد"
    )
    
    is_premium = models.BooleanField(
        default=False,
        help_text="هل المستخدم مشترك (premium)؟"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "عداد المهام"
        verbose_name_plural = "عدادات المهام"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.phone} - {self.accepted_tasks_count}/5 مهام"
    
    def increment_counter(self):
        """زيادة عداد المهام المقبولة"""
        self.accepted_tasks_count += 1
        self.save()
    
    def reset_counter(self):
        """إعادة تعيين العداد بعد الدفع"""
        from django.utils import timezone
        self.accepted_tasks_count = 0
        self.counted_task_ids = []  # ✅ إعادة تعيين القائمة
        self.last_payment_date = timezone.now()
        self.last_reset_date = timezone.now()
        self.save()
    
    @property
    def needs_payment(self):
        """
        هل يحتاج المستخدم للدفع؟
        True = وصل للحد المجاني وليس premium
        """
        FREE_TASK_LIMIT = getattr(settings, 'FREE_TASK_LIMIT', 5)
        return self.accepted_tasks_count >= FREE_TASK_LIMIT and not self.is_premium
    
    @property
    def tasks_remaining_before_payment(self):
        """عدد المهام المتبقية قبل طلب الاشتراك"""
        FREE_TASK_LIMIT = getattr(settings, 'FREE_TASK_LIMIT', 5)
        if self.is_premium:
            return float('inf')  # لا حدود للمشتركين
        remaining = FREE_TASK_LIMIT - self.accepted_tasks_count
        return max(0, remaining)


class PlatformSubscription(models.Model):
    """
    اشتراك شهري للمنصة (معطل حالياً - ينتظر ربط Benkily)
    
    السعر المقترح: 8 MRU/شهر (800 centime)
    """
    
    PAYMENT_METHOD_CHOICES = [
        ('benkily', 'Benkily'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'قيد الانتظار'),
        ('completed', 'مكتمل'),
        ('failed', 'فشل'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscriptions'
    )
    
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="المبلغ بالمليم (centime). مثال: 800.00"
    )
    
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='benkily'
    )
    
    transaction_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="معرف المعاملة من Benkily"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    valid_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text="صالح حتى (30 يوم من تاريخ الدفع)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "اشتراك"
        verbose_name_plural = "اشتراكات"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.phone} - {self.amount} MRU - {self.status}"