# payments/serializers.py
"""
Serializers لنظام الدفع والاشتراكات
عرض بيانات عداد المهام والاشتراكات
"""

from rest_framework import serializers
from .models import UserTaskCounter, PlatformSubscription


class UserTaskCounterSerializer(serializers.ModelSerializer):
    """
    عرض معلومات عداد المهام للمستخدم
    """
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    user_phone = serializers.CharField(source='user.phone', read_only=True)
    user_name = serializers.SerializerMethodField()
    
    # حقول محسوبة
    tasks_remaining = serializers.IntegerField(
        source='tasks_remaining_before_payment',
        read_only=True
    )
    needs_subscription = serializers.BooleanField(
        source='needs_payment',
        read_only=True
    )
    
    # حالة العداد
    counter_status = serializers.SerializerMethodField()
    subscription_status = serializers.SerializerMethodField()
    
    class Meta:
        model = UserTaskCounter
        fields = [
            'id',
            'user_id',
            'user_phone',
            'user_name',
            'accepted_tasks_count',
            'tasks_remaining',
            'needs_subscription',
            'is_premium',
            'last_payment_date',
            'last_reset_date',
            'counter_status',
            'subscription_status',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_user_name(self, obj):
        """الحصول على اسم المستخدم"""
        user = obj.user
        if user.first_name and user.last_name:
            return f"{user.first_name} {user.last_name}"
        return user.username or user.phone
    
    def get_counter_status(self, obj):
        """حالة العداد (نص وصفي)"""
        FREE_LIMIT = 5
        remaining = FREE_LIMIT - obj.accepted_tasks_count
        
        if obj.is_premium:
            return {
                'status': 'premium',
                'message': 'مشترك - لا حدود',
                'message_fr': 'Premium - Illimité'
            }
        
        if remaining > 0:
            return {
                'status': 'active',
                'message': f'متبقي {remaining} مهام مجانية',
                'message_fr': f'{remaining} tâches gratuites restantes'
            }
        
        return {
            'status': 'limit_reached',
            'message': 'استنفدت الحد المجاني - اشتراك مطلوب',
            'message_fr': 'Limite atteinte - Abonnement requis'
        }
    
    def get_subscription_status(self, obj):
        """حالة الاشتراك"""
        if obj.is_premium:
            return {
                'is_active': True,
                'type': 'premium',
                'last_payment': obj.last_payment_date,
                'message': 'نشط',
                'message_fr': 'Actif'
            }
        
        return {
            'is_active': False,
            'type': 'free',
            'message': 'مجاني',
            'message_fr': 'Gratuit'
        }


class UserTaskCounterSimpleSerializer(serializers.ModelSerializer):
    """
    عرض مبسط لعداد المهام (للاستخدام في APIs أخرى)
    """
    tasks_remaining = serializers.IntegerField(
        source='tasks_remaining_before_payment',
        read_only=True
    )
    needs_subscription = serializers.BooleanField(
        source='needs_payment',
        read_only=True
    )
    
    class Meta:
        model = UserTaskCounter
        fields = [
            'accepted_tasks_count',
            'tasks_remaining',
            'needs_subscription',
            'is_premium'
        ]


class PlatformSubscriptionSerializer(serializers.ModelSerializer):
    """
    عرض معلومات الاشتراك الشهري
    """
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    user_phone = serializers.CharField(source='user.phone', read_only=True)
    user_name = serializers.SerializerMethodField()
    
    # حقول محسوبة
    is_active = serializers.SerializerMethodField()
    days_remaining = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    
    class Meta:
        model = PlatformSubscription
        fields = [
            'id',
            'user_id',
            'user_phone',
            'user_name',
            'amount',
            'payment_method',
            'transaction_id',
            'status',
            'status_display',
            'is_active',
            'valid_until',
            'days_remaining',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_user_name(self, obj):
        """الحصول على اسم المستخدم"""
        user = obj.user
        if user.first_name and user.last_name:
            return f"{user.first_name} {user.last_name}"
        return user.username or user.phone
    
    def get_is_active(self, obj):
        """هل الاشتراك نشط؟"""
        from django.utils import timezone
        if obj.status != 'completed':
            return False
        if not obj.valid_until:
            return False
        return obj.valid_until > timezone.now()
    
    def get_days_remaining(self, obj):
        """عدد الأيام المتبقية في الاشتراك"""
        from django.utils import timezone
        if not self.get_is_active(obj):
            return 0
        delta = obj.valid_until - timezone.now()
        return max(0, delta.days)
    
    def get_status_display(self, obj):
        """عرض الحالة بالعربية والفرنسية"""
        status_map = {
            'pending': {
                'ar': 'قيد الانتظار',
                'fr': 'En attente'
            },
            'completed': {
                'ar': 'مكتمل',
                'fr': 'Terminé'
            },
            'failed': {
                'ar': 'فشل',
                'fr': 'Échoué'
            }
        }
        return status_map.get(obj.status, {
            'ar': obj.status,
            'fr': obj.status
        })


class SubscriptionCreateSerializer(serializers.Serializer):
    """
    إنشاء اشتراك جديد (للمستقبل مع Benkily)
    """
    payment_method = serializers.ChoiceField(
        choices=['benkily', 'other'],
        default='benkily'
    )
    
    def validate(self, data):
        """التحقق من البيانات"""
        # يمكن إضافة تحققات إضافية هنا
        return data
    
    def create(self, validated_data):
        """
        إنشاء اشتراك جديد
        (سيتم ربطه مع Benkily لاحقاً)
        """
        from django.utils import timezone
        from datetime import timedelta
        
        user = self.context['request'].user
        
        # إنشاء اشتراك
        subscription = PlatformSubscription.objects.create(
            user=user,
            amount=800.00,  # 8 MRU
            payment_method=validated_data['payment_method'],
            status='pending',
            valid_until=timezone.now() + timedelta(days=30)
        )
        
        return subscription