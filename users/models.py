# users/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from math import radians, cos, sin, asin, sqrt
from .managers import UserManager


class User(AbstractUser):
    """
    Custom User Model - مستخدم مخصص
    يدعم phone للعميل/العامل + email للأدمن فقط
    """
    # إزالة username الافتراضي
    username = None
    
    # إزالة email من AbstractUser
    email = None
    
    # الحقول الأساسية
    phone = models.CharField(
        max_length=20, 
        unique=True,
        null=True, blank=True,
        help_text="رقم الهاتف للعميل/العامل"
    )
    
    # دور المستخدم
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('client', 'Client'),
        ('worker', 'Worker'),
    ]
    role = models.CharField(
        max_length=10, 
        choices=ROLE_CHOICES, 
        default='client'
    )
    
    # حالة التحقق
    is_verified = models.BooleanField(
        default=False,
        help_text="تم التحقق من الهاتف/الإيميل"
    )
    
    # حالة إكمال Onboarding (للعمال فقط)
    onboarding_completed = models.BooleanField(
        default=False,
        help_text="تم إكمال بيانات العامل"
    )
    
    # تواريخ
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # تحديد حقل تسجيل الدخول
    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = ['first_name']
    
    # استخدام المدير المخصص
    objects = UserManager()
    
    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ['-created_at']
    
    def clean(self):
        """التحقق من صحة البيانات"""
        super().clean()
        
        if self.role in ['client', 'worker']:
            if not self.phone:
                raise ValidationError("Client/Worker must have phone")
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        if self.role == 'admin':
            # للأدمن نعرض email من AdminProfile
            try:
                return f"{self.get_full_name() or self.admin_profile.email} (Admin)"
            except:
                return f"{self.get_full_name()} (Admin)"
        else:
            return f"{self.get_full_name() or self.phone} ({self.role})"
    
    @property
    def is_worker(self):
        return self.role == 'worker'
    
    @property
    def is_client(self):
        return self.role == 'client'
    
    @property
    def is_admin(self):
        return self.role == 'admin'
    
    @property
    def display_identifier(self):
        """معرف العرض (phone أو email)"""
        if self.role == 'admin':
            try:
                return self.admin_profile.email
            except:
                return self.phone or "No identifier"
        return self.phone


class AdminProfile(models.Model):
    """
    Admin Profile - بسيط للوحة التحكم
    """
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='admin_profile',
        limit_choices_to={'role': 'admin'}
    )
    
    # email للأدمن فقط مع unique=True
    email = models.EmailField(
        unique=True,
        help_text="البريد الإلكتروني للأدمن"
    )
    
    # معلومات بسيطة
    display_name = models.CharField(
        max_length=100,
        help_text="اسم العرض في لوحة التحكم"
    )
    bio = models.TextField(
        blank=True,
        help_text="نبذة مختصرة"
    )
    
    # صورة الملف الشخصي
    profile_image = models.ImageField(
        upload_to='admin_avatars/', 
        null=True, blank=True,
        help_text="صورة شخصية للأدمن"
    )
    
    # معلومات إضافية
    department = models.CharField(
        max_length=50,
        blank=True,
        help_text="القسم/الإدارة"
    )
    
    # حالة النشاط
    is_active_admin = models.BooleanField(
        default=True,
        help_text="أدمن نشط"
    )
    last_login_dashboard = models.DateTimeField(
        null=True, blank=True,
        help_text="آخر دخول للوحة التحكم"
    )
    
    # تواريخ
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Admin Profile"
        verbose_name_plural = "Admin Profiles"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Admin: {self.display_name} ({self.email})"


