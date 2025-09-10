# workers/models.py - النسخة النهائية المحسنة
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from users.models import User
from services.models import ServiceCategory


class WorkerService(models.Model):
    """
    Services offered by a worker with pricing
    الخدمات التي يقدمها العامل مع الأسعار
    """
    worker = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name="worker_services",
        limit_choices_to={'role': 'worker'}
    )
    category = models.ForeignKey(
        ServiceCategory, 
        on_delete=models.CASCADE
    )
    
    # Pricing
    base_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(100.0)],
        help_text="Prix de base en MRU"
    )
    
    PRICE_TYPE_CHOICES = [
        ('fixed', 'Prix fixe'),
        ('hourly', 'Par heure'),
        ('negotiable', 'Négociable'),
    ]
    price_type = models.CharField(
        max_length=20, 
        choices=PRICE_TYPE_CHOICES, 
        default='negotiable'
    )
    
    # Service details
    description = models.TextField(
        blank=True,
        help_text="Specific description for this service"
    )
    
    # Availability for this specific service
    is_active = models.BooleanField(default=True)
    min_duration_hours = models.PositiveIntegerField(
        default=1,
        help_text="Minimum duration in hours"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('worker', 'category')
        verbose_name = "Worker Service"
        verbose_name_plural = "Worker Services"
        ordering = ['-created_at']

    def __str__(self):
        worker_name = self.worker.get_full_name() or self.worker.phone
        return f"{worker_name} - {self.category.name} ({self.base_price} MRU)"


class WorkerGallery(models.Model):
    """
    Portfolio/gallery images for workers
    معرض أعمال العامل
    """
    worker = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="worker_gallery",
        limit_choices_to={'role': 'worker'}
    )
    image = models.ImageField(upload_to='worker_gallery/')
    caption = models.CharField(max_length=200, blank=True)
    service_category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Which service this image relates to"
    )
    is_featured = models.BooleanField(
        default=False,
        help_text="Featured images show first"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_featured', '-created_at']
        verbose_name = "Worker Gallery Image"
        verbose_name_plural = "Worker Gallery Images"

    def __str__(self):
        worker_name = self.worker.get_full_name() or self.worker.phone
        return f"{worker_name} - Gallery Image"


class WorkerSettings(models.Model):
    """
    Worker application settings and preferences
    إعدادات وتفضيلات تطبيق العامل
    """
    worker = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='worker_settings',
        limit_choices_to={'role': 'worker'}
    )
    
    # Notification preferences
    push_notifications = models.BooleanField(default=True)
    email_notifications = models.BooleanField(default=False)
    sms_notifications = models.BooleanField(default=True)
    
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
    
    # Worker-specific settings
    auto_accept_jobs = models.BooleanField(
        default=False,
        help_text="Automatically accept job requests"
    )
    
    max_daily_jobs = models.PositiveIntegerField(
        default=5,
        help_text="Maximum jobs per day"
    )
    
    profile_visibility = models.CharField(
        max_length=20,
        choices=[
            ('public', 'Public'),
            ('clients_only', 'Clients Only'),
            ('private', 'Private'),
        ],
        default='public'
    )
    
    # Work preferences
    travel_radius_km = models.PositiveIntegerField(
        default=15,
        help_text="Maximum travel distance in kilometers"
    )
    
    instant_booking = models.BooleanField(
        default=True,
        help_text="Allow clients to book instantly"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Worker Settings"
        verbose_name_plural = "Worker Settings"
    
    def __str__(self):
        return f"Settings for {self.worker.get_full_name()}"