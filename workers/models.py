# workers/models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import Profile
from services.models import ServiceCategory

class WorkerProfile(models.Model):
    """
    Detailed worker profile
    الملف الشخصي المفصل للعامل
    """
    profile = models.OneToOneField(
        Profile, 
        on_delete=models.CASCADE, 
        related_name="worker_profile"
    )
    
    # Basic info - معلومات أساسية
    bio = models.TextField(blank=True, help_text="Service description from onboarding")
    service_area = models.CharField(max_length=200, help_text="Zone d'intervention")
    profile_image = models.ImageField(upload_to='worker_avatars/', null=True, blank=True)
    
    # Availability - التوفر
    WEEKDAYS_CHOICES = [
        ('monday', 'Lun'),
        ('tuesday', 'Mar'), 
        ('wednesday', 'Mer'),
        ('thursday', 'Jeu'),
        ('friday', 'Ven'),
        ('saturday', 'Sam'),
        ('sunday', 'Dim'),
    ]
    
    available_days = models.JSONField(
        default=list, 
        help_text="List of available weekdays: ['monday', 'tuesday', ...]"
    )
    work_start_time = models.TimeField(null=True, blank=True)
    work_end_time = models.TimeField(null=True, blank=True)
    
    # Location - الموقع
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Stats and ratings - الإحصائيات والتقييمات
    total_jobs_completed = models.PositiveIntegerField(default=0)
    average_rating = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)]
    )
    total_reviews = models.PositiveIntegerField(default=0)
    
    # Status - حالة الحساب
    is_verified = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True)
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(auto_now=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.profile.user.username} - Worker Profile"

    @property
    def user(self):
        """Quick access to user object"""
        return self.profile.user

    @property
    def phone(self):
        """Quick access to phone"""
        return self.profile.phone

    class Meta:
        verbose_name = "Worker Profile"
        verbose_name_plural = "Worker Profiles"


class WorkerService(models.Model):
    """
    Services offered by a worker with pricing
    الخدمات التي يقدمها العامل مع الأسعار
    """
    worker = models.ForeignKey(
        WorkerProfile, 
        on_delete=models.CASCADE, 
        related_name="services"
    )
    category = models.ForeignKey(
        ServiceCategory, 
        on_delete=models.CASCADE
    )
    
    # Pricing - الأسعار
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
    
    # Service details - تفاصيل الخدمة  
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

    def __str__(self):
        return f"{self.worker.user.username} - {self.category.name} ({self.base_price} MRU)"


class WorkerGallery(models.Model):
    """
    Portfolio/gallery images for workers
    معرض أعمال العامل
    """
    worker = models.ForeignKey(
        WorkerProfile,
        on_delete=models.CASCADE,
        related_name="gallery"
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
        return f"{self.worker.user.username} - Gallery Image"


# Optional: For future features - للميزات المستقبلية
class WorkerExperience(models.Model):
    """
    Work experience entries for workers
    خبرات العمل للعامل
    """
    worker = models.ForeignKey(
        WorkerProfile,
        on_delete=models.CASCADE,
        related_name="experiences"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True, help_text="Leave blank for current")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start_date']
        verbose_name = "Worker Experience"
        verbose_name_plural = "Worker Experiences"

    def __str__(self):
        return f"{self.worker.user.username} - {self.title}"