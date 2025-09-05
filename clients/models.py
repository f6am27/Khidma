# clients/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from accounts.models import Profile
from workers.models import WorkerProfile


class ClientProfile(models.Model):
    """
    Extended client profile with additional information
    ملف العميل المفصل مع معلومات إضافية
    """
    profile = models.OneToOneField(
        Profile, 
        on_delete=models.CASCADE, 
        related_name='client_profile'
    )
    
    # Personal information
    bio = models.TextField(max_length=500, blank=True, help_text="Client bio or description")
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=10, 
        choices=[
            ('male', 'Male'),
            ('female', 'Female'),
            ('other', 'Other'),
        ],
        blank=True
    )
    
    # Contact and location
    address = models.TextField(max_length=300, blank=True, help_text="Full address")
    emergency_contact = models.CharField(max_length=20, blank=True, help_text="Emergency contact number")
    
    # Profile settings
    profile_image = models.ImageField(upload_to='clients/profiles/', null=True, blank=True)
    is_verified = models.BooleanField(default=False, help_text="Account verification status")
    
    # Statistics (auto-calculated)
    total_tasks_published = models.PositiveIntegerField(default=0)
    total_tasks_completed = models.PositiveIntegerField(default=0)
    total_amount_spent = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Account status
    is_active = models.BooleanField(default=True)
    last_activity = models.DateTimeField(auto_now=True)
    
    # Preferences
    preferred_language = models.CharField(
        max_length=10,
        choices=[
            ('fr', 'Français'),
            ('ar', 'العربية'),
            ('en', 'English'),
        ],
        default='fr'
    )
    notifications_enabled = models.BooleanField(default=True)
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Client Profile"
        verbose_name_plural = "Client Profiles"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"ClientProfile: {self.profile.user.username}"
    
    @property
    def full_name(self):
        """Get client's full name"""
        user = self.profile.user
        if user.first_name and user.last_name:
            return f"{user.first_name} {user.last_name}"
        return user.username
    
    @property
    def member_since(self):
        """Get formatted member since date"""
        return self.created_at.strftime("%B %Y")
    
    @property
    def success_rate(self):
        """Calculate task completion success rate"""
        if self.total_tasks_published == 0:
            return 0.0
        return round((self.total_tasks_completed / self.total_tasks_published) * 100, 1)
    
    def update_stats(self):
        """Update client statistics (called after task completion)"""
        from tasks.models import ServiceRequest
        
        # Update task counts
        self.total_tasks_published = ServiceRequest.objects.filter(
            client=self.profile
        ).count()
        
        self.total_tasks_completed = ServiceRequest.objects.filter(
            client=self.profile,
            status='completed'
        ).count()
        
        # Update total spent (when payment system is implemented)
        # self.total_amount_spent = calculate_total_spent()
        
        self.save()


class FavoriteWorker(models.Model):
    """
    Client's favorite workers for easy access
    العمال المفضلين للعميل للوصول السريع
    """
    client = models.ForeignKey(
        Profile, 
        on_delete=models.CASCADE, 
        related_name='favorite_workers'
    )
    worker = models.ForeignKey(
        WorkerProfile, 
        on_delete=models.CASCADE, 
        related_name='favorited_by_clients'
    )
    
    # Additional info
    notes = models.TextField(max_length=200, blank=True, help_text="Private notes about this worker")
    added_at = models.DateTimeField(auto_now_add=True)
    last_contacted = models.DateTimeField(null=True, blank=True)
    
    # Interaction tracking
    times_hired = models.PositiveIntegerField(default=0)
    total_spent_with_worker = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    last_rating_given = models.PositiveIntegerField(null=True, blank=True, help_text="Last rating given to this worker")
    
    class Meta:
        verbose_name = "Favorite Worker"
        verbose_name_plural = "Favorite Workers"
        unique_together = ['client', 'worker']  # Prevent duplicate favorites
        ordering = ['-added_at']
    
    def __str__(self):
        return f"{self.client.user.username} -> {self.worker.user.get_full_name()}"
    
    @property
    def worker_full_name(self):
        """Get worker's full name"""
        user = self.worker.profile.user
        if user.first_name and user.last_name:
            return f"{user.first_name} {user.last_name}"
        return user.username
    
    @property
    def worker_services(self):
        """Get worker's service categories"""
        return [service.category.name for service in self.worker.services.all()]
    
    @property
    def relationship_duration(self):
        """Calculate how long this worker has been in favorites"""
        duration = timezone.now() - self.added_at
        
        if duration.days < 30:
            return f"{duration.days} jours"
        elif duration.days < 365:
            months = duration.days // 30
            return f"{months} mois"
        else:
            years = duration.days // 365
            return f"{years} an{'s' if years > 1 else ''}"
    
    def update_interaction_stats(self, amount_paid=None, rating_given=None):
        """Update interaction statistics"""
        self.times_hired += 1
        self.last_contacted = timezone.now()
        
        if amount_paid:
            self.total_spent_with_worker += amount_paid
        
        if rating_given:
            self.last_rating_given = rating_given
        
        self.save()


class ClientNotification(models.Model):
    """
    Client-specific notifications
    إشعارات خاصة بالعملاء
    """
    NOTIFICATION_TYPES = [
        ('task_published', 'Task Published'),
        ('worker_applied', 'Worker Applied'),
        ('task_accepted', 'Task Accepted'),
        ('task_completed', 'Task Completed'),
        ('payment_reminder', 'Payment Reminder'),
        ('favorite_worker_online', 'Favorite Worker Online'),
        ('system_update', 'System Update'),
        ('promotion', 'Promotion'),
    ]
    
    client = models.ForeignKey(
        Profile, 
        on_delete=models.CASCADE, 
        related_name='client_notifications'
    )
    
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField(max_length=500)
    
    # Related objects
    related_task = models.ForeignKey(
        'tasks.ServiceRequest', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True
    )
    related_worker = models.ForeignKey(
        WorkerProfile, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True
    )
    
    # Status
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Client Notification"
        verbose_name_plural = "Client Notifications"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Notification for {self.client.user.username}: {self.title}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        self.is_read = True
        self.read_at = timezone.now()
        self.save()
    
    @property
    def is_expired(self):
        """Check if notification is expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False


class ClientSettings(models.Model):
    """
    Client application settings and preferences
    إعدادات وتفضيلات تطبيق العميل
    """
    client = models.OneToOneField(
        Profile, 
        on_delete=models.CASCADE, 
        related_name='client_settings'
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
    
    show_last_seen = models.BooleanField(default=True)
    allow_contact_from_workers = models.BooleanField(default=True)
    
    # Location and service preferences
    auto_detect_location = models.BooleanField(default=True)
    search_radius_km = models.PositiveIntegerField(default=10, help_text="Search radius in kilometers")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Client Settings"
        verbose_name_plural = "Client Settings"
    
    def __str__(self):
        return f"Settings for {self.client.user.username}"