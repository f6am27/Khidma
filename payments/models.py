# payments/models.py
"""
نماذج نظام الدفع والاشتراكات
تم التحديث: إضافة نظام تتبع IDs المهام
"""

from django.db import models
from django.conf import settings


class UserTaskCounter(models.Model):
    """
    عداد المهام لكل مستخدم
    
    النظام الجديد:
    - 5 مهام مجانية للبداية
    - بعد ذلك: شراء حزم (8 مهام/حزمة بـ 5 أوقيات)
    """
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='task_counter'
    )
    
    # المهام المجانية (0-5)
    free_tasks_used = models.IntegerField(
        default=0,
        help_text="عدد المهام المجانية المستخدمة (من أصل 5)"
    )
    
    # إحصائيات الاشتراكات
    total_subscriptions = models.IntegerField(
        default=0,
        help_text="عدد مرات شراء الحزم (للإحصائيات)"
    )
    
    # تواريخ
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "عداد المهام"
        verbose_name_plural = "عدادات المهام"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.phone} - {self.free_tasks_used}/5 مجانية - {self.total_subscriptions} اشتراكات"
    
    def get_active_bundle(self):
        """الحصول على الحزمة النشطة الحالية"""
        return TaskBundle.objects.filter(
            user=self.user,
            is_active=True,
            moosyl_payment_status='completed'
        ).first()
    
    @property
    def current_limit(self):
        """الحد الحالي للمهام"""
        active_bundle = self.get_active_bundle()
        if active_bundle:
            return active_bundle.tasks_included  # 8
        return 5  # المجاني
    
    @property
    def current_usage(self):
        """عدد المهام المستخدمة حالياً"""
        active_bundle = self.get_active_bundle()
        if active_bundle:
            return active_bundle.tasks_used
        return self.free_tasks_used
    
    @property
    def needs_payment(self):
        """
        هل يحتاج المستخدم للدفع؟
        True = يجب شراء حزمة جديدة
        """
        # 1. إذا لم يستنفد المجاني بعد
        if self.free_tasks_used < 5:
            return False
        
        # 2. التحقق من الحزمة النشطة
        active_bundle = self.get_active_bundle()
        if active_bundle:
            return active_bundle.is_exhausted
        
        # 3. استنفد المجاني ولا توجد حزمة نشطة
        return True
    
    @property
    def tasks_remaining(self):
        """عدد المهام المتبقية"""
        active_bundle = self.get_active_bundle()
        if active_bundle:
            return active_bundle.tasks_remaining
        
        # المهام المجانية المتبقية
        return max(0, 5 - self.free_tasks_used)
    
    def increment_counter(self, task_id):
        """
        زيادة العداد (تُستدعى من Signal)
        
        المنطق:
        1. إذا كان في الفترة المجانية → زيادة free_tasks_used
        2. إذا كان لديه حزمة نشطة → زيادة tasks_used في الحزمة
        """
        active_bundle = self.get_active_bundle()
        
        if active_bundle and not active_bundle.is_exhausted:
            # لديه حزمة نشطة → استخدم منها
            success = active_bundle.increment_usage()
            if success:
                print(f"✅ Bundle usage increased: {self.user.phone} - Task #{task_id} - {active_bundle.tasks_used}/{active_bundle.tasks_included}")
            return success
        
        elif self.free_tasks_used < 5:
            # لا يزال في الفترة المجانية
            self.free_tasks_used += 1
            self.save()
            print(f"✅ Free tasks increased: {self.user.phone} - Task #{task_id} - {self.free_tasks_used}/5")
            return True
        
        else:
            # لا يمكن الزيادة (يحتاج اشتراك)
            print(f"❌ Cannot increment: {self.user.phone} needs subscription")
            return False
    
class TaskBundle(models.Model):
    """
    حزمة مهام مدفوعة (8 مهام بـ 5 أوقيات)
    يتم إنشاء حزمة جديدة عند كل عملية شراء عبر Moosyl
    """
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='task_bundles'
    )
    
    # تفاصيل الحزمة
    bundle_type = models.CharField(
        max_length=50,
        default='paid_8_tasks',
        help_text="نوع الحزمة"
    )
    
    tasks_included = models.IntegerField(
        default=8,
        help_text="عدد المهام في الحزمة"
    )
    
    tasks_used = models.IntegerField(
        default=0,
        help_text="عدد المهام المستخدمة من الحزمة"
    )
    
    # معلومات الدفع - Moosyl
    payment_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=5.00,
        help_text="المبلغ بالأوقية (MRU)"
    )
    
    payment_method = models.CharField(
        max_length=20,
        default='moosyl',
        help_text="طريقة الدفع"
    )
    
    moosyl_transaction_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="معرف المعاملة من Moosyl"
    )
    
    moosyl_payment_status = models.CharField(
        max_length=50,
        default='pending',
        choices=[
            ('pending', 'قيد الانتظار'),
            ('completed', 'مكتمل'),
            ('failed', 'فشل'),
        ],
        help_text="حالة الدفع من Moosyl"
    )
    
    # حالة الحزمة
    is_active = models.BooleanField(
        default=True,
        help_text="هل الحزمة نشطة؟"
    )
    
    # تواريخ
    purchased_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="تاريخ إنهاء جميع مهام الحزمة"
    )
    
    class Meta:
        verbose_name = "حزمة مهام"
        verbose_name_plural = "حزم المهام"
        ordering = ['-purchased_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['moosyl_transaction_id']),
        ]
    
    def __str__(self):
        return f"{self.user.phone} - {self.tasks_used}/{self.tasks_included} مهام - {self.get_moosyl_payment_status_display()}"
    
    @property
    def is_exhausted(self):
        """هل تم استنفاد الحزمة؟"""
        return self.tasks_used >= self.tasks_included
    
    @property
    def tasks_remaining(self):
        """عدد المهام المتبقية في الحزمة"""
        return max(0, self.tasks_included - self.tasks_used)
    
    def increment_usage(self):
        """زيادة عداد الاستخدام"""
        if self.tasks_used < self.tasks_included:
            self.tasks_used += 1
            
            # إذا اكتملت الحزمة
            if self.tasks_used >= self.tasks_included:
                from django.utils import timezone
                self.is_active = False
                self.completed_at = timezone.now()
            
            self.save()
            return True
        return False


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