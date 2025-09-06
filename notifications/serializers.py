# notifications/serializers.py
from rest_framework import serializers
from django.utils import timezone
from .models import Notification, NotificationSettings, NotificationTemplate
from .utils import get_user_language


class NotificationSerializer(serializers.ModelSerializer):
    """
    محول الإشعارات مع الترجمة التلقائية
    Notification serializer with automatic translation
    """
    # الحقول المترجمة
    title = serializers.SerializerMethodField()
    message = serializers.SerializerMethodField()
    
    # معلومات إضافية
    time_ago = serializers.SerializerMethodField()
    is_expired = serializers.ReadOnlyField()
    recipient_role = serializers.ReadOnlyField()
    
    # معلومات المهمة المرتبطة
    task_title = serializers.SerializerMethodField()
    task_id = serializers.SerializerMethodField()
    
    # معلومات العامل المرتبط
    worker_name = serializers.SerializerMethodField()
    worker_id = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'title', 'message', 'is_read',
            'priority', 'time_ago', 'is_expired', 'recipient_role',
            'task_title', 'task_id', 'worker_name', 'worker_id',
            'created_at', 'read_at'
        ]
        read_only_fields = [
            'id', 'notification_type', 'title', 'message', 'priority',
            'time_ago', 'is_expired', 'recipient_role', 'task_title',
            'task_id', 'worker_name', 'worker_id', 'created_at'
        ]
    
    def get_title(self, obj):
        """الحصول على العنوان المترجم"""
        language = self._get_user_language(obj)
        content = obj.get_localized_content(language)
        return content['title']
    
    def get_message(self, obj):
        """الحصول على الرسالة المترجمة"""
        language = self._get_user_language(obj)
        content = obj.get_localized_content(language)
        return content['message']
    
    def get_time_ago(self, obj):
        """الحصول على الوقت المنقضي بالفرنسية"""
        now = timezone.now()
        diff = now - obj.created_at
        
        if diff.total_seconds() < 60:
            return 'maintenant'
        elif diff.total_seconds() < 3600:
            minutes = int(diff.total_seconds() / 60)
            return f'{minutes}min'
        elif diff.total_seconds() < 86400:
            hours = int(diff.total_seconds() / 3600)
            return f'{hours}h'
        elif diff.days == 1:
            return '1 jour'
        elif diff.days < 7:
            return f'{diff.days} jours'
        elif diff.days < 30:
            weeks = diff.days // 7
            return f'{weeks} semaine{"s" if weeks > 1 else ""}'
        elif diff.days < 365:
            months = diff.days // 30
            return f'{months} mois'
        else:
            years = diff.days // 365
            return f'{years} an{"s" if years > 1 else ""}'
    
    def get_task_title(self, obj):
        """الحصول على عنوان المهمة المرتبطة"""
        return obj.related_task.title if obj.related_task else None
    
    def get_task_id(self, obj):
        """الحصول على رقم المهمة المرتبطة"""
        return obj.related_task.id if obj.related_task else None
    
    def get_worker_name(self, obj):
        """الحصول على اسم العامل المرتبط"""
        if obj.related_worker:
            user = obj.related_worker.profile.user
            if user.first_name and user.last_name:
                return f"{user.first_name} {user.last_name}"
            return user.username
        return None
    
    def get_worker_id(self, obj):
        """الحصول على رقم العامل المرتبط"""
        return obj.related_worker.id if obj.related_worker else None
    
    def _get_user_language(self, obj):
        """الحصول على لغة المستخدم"""
        from .utils import get_user_language
        return get_user_language(obj.recipient)


class NotificationListSerializer(NotificationSerializer):
    """
    محول مبسط لقائمة الإشعارات
    Simplified serializer for notification list
    """
    class Meta(NotificationSerializer.Meta):
        fields = [
            'id', 'notification_type', 'title', 'message', 'is_read',
            'priority', 'time_ago', 'worker_name', 'created_at'
        ]


class NotificationSettingsSerializer(serializers.ModelSerializer):
    """
    محول إعدادات الإشعارات
    Notification settings serializer
    """
    class Meta:
        model = NotificationSettings
        fields = [
            'notifications_enabled', 'task_notifications', 
            'message_notifications', 'payment_notifications',
            'quiet_hours_start', 'quiet_hours_end'
        ]
    
    def __init__(self, *args, **kwargs):
        """تفعيل التحديث الجزئي"""
        super().__init__(*args, **kwargs)
        self.partial = True
        
        for field_name, field in self.fields.items():
            field.required = False
    
    def update(self, instance, validated_data):
        """تحديث الإعدادات مع دعم التحديث الجزئي"""
        for attr, value in validated_data.items():
            if value is not None:
                setattr(instance, attr, value)
        instance.save()
        return instance


