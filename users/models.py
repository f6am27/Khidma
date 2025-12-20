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
    username = None
    
    email = models.EmailField(
        unique=True,
        blank=True,
        default='',
        help_text="البريد الإلكتروني - للأدمن إجباري، للآخرين اختياري"
    )
     #   حقل اللغة
    LANGUAGE_CHOICES = [
        ('ar', 'العربية'),
        ('fr', 'Français'),
        ('en', 'English'),
    ]
    preferred_language = models.CharField(
        max_length=2,
        choices=LANGUAGE_CHOICES,
        default='fr',
        help_text="اللغة المفضلة للمستخدم"
    )
    # الحقول الأساسية
    phone = models.CharField(
        max_length=20, 
        unique=True,
        blank=True,
        default='',
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
    
    # ✅✅✅ أضف هذه الحقول الثلاثة هنا ✅✅✅
    # حقول التعليق والإيقاف المؤقت
    is_suspended = models.BooleanField(
        default=False,
        verbose_name="معلق مؤقتاً",
        help_text="هل الحساب معلق مؤقتاً"
    )
    
    suspended_until = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="معلق حتى",
        help_text="تاريخ انتهاء التعليق - إذا كان فارغاً = إيقاف نهائي"
    )
    
    suspension_reason = models.TextField(
        blank=True,
        verbose_name="سبب التعليق",
        help_text="سبب تعليق الحساب"
    )
    
    USERNAME_FIELD = 'email'
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
            # ✅ للعملاء والعمال: اجعل email فارغ نهائياً
            if not self.email:
                # ✅ نضع قيمة فريدة بدلاً من string فارغ
                self.email = f"noemail_{self.phone}@placeholder.local"
                
        elif self.role == 'admin':
            if not self.email:
                raise ValidationError("Admin must have email")
        
    def save(self, *args, **kwargs):
        # ✅ تطبيق clean قبل الحفظ
        if not self.pk:  # فقط للمستخدمين الجدد
            self.clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        if self.role == 'admin':
            return f"{self.get_full_name() or self.email} (Admin)"
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
            return self.email or "No Email"
        return self.phone or "No Phone"
    
    @property
    def service_area(self):
        """للتوافق مع serializers"""
        if hasattr(self, 'worker_profile'):
            return self.worker_profile.service_area
        return None


class AdminProfile(models.Model):
    """
    Admin Profile - معلومات إضافية للأدمن (اختياري الآن)
    """
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='admin_profile',
        limit_choices_to={'role': 'admin'}
    )
    
    # معلومات إضافية (email الأساسي في User الآن)
    display_name = models.CharField(
        max_length=100,
        blank=True,
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

    is_online = models.BooleanField(
        default=False,
        help_text="هل الأدمن متصل حالياً"
    )
    last_activity = models.DateTimeField(
        auto_now=True,
        help_text="آخر نشاط للأدمن"
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
        return f"Admin: {self.display_name} ({self.user.email})"
    
    # ✅ Methods للتحكم بحالة الاتصال
    def set_online(self):
        """تعيين الأدمن كمتصل"""
        self.is_online = True
        self.last_activity = timezone.now()
        self.save(update_fields=['is_online', 'last_activity'])
    
    def set_offline(self):
        """تعيين الأدمن كغير متصل"""
        self.is_online = False
        self.save(update_fields=['is_online'])
    
    def update_activity(self):
        """تحديث آخر نشاط للأدمن"""
        self.last_activity = timezone.now()
        self.save(update_fields=['last_activity'])
        
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
        blank=True,
        default='',
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
        null=True,
        blank=True,
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
        blank=True,
        help_text="الأيام المتاحة: ['monday', 'tuesday', ...]"
    )

    work_start_time = models.TimeField(
        null=True,
        blank=True,
        help_text="ساعة بداية العمل"
    )

    work_end_time = models.TimeField(
    null=True,
    blank=True,
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
    gender = models.CharField(
        max_length=10, 
        choices=[
            ('male', 'Male'),
            ('female', 'Female'),
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
    
    # ✅✅✅ إضافة حقول الـ Online ✅✅✅
    is_online = models.BooleanField(
        default=False,
        help_text="هل العميل متصل حالياً"
    )
    last_seen = models.DateTimeField(
        auto_now=True,
        help_text="آخر ظهور للعميل"
    )
    # ✅✅✅ نهاية الإضافة ✅✅✅
    
    # الإعدادات
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
    
    # ✅ Methods للتحكم بحالة الاتصال (مثل العامل)
    def set_online(self):
        """تعيين العميل كمتصل"""
        self.is_online = True
        self.save(update_fields=['is_online', 'last_seen'])
    
    def set_offline(self):
        """تعيين العميل كغير متصل"""
        self.is_online = False
        self.save(update_fields=['is_online'])
    
    def update_activity(self):
        """تحديث آخر نشاط للعميل"""
        from django.utils import timezone
        self.last_seen = timezone.now()
        self.save(update_fields=['last_seen'])
    
    @property
    def success_rate(self):
        if self.total_tasks_published == 0:
            return 0.0
        return round(
            (self.total_tasks_completed / self.total_tasks_published) * 100, 
            1
        )
    
class SavedLocation(models.Model):
    """
    المواقع المحفوظة للمستخدمين (عميل/عامل)
    يتم حفظ المواقع تلقائياً عند نشر مهمة بموقع GPS
    """
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='saved_locations',
        help_text="المستخدم صاحب الموقع"
    )
    
    # اسم الموقع (اختياري - يمكن للمستخدم تسميته)
    name = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        help_text="اسم مخصص مثل: المنزل، المكتب، محل أمي"
    )
    
    # العنوان الكامل
    address = models.CharField(
        max_length=300,
        help_text="العنوان الكامل مثل: Tevragh Zeina, Nouakchott"
    )
    
    # الإحداثيات
    latitude = models.DecimalField(
        max_digits=10, 
        decimal_places=7,
        help_text="خط العرض"
    )
    longitude = models.DecimalField(
        max_digits=11, 
        decimal_places=7,
        help_text="خط الطول"
    )
    
    # الإيموجي (اختياري)
    emoji = models.CharField(
        max_length=10, 
        blank=True, 
        default='📍',
        help_text="إيموجي اختياري للموقع"
    )
    
    # إحصائيات الاستخدام
    usage_count = models.PositiveIntegerField(
        default=1,
        help_text="عدد مرات استخدام هذا الموقع"
    )
    last_used_at = models.DateTimeField(
        auto_now=True,
        help_text="آخر مرة استخدم فيها هذا الموقع"
    )
    
    # تواريخ
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Saved Location"
        verbose_name_plural = "Saved Locations"
        ordering = ['-usage_count', '-last_used_at']  # الأكثر استخداماً أولاً
        unique_together = ['user', 'latitude', 'longitude']  # منع التكرار
        indexes = [
            models.Index(fields=['user', '-usage_count']),  # تسريع الاستعلامات
            models.Index(fields=['user', '-last_used_at']),
        ]
    
    def __str__(self):
        if self.name:
            return f"{self.emoji} {self.name} - {self.user.get_full_name()}"
        return f"{self.emoji} {self.address[:30]}... - {self.user.get_full_name()}"