class WorkerProfile(models.Model):
    """
    Worker Profile - إجباري للعمال
    """
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='worker_profile',
        limit_choices_to={'role': 'worker'}
    )
    
    # البيانات الأساسية (من صفحة Onboarding)
    bio = models.TextField(
        help_text="وصف الخدمة من صفحة Onboarding"
    )
    service_area = models.CharField(
        max_length=200, 
        help_text="منطقة الخدمة - مطلوب"
    )
    
    # معلومات الخدمة
    service_category = models.CharField(
        max_length=100,
        help_text="فئة الخدمة المختارة في Onboarding"
    )
    base_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(100.0)],
        help_text="السعر المعتاد من Onboarding"
    )
    
    # صورة الملف الشخصي
    profile_image = models.ImageField(
        upload_to='worker_avatars/', 
        null=True, blank=True
    )
    
    # التوفر (من صفحة Onboarding)
    available_days = models.JSONField(
        default=list, 
        help_text="الأيام المتاحة: ['monday', 'tuesday', ...]"
    )
    work_start_time = models.TimeField(
        help_text="ساعة بداية العمل"
    )
    work_end_time = models.TimeField(
        help_text="ساعة نهاية العمل"
    )
    
    # الموقع (اختياري - للمستقبل)
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, 
        null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, 
        null=True, blank=True
    )
    
    # ===== إضافات جديدة لنظام المواقع =====
    location_sharing_enabled = models.BooleanField(
        default=False,
        help_text="تفعيل مشاركة الموقع الحالي - يتحكم فيه العامل"
    )
    current_latitude = models.DecimalField(
        max_digits=9, decimal_places=6, 
        null=True, blank=True,
        help_text="الموقع الحالي للعامل - خط العرض"
    )
    current_longitude = models.DecimalField(
        max_digits=9, decimal_places=6, 
        null=True, blank=True,
        help_text="الموقع الحالي للعامل - خط الطول"
    )
    location_last_updated = models.DateTimeField(
        null=True, blank=True,
        help_text="آخر مرة تم فيها تحديث الموقع الحالي"
    )
    location_accuracy = models.FloatField(
        null=True, blank=True,
        help_text="دقة الموقع بالأمتار"
    )
    LOCATION_STATUS_CHOICES = [
        ('active', 'نشط'),
        ('stale', 'قديم'),
        ('disabled', 'معطل'),
    ]
    location_status = models.CharField(
        max_length=20,
        choices=LOCATION_STATUS_CHOICES,
        default='disabled',
        help_text="حالة مشاركة الموقع"
    )
    location_sharing_updated_at = models.DateTimeField(
        null=True, blank=True,
        help_text="آخر مرة تم تغيير حالة مشاركة الموقع"
    )
    
    # الإحصائيات (محسوبة تلقائياً)
    total_jobs_completed = models.PositiveIntegerField(default=0)
    average_rating = models.DecimalField(
        max_digits=3, decimal_places=2, 
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)]
    )
    total_reviews = models.PositiveIntegerField(default=0)
    
    # الحالة
    is_verified = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True)
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(auto_now=True)
    
    # تواريخ
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Worker Profile"
        verbose_name_plural = "Worker Profiles"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Worker: {self.user.get_full_name()} - {self.service_category}"
    
    def save(self, *args, **kwargs):
        if not self.pk:
            self.user.onboarding_completed = True
            self.user.save(update_fields=['onboarding_completed'])
        super().save(*args, **kwargs)
    
    # ====== Methods الخاصة بنظام المواقع ======
    def update_current_location(self, latitude, longitude, accuracy=None):
        if not self.location_sharing_enabled:
            return False
        self.current_latitude = latitude
        self.current_longitude = longitude
        self.location_last_updated = timezone.now()
        if accuracy is not None:
            self.location_accuracy = accuracy
        self.location_status = 'active'
        self.save(update_fields=[
            'current_latitude', 'current_longitude',
            'location_last_updated', 'location_accuracy', 'location_status'
        ])
        return True
    
    def toggle_location_sharing(self, enabled):
        self.location_sharing_enabled = enabled
        self.location_sharing_updated_at = timezone.now()
        if enabled:
            self.location_status = 'active' if self.current_latitude else 'disabled'
        else:
            self.location_status = 'disabled'
        self.save(update_fields=[
            'location_sharing_enabled', 'location_sharing_updated_at', 'location_status'
        ])
        return self.location_sharing_enabled
    
    def is_location_fresh(self, minutes=30):
        if not self.location_last_updated:
            return False
        time_diff = timezone.now() - self.location_last_updated
        return time_diff.total_seconds() < (minutes * 60)
    
    def update_location_status(self):
        if not self.location_sharing_enabled:
            self.location_status = 'disabled'
        elif self.is_location_fresh(30):
            self.location_status = 'active'
        else:
            self.location_status = 'stale'
        self.save(update_fields=['location_status'])
    
    def calculate_distance_to(self, target_latitude, target_longitude):
        if not self.current_latitude or not self.current_longitude:
            return None
        return self._haversine_distance(
            float(self.current_latitude), float(self.current_longitude),
            float(target_latitude), float(target_longitude)
        )
    
    @staticmethod
    def _haversine_distance(lat1, lng1, lat2, lng2):
        lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
        c = 2 * asin(sqrt(a))
        r = 6371
        return c * r
    
    @property
    def is_currently_available_with_location(self):
        return (
            self.is_available and 
            self.location_sharing_enabled and 
            self.location_status == 'active' and
            self.is_location_fresh()
        )


class ClientProfile(models.Model):
    """
    Client Profile - اختياري للعملاء
    """
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='client_profile',
        limit_choices_to={'role': 'client'}
    )
    
    # معلومات شخصية (اختيارية)
    bio = models.TextField(blank=True)
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
    
    # العنوان ومعلومات الاتصال
    address = models.TextField(blank=True)
    emergency_contact = models.CharField(max_length=20, blank=True)
    
    # صورة الملف الشخصي  
    profile_image = models.ImageField(
        upload_to='client_avatars/', 
        null=True, blank=True
    )
    
    # الإحصائيات (محسوبة تلقائياً)
    total_tasks_published = models.PositiveIntegerField(default=0)
    total_tasks_completed = models.PositiveIntegerField(default=0)
    total_amount_spent = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00
    )
    
    # الإعدادات
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
    
    # تواريخ
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Client Profile"
        verbose_name_plural = "Client Profiles"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Client: {self.user.get_full_name()}"
    
    @property
    def success_rate(self):
        if self.total_tasks_published == 0:
            return 0.0
        return round(
            (self.total_tasks_completed / self.total_tasks_published) * 100, 
            1
        )
