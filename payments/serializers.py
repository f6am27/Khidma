# payments/serializers.py
"""
Serializers لنظام الدفع والاشتراكات
عرض بيانات عداد المهام والاشتراكات
"""

from rest_framework import serializers
from .models import UserTaskCounter, PlatformSubscription
from payments.models import TaskBundle  

class UserTaskCounterSerializer(serializers.ModelSerializer):
    """
    عرض معلومات عداد المهام للمستخدم - النظام الجديد
    """
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    user_phone = serializers.CharField(source='user.phone', read_only=True)
    user_name = serializers.SerializerMethodField()
    
    # حقول محسوبة
    current_limit = serializers.IntegerField(read_only=True)
    current_usage = serializers.IntegerField(read_only=True)
    tasks_remaining = serializers.IntegerField(read_only=True)
    needs_subscription = serializers.BooleanField(
        source='needs_payment',
        read_only=True
    )
    
    # الحزمة النشطة
    active_bundle = serializers.SerializerMethodField()
    
    # حالة العداد
    counter_status = serializers.SerializerMethodField()
    
    class Meta:
        model = UserTaskCounter
        fields = [
            'id',
            'user_id',
            'user_phone',
            'user_name',
            'free_tasks_used',
            'total_subscriptions',
            'current_limit',
            'current_usage',
            'tasks_remaining',
            'needs_subscription',
            'active_bundle',
            'counter_status',
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
    
    def get_active_bundle(self, obj):
        """معلومات الحزمة النشطة"""
        bundle = obj.get_active_bundle()
        if bundle:
            return {
                'id': bundle.id,
                'tasks_included': bundle.tasks_included,
                'tasks_used': bundle.tasks_used,
                'tasks_remaining': bundle.tasks_remaining,
                'purchased_at': bundle.purchased_at,
            }
        return None
    
    def get_counter_status(self, obj):
        """حالة العداد (نص وصفي)"""
        active_bundle = obj.get_active_bundle()
        
        if active_bundle:
            remaining = active_bundle.tasks_remaining
            return {
                'status': 'active_bundle',
                'message': f'لديك {remaining} مهام متبقية في الحزمة',
                'message_fr': f'Il vous reste {remaining} tâches dans le bundle',
                'type': 'paid'
            }
        
        elif obj.free_tasks_used < 5:
            remaining = 5 - obj.free_tasks_used
            return {
                'status': 'free_period',
                'message': f'متبقي {remaining} مهام مجانية',
                'message_fr': f'{remaining} tâches gratuites restantes',
                'type': 'free'
            }
        
        else:
            return {
                'status': 'limit_reached',
                'message': 'استنفدت الحد المجاني - يجب شراء حزمة',
                'message_fr': 'Limite atteinte - Achat de bundle requis',
                'type': 'needs_payment'
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
    
# ================================
# Serializers للنظام الجديد - TaskBundle
# ================================

class TaskBundleSerializer(serializers.ModelSerializer):
    """
    عرض معلومات حزمة المهام
    """
    user_phone = serializers.CharField(source='user.phone', read_only=True)
    user_name = serializers.SerializerMethodField()
    
    # حقول محسوبة
    is_exhausted = serializers.BooleanField(read_only=True)
    tasks_remaining = serializers.IntegerField(read_only=True)
    payment_status_display = serializers.CharField(
        source='get_moosyl_payment_status_display',
        read_only=True
    )
    
    class Meta:
        model = TaskBundle
        fields = [
            'id',
            'user_phone',
            'user_name',
            'bundle_type',
            'tasks_included',
            'tasks_used',
            'tasks_remaining',
            'is_exhausted',
            'payment_amount',
            'payment_method',
            'moosyl_transaction_id',
            'moosyl_payment_status',
            'payment_status_display',
            'is_active',
            'purchased_at',
            'completed_at',
        ]
        read_only_fields = ['id', 'purchased_at', 'completed_at']
    
    def get_user_name(self, obj):
        user = obj.user
        if user.first_name and user.last_name:
            return f"{user.first_name} {user.last_name}"
        return user.username or user.phone


class TaskBundleCreateSerializer(serializers.Serializer):
    """
    شراء حزمة جديدة عبر Moosyl
    """
    # سيتم استخدامه في API شراء الحزمة
    # الحقول ستأتي من Moosyl بعد قراءة التوثيق
    
    def validate(self, data):
        """التحقق من البيانات"""
        user = self.context['request'].user
        
        # التحقق: هل يحتاج فعلاً للشراء؟
        counter, _ = UserTaskCounter.objects.get_or_create(user=user)
        if not counter.needs_payment:
            raise serializers.ValidationError({
                'error': 'لا تحتاج لشراء حزمة الآن',
                'tasks_remaining': counter.tasks_remaining
            })
        
        return data


# ================================
# Serializer لشراء حزمة عبر Moosyl
# ================================

class PurchaseBundleSerializer(serializers.Serializer):
    """
    بدء عملية شراء حزمة (8 مهام بـ 5 أوقيات)
    """
    # لا نحتاج حقول input - كل شيء تلقائي
    
    def validate(self, data):
        """التحقق من أن المستخدم يحتاج فعلاً للشراء"""
        user = self.context['request'].user
        counter, _ = UserTaskCounter.objects.get_or_create(user=user)
        
        if not counter.needs_payment:
            raise serializers.ValidationError({
                'error': 'لا تحتاج لشراء حزمة الآن',
                'tasks_remaining': counter.tasks_remaining,
                'message_fr': 'Vous n\'avez pas besoin d\'acheter un bundle maintenant'
            })
        
        return data