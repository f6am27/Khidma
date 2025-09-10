# clients/models.py - النسخة النهائية المحسنة
from django.db import models
from django.utils import timezone
from users.models import User


class FavoriteWorker(models.Model):
    """
    Client's favorite workers for easy access
    العمال المفضلين للعميل للوصول السريع
    """
    client = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='favorite_workers',
        limit_choices_to={'role': 'client'}
    )
    worker = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='favorited_by_clients',
        limit_choices_to={'role': 'worker'}
    )
    
    # Additional info
    notes = models.TextField(
        max_length=200, 
        blank=True, 
        help_text="Private notes about this worker"
    )
    added_at = models.DateTimeField(auto_now_add=True)
    last_contacted = models.DateTimeField(null=True, blank=True)
    
    # Interaction tracking
    times_hired = models.PositiveIntegerField(default=0)
    total_spent_with_worker = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00
    )
    
    class Meta:
        verbose_name = "Favorite Worker"
        verbose_name_plural = "Favorite Workers"
        unique_together = ['client', 'worker']
        ordering = ['-added_at']
    
    def __str__(self):
        return f"{self.client.get_full_name()} -> {self.worker.get_full_name()}"
    
    def update_interaction_stats(self, amount_paid=None):
        """Update interaction statistics"""
        self.times_hired += 1
        self.last_contacted = timezone.now()
        
        if amount_paid:
            self.total_spent_with_worker += amount_paid
        
        self.save()


class ClientSettings(models.Model):
    """
    Client application settings and preferences - دمج مع ClientProfile
    إعدادات وتفضيلات تطبيق العميل
    """
    client = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='client_settings',
        limit_choices_to={'role': 'client'}
    )
    
    # Notification preferences
    push_notifications = models.BooleanField(default=True)
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    
    # App preferences
    theme_preference = models.CharField(
        max_length=10,
        choices=[
            ('light', 'Light'),
            ('dark', 'Dark'),
            ('auto', 'Auto'),
        ],
        default='auto'
    )
    
    language = models.CharField(
        max_length=10,
        choices=[
            ('fr', 'Français'),
            ('ar', 'العربية'),
            ('en', 'English'),
        ],
        default='fr'
    )
    
    # Privacy settings
    profile_visibility = models.CharField(
        max_length=20,
        choices=[
            ('public', 'Public'),
            ('workers_only', 'Workers Only'),
            ('private', 'Private'),
        ],
        default='workers_only'
    )
    
    allow_contact_from_workers = models.BooleanField(default=True)
    
    # Location and service preferences
    auto_detect_location = models.BooleanField(default=True)
    search_radius_km = models.PositiveIntegerField(
        default=10, 
        help_text="Search radius in kilometers"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Client Settings"
        verbose_name_plural = "Client Settings"
    
    def __str__(self):
        return f"Settings for {self.client.get_full_name()}"