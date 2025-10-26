# notifications/serializers.py
from rest_framework import serializers
from django.utils import timezone
from .models import Notification, NotificationSettings
from users.models import User


class NotificationSerializer(serializers.ModelSerializer):
    """
    محول الإشعارات مع نصوص مباشرة
    Notification serializer with direct text
    """
    # معلومات إضافية
    time_ago = serializers.SerializerMethodField()
    recipient_role = serializers.SerializerMethodField()     
    # معلومات المهمة المرتبطة
    task_title = serializers.SerializerMethodField()
    task_id = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'title', 'message', 'is_read',
            'time_ago', 'recipient_role', 'task_title', 'task_id',
            'created_at', 'read_at'
        ]
        read_only_fields = [
            'id', 'notification_type', 'title', 'message',
            'time_ago', 'recipient_role', 'task_title',
            'task_id', 'created_at'
        ]
    
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
    
    def get_recipient_role(self, obj):
        """الحصول على دور المستلم"""
        return obj.recipient.role if obj.recipient else 'client'


class NotificationListSerializer(NotificationSerializer):
    """
    محول مبسط لقائمة الإشعارات
    Simplified serializer for notification list
    """
    class Meta(NotificationSerializer.Meta):
        fields = [
            'id', 'notification_type', 'title', 'message', 'is_read',
            'time_ago', 'created_at'
        ]


class NotificationSettingsSerializer(serializers.ModelSerializer):
    """
    محول إعدادات الإشعارات - مبسط
    Notification settings serializer - simplified
    """
    class Meta:
        model = NotificationSettings
        fields = ['notifications_enabled']
    
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
        user = self.context['request'].user
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
    title = serializers.CharField(max_length=200, help_text="عنوان الإشعار")
    message = serializers.CharField(help_text="محتوى الإشعار")
    
    def validate_recipient_id(self, value):
        """التحقق من وجود المستلم"""
        try:
            User.objects.get(id=value)
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError("Utilisateur non trouvé")
    
    def create(self, validated_data):
        """إنشاء إشعار جديد"""
        recipient = User.objects.get(id=validated_data['recipient_id'])
        
        return Notification.objects.create(
            recipient=recipient,
            notification_type=validated_data['notification_type'],
            title=validated_data['title'],
            message=validated_data['message']
        )