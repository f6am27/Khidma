# users/managers.py
from django.contrib.auth.models import BaseUserManager


class UserManager(BaseUserManager):
    """
    مدير مخصص للمستخدمين
    يدعم إنشاء مستخدمين بـ phone أو email حسب الدور
    """
    
    def _create_user(self, identifier, password, role='client', **extra_fields):
        """
        إنشاء مستخدم مع phone أو email حسب الدور
        """
        if not identifier:
            raise ValueError('The identifier (phone/email) must be set')
        
        # تحديد نوع المعرف حسب الدور
        if role == 'admin':
            if '@' not in identifier:
                raise ValueError('Admin users must use email')
            email = self.normalize_email(identifier)
            # للأدمن: استخدام email في User مباشرة، بدون phone
            user = self.model(email=email, phone=None, role=role, **extra_fields)
        else:
            # client or worker: استخدام phone فقط، email فارغ
            user = self.model(phone=identifier, email=None, role=role, **extra_fields)
        
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_user(self, identifier, password=None, role='client', **extra_fields):
        """إنشاء مستخدم عادي"""
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(identifier, password, role, **extra_fields)
    
    def create_superuser(self, email=None, password=None, **extra_fields):
        """إنشاء مستخدم فائق (admin)"""
        if not email:
            raise ValueError('Superuser must have email')
        
        # إزالة role إذا كان موجود في extra_fields لتجنب التضارب
        extra_fields.pop('role', None)
            
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_verified', True)  # الأدمن محقق تلقائياً
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self._create_user(email, password, 'admin', **extra_fields)
    
    def create_client(self, phone, password, **extra_fields):
        """إنشاء عميل"""
        extra_fields.setdefault('role', 'client')
        return self.create_user(phone, password, 'client', **extra_fields)
    
    def create_worker(self, phone, password, **extra_fields):
        """إنشاء عامل"""
        extra_fields.setdefault('role', 'worker')
        return self.create_user(phone, password, 'worker', **extra_fields)
    
    def create_admin(self, email, password, **extra_fields):
        """إنشاء أدمن"""
        extra_fields.setdefault('role', 'admin')
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_verified', True)  # الأدمن محقق تلقائياً
        return self.create_user(email, password, 'admin', **extra_fields)