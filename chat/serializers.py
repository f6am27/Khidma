# chat/serializers.py
from rest_framework import serializers
from django.utils import timezone
from django.db.models import Q
from .models import Conversation, Message, BlockedUser, Report
from users.models import User


class UserProfileSerializer(serializers.ModelSerializer):
    """
    معلومات المستخدم للمحادثات
    User profile info for chat
    """
    full_name = serializers.SerializerMethodField()
    profile_image_url = serializers.SerializerMethodField()
    is_online = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'full_name', 'role', 'profile_image_url', 'is_online']
    
    def get_full_name(self, obj):
        """الحصول على الاسم الكامل"""
        if obj.first_name and obj.last_name:
            return f"{obj.first_name} {obj.last_name}"
        return obj.username
    
    def get_profile_image_url(self, obj):
        """الحصول على رابط صورة الملف الشخصي"""
        if hasattr(obj, 'client_profile') and obj.client_profile.profile_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.client_profile.profile_image.url)
            return obj.client_profile.profile_image.url
        elif hasattr(obj, 'worker_profile') and obj.worker_profile.profile_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.worker_profile.profile_image.url)
            return obj.worker_profile.profile_image.url
        return None
    
    def get_is_online(self, obj):
        """حالة الاتصال"""
        if obj.last_login:
            time_diff = timezone.now() - obj.last_login
            return time_diff.total_seconds() < 300  # 5 دقائق
        return False


class MessageSerializer(serializers.ModelSerializer):
    """
    محول الرسائل
    Message serializer
    """
    sender = UserProfileSerializer(read_only=True)
    is_from_me = serializers.SerializerMethodField()
    time_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = [
            'id', 'content', 'sender', 'is_from_me', 'is_read', 
            'created_at', 'read_at', 'time_ago'
        ]
        read_only_fields = ['id', 'sender', 'is_read', 'created_at', 'read_at']
    
    def get_is_from_me(self, obj):
        """هل الرسالة من المستخدم الحالي"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.sender == request.user
        return False
    
    def get_time_ago(self, obj):
        """الوقت المنقضي منذ الرسالة"""
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
            return 'hier'
        elif diff.days < 7:
            return f'{diff.days}j'
        else:
            return f'{obj.created_at.day}/{obj.created_at.month}'


class ConversationSerializer(serializers.ModelSerializer):
    """
    محول المحادثات
    Conversation serializer
    """
    other_participant = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    time_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'other_participant', 'last_message', 'unread_count',
            'total_messages', 'time_ago', 'created_at', 'last_message_at'
        ]
        read_only_fields = ['id', 'total_messages', 'created_at', 'last_message_at']
    
    def get_other_participant(self, obj):
        """المشارك الآخر في المحادثة"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            current_user = request.user
            if current_user == obj.client:
                return UserProfileSerializer(obj.worker, context=self.context).data
            else:
                return UserProfileSerializer(obj.client, context=self.context).data
        return None
    
    def get_last_message(self, obj):
        """آخر رسالة في المحادثة"""
        last_message = obj.last_message
        if last_message:
            return {
                'content': last_message.content,
                'sender_name': last_message.sender.get_full_name() or last_message.sender.username,
                'is_from_me': last_message.sender == self.context.get('request').user,
                'created_at': last_message.created_at
            }
        return None
    
    def get_unread_count(self, obj):
        """عدد الرسائل غير المقروءة"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.get_unread_count(request.user)
        return 0
    
    def get_time_ago(self, obj):
        """الوقت المنقضي منذ آخر رسالة"""
        if obj.last_message_at:
            now = timezone.now()
            diff = now - obj.last_message_at
            
            if diff.total_seconds() < 60:
                return 'maintenant'
            elif diff.total_seconds() < 3600:
                minutes = int(diff.total_seconds() / 60)
                return f'{minutes}min'
            elif diff.total_seconds() < 86400:
                hours = int(diff.total_seconds() / 3600)
                return f'{hours}h'
            elif diff.days == 1:
                return 'hier'
            elif diff.days < 7:
                return f'{diff.days}j'
            else:
                return f'{obj.last_message_at.day}/{obj.last_message_at.month}'
        return 'Aucun message'


class SendMessageSerializer(serializers.ModelSerializer):
    """
    محول إرسال الرسائل
    Send message serializer
    """
    class Meta:
        model = Message
        fields = ['content']
    
    def validate_content(self, value):
        """التحقق من محتوى الرسالة"""
        if not value or not value.strip():
            raise serializers.ValidationError("Le message ne peut pas être vide")
        
        if len(value.strip()) > 1000:
            raise serializers.ValidationError("Le message est trop long")
        
        return value.strip()


class ReportSerializer(serializers.ModelSerializer):
    """
    محول التبليغات
    Report serializer
    """
    reporter = UserProfileSerializer(read_only=True)
    reported_user = UserProfileSerializer(read_only=True)
    reason_display = serializers.CharField(source='get_reason_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Report
        fields = [
            'id', 'reporter', 'reported_user', 'reason', 'reason_display',
            'description', 'status', 'status_display', 'admin_notes',
            'created_at', 'resolved_at'
        ]
        read_only_fields = [
            'id', 'reporter', 'status', 'admin_notes', 'created_at', 'resolved_at'
        ]


class CreateReportSerializer(serializers.ModelSerializer):
    """
    محول إنشاء تبليغ
    Create report serializer
    """
    reported_user_id = serializers.IntegerField(write_only=True)
    conversation_id = serializers.IntegerField(write_only=True, required=False)
    
    class Meta:
        model = Report
        fields = ['reported_user_id', 'conversation_id', 'reason', 'description']
    
    def validate_reported_user_id(self, value):
        """التحقق من المستخدم المُبلَّغ عنه"""
        try:
            user = User.objects.get(id=value)
            request = self.context.get('request')
            
            if user == request.user:
                raise serializers.ValidationError("Vous ne pouvez pas vous signaler vous-même")
            
            return value
            
        except User.DoesNotExist:
            raise serializers.ValidationError("Utilisateur non trouvé")
    
    def create(self, validated_data):
        """إنشاء التبليغ"""
        request = self.context.get('request')
        reported_user_id = validated_data.pop('reported_user_id')
        conversation_id = validated_data.pop('conversation_id', None)
        
        return Report.objects.create(
            reporter=request.user,
            reported_user_id=reported_user_id,
            conversation_id=conversation_id,
            **validated_data
        )


class BlockUserSerializer(serializers.ModelSerializer):
    """
    محول حظر المستخدمين
    Block user serializer
    """
    blocked_user_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = BlockedUser
        fields = ['blocked_user_id', 'reason']
        extra_kwargs = {
            'reason': {'required': False}
        }
    
    def validate_blocked_user_id(self, value):
        """التحقق من المستخدم المحظور"""
        try:
            user = User.objects.get(id=value)
            request = self.context.get('request')
            
            if user == request.user:
                raise serializers.ValidationError("Vous ne pouvez pas vous bloquer vous-même")
            
            if BlockedUser.objects.filter(
                blocker=request.user,
                blocked=user
            ).exists():
                raise serializers.ValidationError("Cet utilisateur est déjà bloqué")
            
            return value
            
        except User.DoesNotExist:
            raise serializers.ValidationError("Utilisateur non trouvé")
    
    def create(self, validated_data):
        """إنشاء الحظر"""
        request = self.context.get('request')
        blocked_user_id = validated_data.pop('blocked_user_id')
        
        return BlockedUser.objects.create(
            blocker=request.user,
            blocked_id=blocked_user_id,
            **validated_data
        )