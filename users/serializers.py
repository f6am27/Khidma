# users/serializers.py
from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, WorkerProfile, ClientProfile, AdminProfile
from .utils import to_e164


class RegisterSerializer(serializers.Serializer):
    """
    تسجيل مستخدم جديد (عميل أو عامل)
    """
    username = serializers.CharField(min_length=3, max_length=150)
    phone = serializers.CharField(min_length=8, max_length=25)
    password = serializers.CharField(min_length=6, max_length=128, write_only=True)
    role = serializers.ChoiceField(choices=['client', 'worker'], default='client')
    lang = serializers.ChoiceField(choices=['ar', 'fr'], default='ar', required=False)

    def validate_phone(self, value):
        """التحقق من صحة رقم الهاتف"""
        try:
            phone_e164 = to_e164(value)
            
            # التحقق من عدم وجود المستخدم مسبقاً
            if User.objects.filter(phone=phone_e164).exists():
                raise serializers.ValidationError("User with this phone already exists")
            
            return phone_e164
        except ValueError as e:
            raise serializers.ValidationError(str(e))


class VerifySerializer(serializers.Serializer):
    """
    التحقق من رمز OTP
    """
    phone = serializers.CharField()
    code = serializers.CharField(min_length=4, max_length=6)

    def validate_phone(self, value):
        """التحقق من صحة رقم الهاتف"""
        try:
            return to_e164(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))


class LoginSerializer(serializers.Serializer):
    """
    تسجيل الدخول
    """
    phone_or_username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        """التحقق من بيانات تسجيل الدخول"""
        identifier = attrs.get('phone_or_username')
        password = attrs.get('password')

        if not identifier or not password:
            raise serializers.ValidationError("Phone/username and password required")

        user = None
        
        # محاولة التحقق من أنه رقم هاتف
        try:
            phone_e164 = to_e164(identifier)
            # البحث عن المستخدم بالهاتف
            try:
                user = User.objects.get(phone=phone_e164)
            except User.DoesNotExist:
                pass  # لم يجد بالهاتف، سيجرب first_name
        except ValueError:
            # ليس رقم هاتف صالح
            pass
        
        # إذا لم يجد بالهاتف، جرب first_name
        if not user:
            try:
                user = User.objects.get(first_name=identifier)
            except User.DoesNotExist:
                pass
        
        # إذا لم يجد المستخدم بأي طريقة
        if not user:
            raise serializers.ValidationError("Invalid credentials")

        # التحقق من كلمة المرور
        if not user.check_password(password):
            raise serializers.ValidationError("Invalid credentials")

        if not user.is_active:
            raise serializers.ValidationError("User account is disabled")

        attrs['user'] = user
        return attrs
    
class ResendOTPSerializer(serializers.Serializer):
    """
    إعادة إرسال رمز OTP
    """
    phone = serializers.CharField()
    lang = serializers.ChoiceField(choices=['ar', 'fr'], default='ar', required=False)

    def validate_phone(self, value):
        """التحقق من صحة رقم الهاتف"""
        try:
            return to_e164(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))


class PasswordResetStartSerializer(serializers.Serializer):
    """
    بدء إعادة تعيين كلمة المرور
    """
    phone = serializers.CharField()
    lang = serializers.ChoiceField(choices=['ar', 'fr'], default='ar', required=False)

    def validate_phone(self, value):
        """التحقق من وجود المستخدم"""
        try:
            phone_e164 = to_e164(value)
            
            # التحقق من وجود المستخدم
            if not User.objects.filter(phone=phone_e164).exists():
                raise serializers.ValidationError("User with this phone does not exist")
            
            return phone_e164
        except ValueError as e:
            raise serializers.ValidationError(str(e))


