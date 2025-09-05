# tasks/models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import Profile
from workers.models import WorkerProfile
from services.models import ServiceCategory


class ServiceRequest(models.Model):
    """
    Task/Service request posted by client
    طلب الخدمة/المهمة من العميل
    """
    # Basic info
    client = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="service_requests"
    )
    
    # Task details
    title = models.CharField(max_length=200)
    description = models.TextField()
    service_category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.CASCADE,
        related_name="service_requests"
    )
    
    # Pricing - no minimum/maximum restrictions
    budget = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],  # Only ensure positive amount
        help_text="Budget proposé en MRU"
    )
    
    # Location and timing
    location = models.CharField(max_length=300)  # "Tevragh Zeina, Nouakchott"
    preferred_time = models.CharField(max_length=100)  # "9:00 AM" or "2:30 PM" etc.
    
    # Location coordinates (optional for GPS location)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Status management
    STATUS_CHOICES = [
        ('published', 'Publiée'),
        ('active', 'En cours'),
        ('work_completed', 'Travail terminé'),
        ('completed', 'Terminée'),
        ('cancelled', 'Annulée'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='published'
    )
    
    # Worker assignment
    assigned_worker = models.ForeignKey(
        WorkerProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tasks"
    )
    
    # Final pricing (negotiated price if different from budget)
    final_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Prix final négocié"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    work_completed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    # Additional info
    is_urgent = models.BooleanField(default=False)
    requires_materials = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Service Request"
        verbose_name_plural = "Service Requests"
    
    def __str__(self):
        return f"{self.title} - {self.client.user.username} ({self.get_status_display()})"
    
    @property
    def applications_count(self):
        """Number of workers who applied"""
        return self.applications.filter(is_active=True).count()
    
    @property 
    def client_user(self):
        """Quick access to client user"""
        return self.client.user
    
    @property
    def service_type(self):
        """Service type name (for Flutter compatibility)"""
        return self.service_category.name


class TaskApplication(models.Model):
    """
    Worker application to a service request (simplified)
    تقدم العامل للمهمة/الخدمة (مبسط)
    """
    service_request = models.ForeignKey(
        ServiceRequest,
        on_delete=models.CASCADE,
        related_name="applications"
    )
    worker = models.ForeignKey(
        WorkerProfile,
        on_delete=models.CASCADE,
        related_name="task_applications"
    )
    
    # Message templates for automatic responses
    MESSAGE_TEMPLATES = [
        "Je suis disponible pour cette tâche et j'ai l'expérience nécessaire.",
        "Bonjour, je peux réaliser cette mission rapidement et efficacement.",
        "J'ai plusieurs années d'expérience dans ce domaine. Je suis disponible.",
        "Mission intéressante ! Je suis libre et motivé pour la réaliser.",
        "Bonjour, je propose mes services pour cette tâche. Qualité garantie.",
    ]
    
    # Only message field - no proposed price or availability time
    application_message = models.TextField(
        blank=True,
        default="Je suis disponible pour cette tâche et j'ai l'expérience nécessaire.",
        help_text="Message du candidat (optionnel)"
    )
    
    # Application status
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('accepted', 'Acceptée'),
        ('rejected', 'Refusée'),
    ]
    application_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    # Flags
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    applied_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('service_request', 'worker')
        ordering = ['-applied_at']
        verbose_name = "Task Application"
        verbose_name_plural = "Task Applications"
    
    def __str__(self):
        return f"{self.worker.user.username} → {self.service_request.title}"
    
    @property
    def worker_name(self):
        """Worker full name for display"""
        user = self.worker.profile.user
        if user.first_name and user.last_name:
            return f"{user.first_name} {user.last_name}"
        return user.username
    
    @property
    def worker_rating(self):
        """Worker average rating"""
        return self.worker.average_rating
    
    @property
    def worker_phone(self):
        """Worker phone number"""
        return self.worker.profile.phone


class TaskReview(models.Model):
    """
    Client review of completed task (simplified)
    تقييم العميل للمهمة المكتملة (مبسط)
    """
    service_request = models.OneToOneField(
        ServiceRequest,
        on_delete=models.CASCADE,
        related_name="review"
    )
    client = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="given_reviews"
    )
    worker = models.ForeignKey(
        WorkerProfile,
        on_delete=models.CASCADE,
        related_name="received_reviews"
    )
    
    # Rating (1-5 stars) - required
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Note de 1 à 5 étoiles"
    )
    
    # Written review - optional
    review_text = models.TextField(
        blank=True,
        help_text="Commentaire sur le service (optionnel)"
    )
    
    # Flags
    would_recommend = models.BooleanField(default=True)
    is_public = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Task Review"
        verbose_name_plural = "Task Reviews"
    
    def __str__(self):
        return f"Review: {self.service_request.title} - {self.rating}⭐"
    
    def save(self, *args, **kwargs):
        """Update worker's average rating when review is saved"""
        super().save(*args, **kwargs)
        
        # Recalculate worker's average rating
        from django.db.models import Avg
        
        avg_rating = TaskReview.objects.filter(
            worker=self.worker,
            is_public=True
        ).aggregate(avg_rating=Avg('rating'))['avg_rating']
        
        if avg_rating:
            self.worker.average_rating = round(avg_rating, 2)
            
            # Update review count
            self.worker.total_reviews = TaskReview.objects.filter(
                worker=self.worker,
                is_public=True
            ).count()
            
            self.worker.save(update_fields=['average_rating', 'total_reviews'])


class TaskNotification(models.Model):
    """
    Notifications related to tasks
    إشعارات متعلقة بالمهام
    """
    # Recipients
    recipient = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="task_notifications"
    )
    
    # Related objects
    service_request = models.ForeignKey(
        ServiceRequest,
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True
    )
    task_application = models.ForeignKey(
        TaskApplication,
        on_delete=models.CASCADE,
        related_name="notifications", 
        null=True,
        blank=True
    )
    
    # Notification details
    NOTIFICATION_TYPES = [
        ('task_posted', 'Nouvelle tâche publiée'),
        ('application_received', 'Nouvelle candidature reçue'),
        ('application_accepted', 'Candidature acceptée'),
        ('application_rejected', 'Candidature refusée'),
        ('work_started', 'Travail commencé'),
        ('work_completed', 'Travail terminé'),
        ('task_completed', 'Tâche terminée'),
        ('payment_completed', 'Paiement effectué'),
        ('review_received', 'Évaluation reçue'),
        ('task_cancelled', 'Tâche annulée'),
    ]
    
    notification_type = models.CharField(
        max_length=50,
        choices=NOTIFICATION_TYPES
    )
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Status
    is_read = models.BooleanField(default=False)
    is_sent = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Task Notification"
        verbose_name_plural = "Task Notifications"
    
    def __str__(self):
        return f"{self.recipient.user.username} - {self.title}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = models.timezone.now()
            self.save(update_fields=['is_read', 'read_at'])