# payments/models.py
from django.db import models
from django.core.validators import MinValueValidator
from users.models import User
from tasks.models import ServiceRequest


class Payment(models.Model):
    """
    Payment transaction model
    Record all payments between clients and workers
    """
    
    task = models.OneToOneField(
        ServiceRequest,
        on_delete=models.CASCADE,
        related_name='payment'
    )
    
    payer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='payments_made',
        limit_choices_to={'role': 'client'}
    )
    
    receiver = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='payments_received',
        limit_choices_to={'role': 'worker'}
    )
    
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Espèces'),
        ('bankily', 'Bankily'),
        ('sedad', 'Sedad'),
        ('masrivi', 'Masrivi'),
    ]
    
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='cash'
    )
    
    transaction_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        unique=True
    )
    
    # ✅ معلومات Moosyl (للمدفوعات الإلكترونية)
    moosyl_transaction_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        unique=True,
        help_text="معرف المعاملة من Moosyl"
    )
    
    moosyl_response = models.JSONField(
        null=True,
        blank=True,
        help_text="الاستجابة الكاملة من Moosyl"
    )
    
    failure_reason = models.TextField(
        blank=True,
        null=True,
        help_text="سبب الفشل إن وجد"
    )
    
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('processing', 'En cours'),
        ('completed', 'Terminé'),
        ('failed', 'Échoué'),
        ('cancelled', 'Annulé'),
    ]
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    notes = models.TextField(
        blank=True,
        null=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        indexes = [
            models.Index(fields=['payer', '-created_at']),
            models.Index(fields=['receiver', '-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['moosyl_transaction_id']),
        ]
    
    def __str__(self):
        payer_name = self.payer.get_full_name() or self.payer.phone
        receiver_name = self.receiver.get_full_name() or self.receiver.phone
        return f"Payment: {self.amount} MRU - {payer_name} to {receiver_name}"
    
    def save(self, *args, **kwargs):
        """تحديث timestamp عند الحفظ"""
        if self.status == 'completed' and not self.completed_at:
            from django.utils import timezone
            self.completed_at = timezone.now()
        super().save(*args, **kwargs)
    
    @property
    def is_completed(self):
        """التحقق من اكتمال الدفع"""
        return self.status == 'completed'
    
    @property
    def is_electronic_payment(self):
        """التحقق من أن الدفع إلكتروني (عبر Moosyl)"""
        return self.payment_method in ['bankily', 'sedad', 'masrivi']
    
    @property
    def payment_method_display(self):
        """عرض طريقة الدفع بشكل مقروء"""
        return dict(self.PAYMENT_METHOD_CHOICES).get(self.payment_method)
    
    def mark_as_completed(self, moosyl_transaction_id=None):
        """تمييز الدفع كمكتمل"""
        from django.utils import timezone
        self.status = 'completed'
        self.completed_at = timezone.now()
        if moosyl_transaction_id:
            self.moosyl_transaction_id = moosyl_transaction_id
        self.save()
    
    def mark_as_failed(self, reason=""):
        """تمييز الدفع كفاشل"""
        self.status = 'failed'
        self.failure_reason = reason
        self.save()