class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    تأكيد إعادة تعيين كلمة المرور
    """
    phone = serializers.CharField()
    code = serializers.CharField(min_length=4, max_length=6)
    new_password = serializers.CharField(min_length=6, max_length=128, write_only=True)
    new_password_confirm = serializers.CharField(min_length=6, max_length=128, write_only=True)

    def validate_phone(self, value):
        """التحقق من صحة رقم الهاتف"""
        try:
            return to_e164(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))

    def validate(self, attrs):
        """التحقق من تطابق كلمات المرور"""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("Passwords do not match")
        return attrs


class UserSerializer(serializers.ModelSerializer):
    """
    عرض بيانات المستخدم
    """
    display_identifier = serializers.CharField(read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'first_name', 'last_name', 'display_identifier', 
            'role', 'is_verified', 'onboarding_completed', 'created_at'
        ]
        read_only_fields = ['id', 'role', 'is_verified', 'onboarding_completed', 'created_at']


class WorkerProfileSerializer(serializers.ModelSerializer):
    """
    ملف العامل
    """
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = WorkerProfile
        fields = '__all__'
        read_only_fields = ['user', 'total_jobs_completed', 'average_rating', 'total_reviews']


class ClientProfileSerializer(serializers.ModelSerializer):
    """
    ملف العميل
    """
    user = UserSerializer(read_only=True)
    success_rate = serializers.FloatField(read_only=True)
    
    class Meta:
        model = ClientProfile
        fields = '__all__'
        read_only_fields = ['user', 'total_tasks_published', 'total_tasks_completed', 'total_amount_spent']

# إضافة هذه الـ Serializers إلى ملف users/serializers.py الموجود

class WorkerProfileUpdateSerializer(serializers.ModelSerializer):
    """
    تحديث ملف العامل
    """
    # حقول من User
    first_name = serializers.CharField(source='user.first_name', max_length=150)
    last_name = serializers.CharField(source='user.last_name', max_length=150, required=False, allow_blank=True)
    
    class Meta:
        model = WorkerProfile
        fields = [
            'first_name', 'last_name', 'bio', 'service_area', 
            'service_category', 'base_price', 'available_days',
            'work_start_time', 'work_end_time', 'is_available'
        ]
    
    def update(self, instance, validated_data):
        # استخراج بيانات User
        user_data = validated_data.pop('user', {})
        
        # تحديث بيانات User
        if user_data:
            user = instance.user
            for key, value in user_data.items():
                setattr(user, key, value)
            user.save()
        
        # تحديث بيانات WorkerProfile
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        
        return instance


class ClientProfileUpdateSerializer(serializers.ModelSerializer):
    """
    تحديث ملف العميل
    """
    # حقول من User
    first_name = serializers.CharField(source='user.first_name', max_length=150)
    last_name = serializers.CharField(source='user.last_name', max_length=150, required=False, allow_blank=True)
    
    class Meta:
        model = ClientProfile
        fields = [
            'first_name', 'last_name', 'bio', 'date_of_birth',
            'gender', 'address', 'emergency_contact', 'preferred_language',
            'notifications_enabled'
        ]
    
    def update(self, instance, validated_data):
        # استخراج بيانات User
        user_data = validated_data.pop('user', {})
        
        # تحديث بيانات User
        if user_data:
            user = instance.user
            for key, value in user_data.items():
                setattr(user, key, value)
            user.save()
        
        # تحديث بيانات ClientProfile
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        
        return instance


class WorkerOnboardingSerializer(serializers.ModelSerializer):
    """
    إكمال Onboarding للعامل
    """
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name', required=False, allow_blank=True)
    
    class Meta:
        model = WorkerProfile
        fields = [
            'first_name', 'last_name', 'bio', 'service_area',
            'service_category', 'base_price', 'available_days',
            'work_start_time', 'work_end_time'
        ]
    
    def create(self, validated_data):
        user_data = validated_data.pop('user', {})
        user = self.context['request'].user
        
        # تحديث بيانات User
        for key, value in user_data.items():
            setattr(user, key, value)
        user.onboarding_completed = True
        user.save()
        
        # إنشاء WorkerProfile
        worker_profile = WorkerProfile.objects.create(
            user=user,
            **validated_data
        )
        
        return worker_profile


class LocationUpdateSerializer(serializers.Serializer):
    """
    تحديث موقع العامل
    """
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    accuracy = serializers.FloatField(required=False, allow_null=True)


class LocationSharingToggleSerializer(serializers.Serializer):
    """
    تفعيل/إلغاء تفعيل مشاركة الموقع
    """
    enabled = serializers.BooleanField()