class NotificationStatsSerializer(serializers.Serializer):
    """
    محول إحصائيات الإشعارات
    Notification statistics serializer
    """
    total_notifications = serializers.IntegerField(read_only=True)
    unread_notifications = serializers.IntegerField(read_only=True)
    read_notifications = serializers.IntegerField(read_only=True)
    notifications_today = serializers.IntegerField(read_only=True)
    notifications_this_week = serializers.IntegerField(read_only=True)
    
    # إحصائيات حسب النوع
    task_notifications = serializers.IntegerField(read_only=True)
    message_notifications = serializers.IntegerField(read_only=True)
    payment_notifications = serializers.IntegerField(read_only=True)
    
    # إحصائيات حسب الأولوية
    high_priority = serializers.IntegerField(read_only=True)
    medium_priority = serializers.IntegerField(read_only=True)
    low_priority = serializers.IntegerField(read_only=True)


class NotificationTemplateSerializer(serializers.ModelSerializer):
    """
    محول قوالب الإشعارات
    Notification template serializer
    """
    class Meta:
        model = NotificationTemplate
        fields = [
            'id', 'notification_type', 'title_fr', 'message_fr',
            'title_ar', 'message_ar', 'title_en', 'message_en',
            'template_variables', 'is_active'
        ]
    
    def validate_template_variables(self, value):
        """التحقق من صحة متغيرات القالب"""
        if not isinstance(value, list):
            raise serializers.ValidationError("Template variables must be a list")
        return value


class BulkNotificationSerializer(serializers.Serializer):
    """
    محول الإشعارات المجمعة
    Bulk notification serializer
    """
    notification_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="قائمة رقم الإشعارات"
    )
    
    action = serializers.ChoiceField(
        choices=[
            ('mark_read', 'Marquer comme lu'),
            ('mark_unread', 'Marquer comme non lu'),
            ('delete', 'Supprimer'),
        ],
        help_text="الإجراء المطلوب"
    )
    
    def validate_notification_ids(self, value):
        """التحقق من وجود الإشعارات"""
        if not value:
            raise serializers.ValidationError("Au moins un ID de notification est requis")
        
        # التحقق من وجود الإشعارات
        user = self.context['request'].user.profile
        existing_ids = Notification.objects.filter(
            id__in=value,
            recipient=user
        ).values_list('id', flat=True)
        
        missing_ids = set(value) - set(existing_ids)
        if missing_ids:
            raise serializers.ValidationError(
                f"Notifications non trouvées: {list(missing_ids)}"
            )
        
        return value


class NotificationCreateSerializer(serializers.Serializer):
    """
    محول إنشاء إشعار جديد (للإدارة)
    Create notification serializer (for admin)
    """
    recipient_id = serializers.IntegerField(help_text="رقم المستلم")
    notification_type = serializers.ChoiceField(
        choices=Notification.ALL_NOTIFICATION_TYPES,
        help_text="نوع الإشعار"
    )
    context_data = serializers.JSONField(
        default=dict,
        help_text="بيانات السياق"
    )
    priority = serializers.ChoiceField(
        choices=Notification.PRIORITY_CHOICES,
        default='medium',
        help_text="أولوية الإشعار"
    )
    expires_at = serializers.DateTimeField(
        required=False,
        help_text="تاريخ انتهاء الصلاحية"
    )
    
    def validate_recipient_id(self, value):
        """التحقق من وجود المستلم"""
        from accounts.models import Profile
        try:
            Profile.objects.get(id=value)
            return value
        except Profile.DoesNotExist:
            raise serializers.ValidationError("Utilisateur non trouvé")
    
    def create(self, validated_data):
        """إنشاء إشعار جديد"""
        from accounts.models import Profile
        
        recipient = Profile.objects.get(id=validated_data['recipient_id'])
        
        return Notification.objects.create(
            recipient=recipient,
            notification_type=validated_data['notification_type'],
            title_key=f"notifications.{validated_data['notification_type']}.title",
            message_key=f"notifications.{validated_data['notification_type']}.message",
            context_data=validated_data.get('context_data', {}),
            priority=validated_data.get('priority', 'medium'),
            expires_at=validated_data.get('expires_at')
        )