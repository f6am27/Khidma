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
        ('cash', 'Especes'),
        ('bankily', 'Bankily'),
        ('sedad', 'Sedad'),
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
    
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('completed', 'Termine'),
        ('cancelled', 'Annule'),
    ]
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='completed'
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
    def payment_method_display(self):
        """عرض طريقة الدفع بشكل مقروء"""
        return dict(self.PAYMENT_METHOD_CHOICES).get(self.payment_method)