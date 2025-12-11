# complaints/serializers.py
from rest_framework import serializers
from .models import Complaint
from users.models import User
from django.utils import timezone



class ComplaintListSerializer(serializers.ModelSerializer):
    """
    Serializer لقائمة الشكاوى (للأدمن)
    """
    user_name = serializers.SerializerMethodField()
    user_phone = serializers.SerializerMethodField()
    user_role = serializers.CharField(source='user.role', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    
    # ✅ إضافة رابط الصوت
    audio_file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Complaint
        fields = [
            'id', 'user', 'user_name', 'user_phone', 'user_role',
            'type', 'type_display', 'category', 'category_display',
            'status', 'status_display', 'priority', 'priority_display',
            'description', 'audio_file_url', 'audio_duration',  # ✅ تمت الإضافة
            'created_at', 'resolved_at', 'admin_notes'
        ]
        read_only_fields = ['id', 'created_at', 'resolved_at']
    
    def get_user_name(self, obj):
        """اسم المستخدم"""
        return obj.user.get_full_name() or obj.user.phone
    
    def get_user_phone(self, obj):
        """رقم هاتف المستخدم"""
        return obj.user.phone
    
    # ✅ إضافة دالة رابط الصوت
    def get_audio_file_url(self, obj):
        """رابط الملف الصوتي"""
        if obj.audio_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.audio_file.url)
        return None


class ComplaintDetailSerializer(serializers.ModelSerializer):
    """
    Serializer لتفاصيل الشكوى (للأدمن)
    """
    user_name = serializers.SerializerMethodField()
    user_phone = serializers.SerializerMethodField()
    user_role = serializers.CharField(source='user.role', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    
    resolved_by_name = serializers.SerializerMethodField()
    audio_file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Complaint
        fields = [
            'id', 'user', 'user_name', 'user_phone', 'user_email', 'user_role',
            'type', 'type_display', 'category', 'category_display',
            'description', 'audio_file', 'audio_file_url', 'audio_duration',
            'status', 'status_display', 'priority', 'priority_display',
            'resolved_by', 'resolved_by_name', 'admin_notes',
            'created_at', 'resolved_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'resolved_at', 'updated_at']
    
    def get_user_name(self, obj):
        """اسم المستخدم الكامل"""
        return obj.user.get_full_name() or obj.user.phone
    
    def get_user_phone(self, obj):
        """رقم هاتف المستخدم"""
        return obj.user.phone
    
    def get_resolved_by_name(self, obj):
        """اسم الأدمن الذي حل الشكوى"""
        if obj.resolved_by:
            return obj.resolved_by.get_full_name() or obj.resolved_by.email
        return None
    
    def get_audio_file_url(self, obj):
        """رابط الملف الصوتي"""
        if obj.audio_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.audio_file.url)
            return obj.audio_file.url
        return None


class ComplaintCreateSerializer(serializers.ModelSerializer):
    """
    Serializer لإنشاء شكوى (للمستخدمين)
    """
    class Meta:
        model = Complaint
        fields = [
            'category', 'description', 'audio_file', 'audio_duration'
        ]
        extra_kwargs = {
            'description': {'required': False, 'allow_blank': True},
            'audio_file': {'required': False, 'allow_null': True},
            'audio_duration': {'required': False, 'allow_null': True},
        }
    
    def validate(self, data):
        """التحقق من وجود إما نص أو صوت"""
        description = data.get('description')
        audio_file = data.get('audio_file')
        
        if not description and not audio_file:
            raise serializers.ValidationError(
                "يجب تقديم وصف نصي أو تسجيل صوتي على الأقل"
            )
        
        # التحقق من حجم الملف الصوتي
        if audio_file and audio_file.size > 10 * 1024 * 1024:  # 10MB
            raise serializers.ValidationError(
                "حجم الملف الصوتي يجب أن لا يتجاوز 10MB"
            )
        
        # التحقق من مدة التسجيل
        audio_duration = data.get('audio_duration')
        if audio_file and audio_duration:
            if audio_duration > 180:  # 3 دقائق
                raise serializers.ValidationError(
                    "مدة التسجيل يجب أن لا تتجاوز 3 دقائق"
                )
        
        return data
    
    def create(self, validated_data):
        """إنشاء الشكوى"""
        request = self.context.get('request')
        user = request.user
        
        complaint = Complaint.objects.create(
            user=user,
            **validated_data
        )
        
        return complaint


class ComplaintUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer لتحديث حالة الشكوى (للأدمن فقط)
    """
    class Meta:
        model = Complaint
        fields = ['status', 'priority', 'admin_notes']
    
    def update(self, instance, validated_data):
        """تحديث الشكوى"""
        request = self.context.get('request')
        
        # إذا تم تغيير الحالة إلى محلول/مغلق
        new_status = validated_data.get('status')
        if new_status in ['resolved', 'closed'] and instance.status not in ['resolved', 'closed']:
            instance.resolved_by = request.user
            instance.resolved_at = timezone.now()
        
        return super().update(instance, validated_data)


class UserComplaintSerializer(serializers.ModelSerializer):
    """
    Serializer لعرض شكاوى المستخدم الخاصة
    """
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    audio_file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Complaint
        fields = [
            'id', 'type', 'type_display', 'category', 'category_display',
            'description', 'audio_file_url', 'audio_duration',
            'status', 'status_display', 'admin_notes',
            'created_at', 'resolved_at'
        ]
        read_only_fields = ['id', 'created_at', 'resolved_at']
    
    def get_audio_file_url(self, obj):
        """رابط الملف الصوتي"""
        if obj.audio_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.audio_file.url)
            return obj.audio_file.url
        return None